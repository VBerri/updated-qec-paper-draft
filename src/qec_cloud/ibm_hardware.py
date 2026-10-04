from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Sequence

import pandas as pd
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError, InvalidAccountError
from qiskit_ibm_runtime.exceptions import IBMBackendError

from qec_baseline.majority_decode import logical_success_from_counts
from qec_baseline.qiskit_circuits import (
    build_repetition_memory_circuit,
    build_repetition_syndrome_memory_circuit,
    build_unencoded_memory_control_circuit,
)
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


def _build_corrected_hardware_specs(delay_dt: int = 256):
    return [
        {"label": "encoded_r1_log0", "kind": "encoded", "rounds": 1, "logical_bit": 0, "delay_dt": delay_dt},
        {"label": "encoded_r1_log1", "kind": "encoded", "rounds": 1, "logical_bit": 1, "delay_dt": delay_dt},
        {"label": "encoded_r3_log0", "kind": "encoded", "rounds": 3, "logical_bit": 0, "delay_dt": delay_dt},
        {"label": "encoded_r3_log1", "kind": "encoded", "rounds": 3, "logical_bit": 1, "delay_dt": delay_dt},
        {"label": "unencoded_r3_log0", "kind": "unencoded", "rounds": 3, "logical_bit": 0, "delay_dt": delay_dt},
        {"label": "unencoded_r3_log1", "kind": "unencoded", "rounds": 3, "logical_bit": 1, "delay_dt": delay_dt},
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


def _normalize_corrected_specs(circuit_specs: Sequence[dict] | None, delay_dt: int):
    if circuit_specs is None:
        circuit_specs = _build_corrected_hardware_specs(delay_dt=delay_dt)

    normalized = []
    for spec in circuit_specs:
        label = str(spec["label"])
        kind = str(spec.get("kind", "encoded"))
        rounds = int(spec["rounds"])
        logical_bit = int(spec.get("logical_bit", 0))
        this_delay = int(spec.get("delay_dt", delay_dt))
        if kind == "encoded":
            circuit = build_repetition_syndrome_memory_circuit(rounds=rounds, delay_dt=this_delay, logical_bit=logical_bit)
        elif kind == "unencoded":
            circuit = build_unencoded_memory_control_circuit(rounds=rounds, delay_dt=this_delay, logical_bit=logical_bit)
        else:
            raise ValueError(f"Unsupported corrected hardware kind: {kind}")

        normalized.append(
            {
                "label": label,
                "kind": kind,
                "rounds": rounds,
                "logical_bit": logical_bit,
                "delay_dt": this_delay,
                "circuit": circuit,
            }
        )
    return normalized


def _bits_from_memory_str(memory_str: str) -> list[int]:
    cleaned = memory_str.replace(" ", "")
    return [int(ch) for ch in cleaned[::-1]]


def _decode_encoded_shot(bits: list[int], rounds: int, prepared_logical_bit: int) -> int:
    # Flat memory map from circuit builder:
    # [2*rounds syndrome bits][3 final data bits]
    data_start = 2 * rounds
    data_bits = bits[data_start : data_start + 3]
    if len(data_bits) != 3:
        return 0

    # Use latest non-trivial syndrome as correction hint before majority.
    inferred_data = data_bits.copy()
    for r in range(rounds - 1, -1, -1):
        s01 = bits[2 * r]
        s12 = bits[2 * r + 1]
        if s01 == 0 and s12 == 0:
            continue
        if s01 == 1 and s12 == 0:
            inferred_data[0] ^= 1
        elif s01 == 0 and s12 == 1:
            inferred_data[2] ^= 1
        else:
            inferred_data[1] ^= 1
        break

    majority = 1 if sum(inferred_data) >= 2 else 0
    return 1 if majority == prepared_logical_bit else 0


def _decode_unencoded_shot(bits: list[int], prepared_logical_bit: int) -> int:
    if not bits:
        return 0
    return 1 if bits[0] == prepared_logical_bit else 0


def _successes_from_counts(spec: dict, counts: dict[str, int]) -> int:
    successes = 0
    for bitstring, n in counts.items():
        bits = _bits_from_memory_str(bitstring)
        if spec["kind"] == "encoded":
            succ = _decode_encoded_shot(bits, rounds=spec["rounds"], prepared_logical_bit=spec["logical_bit"])
        else:
            succ = _decode_unencoded_shot(bits, prepared_logical_bit=spec["logical_bit"])
        successes += int(n) * succ
    return successes


def _wilson_ci(successes: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    if shots <= 0:
        return 0.0, 0.0
    phat = successes / shots
    denom = 1.0 + (z**2 / shots)
    center = (phat + (z**2 / (2 * shots))) / denom
    radius = (z / denom) * math.sqrt((phat * (1 - phat) / shots) + (z**2 / (4 * shots * shots)))
    return max(0.0, center - radius), min(1.0, center + radius)


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


def run_ibm_hardware_syndrome_validation(
    shots: int = 1000,
    backend_name: str | None = None,
    delay_dt: int = 256,
    circuit_specs: Sequence[dict] | None = None,
    out_csv: str | Path = "results/ibm_hardware_syndrome_validation_results.csv",
    out_job_json: str | Path = "results/ibm_hardware_syndrome_validation_job_metadata.json",
    out_transpile_json: str | Path = "results/ibm_hardware_syndrome_transpile_summary.json",
) -> dict:
    if shots <= 0:
        raise ValueError("shots must be positive")

    token, instance = validate_ibm_environment()
    service = _build_service(token=token, instance=instance)
    backend = _pick_backend(service, min_num_qubits=5, backend_name=backend_name)

    selected = _normalize_corrected_specs(circuit_specs=circuit_specs, delay_dt=delay_dt)
    circuits = [x["circuit"] for x in selected]
    transpiled = transpile(circuits, backend=backend, optimization_level=1)

    transpile_rows = []
    for spec, tqc in zip(selected, transpiled):
        transpile_rows.append(
            {
                "label": spec["label"],
                "kind": spec["kind"],
                "rounds": spec["rounds"],
                "logical_bit": spec["logical_bit"],
                "delay_dt": spec["delay_dt"],
                "depth": int(tqc.depth()),
                "size": int(tqc.size()),
                "num_clbits": int(tqc.num_clbits),
                "ops": {k: int(v) for k, v in tqc.count_ops().items()},
            }
        )

    sampler = SamplerV2(mode=backend)
    job = sampler.run(transpiled, shots=shots)
    sampler_result = job.result()
    counts_list = [_extract_counts_from_sampler_pub(sampler_result[idx]) for idx in range(len(selected))]

    rows = []
    for idx, spec in enumerate(selected):
        counts = counts_list[idx]
        successes = _successes_from_counts(spec, counts)

        success = successes / shots
        ci_low, ci_high = _wilson_ci(successes=successes, shots=shots)
        rows.append(
            {
                "layer": "layer3",
                "experiment": "ibm_hardware_syndrome_validation",
                "label": spec["label"],
                "kind": spec["kind"],
                "rounds": spec["rounds"],
                "logical_bit": spec["logical_bit"],
                "delay_dt": spec["delay_dt"],
                "shots": shots,
                "backend": _backend_name(backend),
                "successes": successes,
                "logical_success_probability": success,
                "logical_error_rate": 1.0 - success,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
            }
        )

    ensure_project_dirs(Path(out_csv).resolve().parents[1])
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)

    out_transpile_json = Path(out_transpile_json)
    out_transpile_json.parent.mkdir(parents=True, exist_ok=True)
    out_transpile_json.write_text(json.dumps(transpile_rows, indent=2), encoding="utf-8")

    meta = {
        "status": "completed",
        "backend": _backend_name(backend),
        "job_id": job.job_id(),
        "shots": shots,
        "num_circuits": len(selected),
        "instance_provided": bool(instance),
        "transpile_summary": str(out_transpile_json),
    }
    out_job_json = Path(out_job_json)
    out_job_json.parent.mkdir(parents=True, exist_ok=True)
    out_job_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
