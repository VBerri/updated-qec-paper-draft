from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

import pandas as pd
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError, InvalidAccountError
from qiskit_ibm_runtime.exceptions import IBMBackendError

from qec_baseline.majority_decode import logical_success_from_counts
from qec_baseline.qiskit_circuits import build_repetition_memory_circuit
from qec_stim.utils import ensure_project_dirs


def _build_service(token: str | None, instance: str | None) -> QiskitRuntimeService:
    base_kwargs = {}
    if token:
        base_kwargs["token"] = token
    if instance:
        base_kwargs["instance"] = instance

    # qiskit-ibm-runtime channel names changed across versions.
    last_error: Exception | None = None
    for channel in ("ibm_cloud", "ibm_quantum_platform", "ibm_quantum"):
        try:
            return QiskitRuntimeService(channel=channel, **base_kwargs)
        except ValueError as exc:
            # Unknown channel name in this version: try the next known alias.
            if "channel" in str(exc):
                last_error = exc
                continue
            raise
        except (InvalidAccountError, AccountNotFoundError) as exc:
            # Account/token may be valid for a different channel family.
            last_error = exc
            continue

    raise RuntimeError(
        "Unable to initialize QiskitRuntimeService with known channel names. "
        "Upgrade qiskit-ibm-runtime or verify account configuration."
    ) from last_error


def _backend_name(backend) -> str:
    name_attr = getattr(backend, "name", None)
    return name_attr() if callable(name_attr) else str(name_attr)


def _extract_counts_from_sampler_pub(pub_result) -> dict:
    data = getattr(pub_result, "data", None)
    if data is None:
        raise RuntimeError("Sampler result does not contain data payload")

    for field in dir(data):
        if field.startswith("_"):
            continue
        field_obj = getattr(data, field)
        if hasattr(field_obj, "get_counts"):
            return field_obj.get_counts()

    raise RuntimeError("Unable to extract counts from SamplerV2 result payload")


def _pick_backend(
    service: QiskitRuntimeService,
    min_num_qubits: int = 3,
    backend_name: str | None = None,
):
    if backend_name:
        backend = service.backend(backend_name)
        status = backend.status()
        if not status.operational:
            raise RuntimeError(f"Requested backend '{backend_name}' is not operational.")
        num_qubits = getattr(getattr(backend, "configuration", lambda: None)(), "num_qubits", None)
        if num_qubits is not None and num_qubits < min_num_qubits:
            raise RuntimeError(
                f"Requested backend '{backend_name}' has {num_qubits} qubits, "
                f"but at least {min_num_qubits} are required."
            )
        return backend

    candidates = service.backends(
        simulator=False,
        operational=True,
        min_num_qubits=min_num_qubits,
    )
    if not candidates:
        raise RuntimeError("No operational IBM backend available for the requested qubit count.")
    return min(candidates, key=lambda b: b.status().pending_jobs)


def _build_layer3_circuits(code_size: int = 3):
    return [
        {
            "label": "z_idle_2",
            "basis": "Z",
            "idle_steps": 2,
            "circuit": build_repetition_memory_circuit(code_size=code_size, idle_steps=2, basis="Z"),
        },
        {
            "label": "z_idle_4",
            "basis": "Z",
            "idle_steps": 4,
            "circuit": build_repetition_memory_circuit(code_size=code_size, idle_steps=4, basis="Z"),
        },
        {
            "label": "x_idle_4",
            "basis": "X",
            "idle_steps": 4,
            "circuit": build_repetition_memory_circuit(code_size=code_size, idle_steps=4, basis="X"),
        },
    ]


def _normalize_circuit_specs(code_size: int, circuit_specs: Sequence[dict] | None):
    if circuit_specs is None:
        return _build_layer3_circuits(code_size=code_size)

    normalized = []
    for spec in circuit_specs:
        label = str(spec["label"])
        basis = str(spec["basis"]).upper()
        idle_steps = int(spec["idle_steps"])
        normalized.append(
            {
                "label": label,
                "basis": basis,
                "idle_steps": idle_steps,
                "circuit": build_repetition_memory_circuit(code_size=code_size, idle_steps=idle_steps, basis=basis),
            }
        )
    return normalized


def validate_ibm_environment() -> tuple[str | None, str | None]:
    token = os.getenv("IBM_QUANTUM_TOKEN")
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    return token, instance


def run_ibm_hardware_validation_placeholder() -> dict:
    token, instance = validate_ibm_environment()
    has_token = bool(token)

    return {
        "status": "ready_not_executed",
        "message": "Layer 3 placeholder checked environment. Hardware execution is intentionally deferred.",
        "token_provided": has_token,
        "instance_provided": bool(instance),
    }


def run_ibm_hardware_validation(
    shots: int = 1000,
    max_circuits: int = 3,
    code_size: int = 3,
    backend_name: str | None = None,
    circuit_specs: Sequence[dict] | None = None,
    out_csv: str | Path = "results/ibm_hardware_validation_results.csv",
    out_job_json: str | Path = "results/ibm_hardware_job_metadata.json",
) -> dict:
    if shots <= 0:
        raise ValueError("shots must be positive")
    if max_circuits <= 0:
        raise ValueError("max_circuits must be positive")
    if code_size < 3:
        raise ValueError("code_size must be at least 3")

    token, instance = validate_ibm_environment()
    service = _build_service(token=token, instance=instance)

    backend = _pick_backend(service, min_num_qubits=code_size, backend_name=backend_name)
    candidates = _normalize_circuit_specs(code_size=code_size, circuit_specs=circuit_specs)
    selected = candidates[:max_circuits]

    circuits = [x["circuit"] for x in selected]
    transpiled = transpile(circuits, backend=backend, optimization_level=1)
    try:
        job = backend.run(transpiled, shots=shots)
        result = job.result()
        counts_list = [result.get_counts(idx) for idx in range(len(selected))]
    except IBMBackendError:
        sampler = SamplerV2(mode=backend)
        job = sampler.run(transpiled, shots=shots)
        sampler_result = job.result()
        counts_list = [_extract_counts_from_sampler_pub(sampler_result[idx]) for idx in range(len(selected))]

    rows = []
    for idx, spec in enumerate(selected):
        counts = counts_list[idx]
        success = logical_success_from_counts(counts, expected_logical="0")
        rows.append(
            {
                "layer": "layer3",
                "experiment": "ibm_hardware_validation",
                "label": spec["label"],
                "basis": spec["basis"],
                "code_size": code_size,
                "idle_steps": spec["idle_steps"],
                "shots": shots,
                "backend": _backend_name(backend),
                "logical_success_probability": success,
                "logical_error_rate": 1.0 - success,
            }
        )

    ensure_project_dirs(Path(out_csv).resolve().parents[1])
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)

    meta = {
        "status": "completed",
        "backend": _backend_name(backend),
        "job_id": job.job_id(),
        "shots": shots,
        "num_circuits": len(selected),
        "instance_provided": bool(instance),
    }
    out_job_json = Path(out_job_json)
    out_job_json.parent.mkdir(parents=True, exist_ok=True)
    out_job_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
