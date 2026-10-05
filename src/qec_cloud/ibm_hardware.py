from __future__ import annotations

import json
import math
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
from qiskit import qpy, transpile
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


def _duration_dt_or_raise(circuit, label: str, backend=None) -> int:
    duration = getattr(circuit, "duration", None)
    if duration is None:
        try:
            duration = circuit.estimate_duration(target=getattr(backend, "target", None))
        except Exception:
            duration = None
    if duration is None:
        raise RuntimeError(
            f"Transpiled circuit '{label}' has no scheduled duration. "
            "Refusing to substitute zero for duration matching."
        )
    duration_dt = int(duration)
    if duration_dt <= 0:
        raise RuntimeError(
            f"Transpiled circuit '{label}' has non-positive duration ({duration_dt} dt). "
            "Duration-matched controls cannot be built from this result."
        )
    return duration_dt


def _extract_pub_runtime_metadata(pub_result) -> dict[str, Any]:
    meta = getattr(pub_result, "metadata", None)
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    try:
        return dict(meta)
    except Exception:
        return {"raw_metadata": str(meta)}


def _build_fault_injected_repetition_syndrome_circuit(
    rounds: int,
    delay_dt: int,
    logical_bit: int,
    data_fault_qubit: int | None = None,
    data_fault_stage: int | None = None,
    meas_fault_ancilla: int | None = None,
    meas_fault_round: int | None = None,
):
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    data = QuantumRegister(3, "data")
    anc = QuantumRegister(2, "anc")
    memory = ClassicalRegister(2 * rounds + 3, "m")
    qc = QuantumCircuit(data, anc, memory)

    if logical_bit == 1:
        qc.x(data)

    for r in range(rounds):
        if data_fault_qubit is not None and data_fault_stage == r:
            qc.x(data[data_fault_qubit])

        if delay_dt > 0:
            for q in data:
                qc.delay(delay_dt, q, unit="dt")

        qc.cx(data[0], anc[0])
        qc.cx(data[1], anc[0])
        qc.cx(data[1], anc[1])
        qc.cx(data[2], anc[1])

        if meas_fault_ancilla is not None and meas_fault_round == r:
            qc.x(anc[meas_fault_ancilla])

        qc.measure(anc[0], memory[2 * r])
        qc.measure(anc[1], memory[2 * r + 1])
        qc.reset(anc)

    if data_fault_qubit is not None and data_fault_stage == rounds:
        qc.x(data[data_fault_qubit])

    qc.measure(data[0], memory[2 * rounds + 0])
    qc.measure(data[1], memory[2 * rounds + 1])
    qc.measure(data[2], memory[2 * rounds + 2])
    return qc


def _transpile_for_hardware(circuit, backend, seed_transpiler: int, initial_layout):
    return transpile(
        circuit,
        backend=backend,
        optimization_level=1,
        seed_transpiler=seed_transpiler,
        initial_layout=initial_layout,
        scheduling_method="asap",
    )


def _scheduled_memory_interval_dt(tqc, physical_qubit: int, logical_bit: int, durations) -> int:
    """Preparation-end to final-measurement-start interval (dt) for one physical qubit.

    This is the qubit's actual memory exposure, not the total scheduled circuit duration.
    """
    starts = getattr(tqc, "op_start_times", None)
    if starts is None:
        raise RuntimeError("Scheduled circuit is missing op_start_times; transpile with scheduling_method='asap'.")
    x_end = None
    meas_start = None
    for inst, start in zip(tqc.data, starts):
        q_indices = [tqc.find_bit(q).index for q in inst.qubits]
        if physical_qubit not in q_indices:
            continue
        name = inst.operation.name
        if name == "measure":
            meas_start = int(start) if meas_start is None else min(meas_start, int(start))
        elif name == "x" and logical_bit == 1:
            x_dur = int(durations.get("x", [physical_qubit], unit="dt"))
            end = int(start) + x_dur
            x_end = end if x_end is None else min(x_end, end)
    if meas_start is None:
        raise RuntimeError(f"No measurement found on physical qubit {physical_qubit} in scheduled circuit.")
    prep_end = 0 if logical_bit == 0 else (x_end if x_end is not None else 0)
    return int(meas_start - prep_end)


def _match_control_memory_interval(
    *,
    backend,
    rounds: int,
    logical_bit: int,
    delay_dt_hint: int,
    target_interval_dt: int,
    physical_qubit: int,
    seed_transpiler: int,
    durations,
) -> tuple[Any, Any, int, int, int]:
    """Build a single-qubit control whose prep-to-measurement interval equals the encoded target."""
    layout = [int(physical_qubit)]
    required = int(target_interval_dt)
    last = None
    for _ in range(16):
        required = max(0, required)
        circuit = build_unencoded_memory_control_circuit(
            rounds=rounds,
            delay_dt=max(1, delay_dt_hint),
            logical_bit=logical_bit,
            total_delay_dt=required,
        )
        tqc = _transpile_for_hardware(circuit, backend, seed_transpiler=seed_transpiler, initial_layout=layout)
        interval = _scheduled_memory_interval_dt(tqc, int(physical_qubit), logical_bit, durations)
        last = interval
        delta = interval - int(target_interval_dt)
        if delta == 0:
            total_dt = _duration_dt_or_raise(tqc, label="unencoded_matched", backend=backend)
            return circuit, tqc, int(required), int(interval), int(total_dt)
        required -= delta
    raise RuntimeError(
        "Failed to match control memory interval exactly after iterative tuning "
        f"(target={target_interval_dt} dt, last={last} dt)."
    )


def _build_service(token: str | None, instance: str | None) -> QiskitRuntimeService:
    base_kwargs = {}
    if token:
        base_kwargs["token"] = token
    if instance:
        base_kwargs["instance"] = instance

    last_error: Exception | None = None
    for channel in ("ibm_cloud", "ibm_quantum_platform"):
        try:
            return QiskitRuntimeService(channel=channel, **base_kwargs)
        except ValueError as exc:
            if "channel" in str(exc):
                last_error = exc
                continue
            raise
        except (InvalidAccountError, AccountNotFoundError) as exc:
            last_error = exc
            continue

    raise RuntimeError(
        "Unable to initialize QiskitRuntimeService with known channel names. "
        "Upgrade qiskit-ibm-runtime or verify account configuration."
    ) from last_error


def _backend_name(backend) -> str:
    name_attr = getattr(backend, "name", None)
    return name_attr() if callable(name_attr) else str(name_attr)


def _extract_counts_from_sampler_pub(pub_result, register_name: str = "m") -> dict[str, int]:
    data = getattr(pub_result, "data", None)
    if data is None:
        raise RuntimeError("Sampler result does not contain data payload")

    if hasattr(data, register_name):
        register_obj = getattr(data, register_name)
        if hasattr(register_obj, "get_counts"):
            return {str(k): int(v) for k, v in register_obj.get_counts().items()}

    available = [field for field in dir(data) if not field.startswith("_")]
    raise RuntimeError(
        f"Unable to extract register '{register_name}' from SamplerV2 payload. Available fields: {available}"
    )


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
                f"Requested backend '{backend_name}' has {num_qubits} qubits, but at least {min_num_qubits} are required."
            )
        return backend

    candidates = service.backends(simulator=False, operational=True, min_num_qubits=min_num_qubits)
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


def _build_corrected_hardware_specs(delay_dt: int = 0) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for rounds in (1, 3):
        for logical_bit in (0, 1):
            specs.append(
                {
                    "label": f"encoded_r{rounds}_log{logical_bit}",
                    "kind": "encoded",
                    "rounds": rounds,
                    "logical_bit": logical_bit,
                    "delay_dt": delay_dt,
                }
            )
            for control_data_index in (0, 1, 2):
                specs.append(
                    {
                        "label": f"unencoded_r{rounds}_log{logical_bit}_dq{control_data_index}",
                        "kind": "unencoded",
                        "rounds": rounds,
                        "logical_bit": logical_bit,
                        "delay_dt": delay_dt,
                        "control_data_index": control_data_index,
                    }
                )
    return specs


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
        total_delay_dt = spec.get("total_delay_dt", None)
        if total_delay_dt is not None:
            total_delay_dt = int(total_delay_dt)
        control_data_index = int(spec.get("control_data_index", 0))
        fault_model = spec.get("fault_model", None)

        if kind == "encoded":
            if fault_model is None:
                circuit = build_repetition_syndrome_memory_circuit(rounds=rounds, delay_dt=this_delay, logical_bit=logical_bit)
            else:
                circuit = _build_fault_injected_repetition_syndrome_circuit(
                    rounds=rounds,
                    delay_dt=this_delay,
                    logical_bit=logical_bit,
                    data_fault_qubit=fault_model.get("data_fault_qubit"),
                    data_fault_stage=fault_model.get("data_fault_stage"),
                    meas_fault_ancilla=fault_model.get("meas_fault_ancilla"),
                    meas_fault_round=fault_model.get("meas_fault_round"),
                )
        elif kind == "unencoded":
            circuit = build_unencoded_memory_control_circuit(
                rounds=rounds,
                delay_dt=max(this_delay, 1),
                logical_bit=logical_bit,
                total_delay_dt=total_delay_dt,
            )
        else:
            raise ValueError(f"Unsupported corrected hardware kind: {kind}")

        normalized.append(
            {
                "label": label,
                "kind": kind,
                "rounds": rounds,
                "logical_bit": logical_bit,
                "delay_dt": this_delay,
                "total_delay_dt": total_delay_dt,
                "control_data_index": control_data_index,
                "fault_model": fault_model,
                "circuit": circuit,
            }
        )
    return normalized


def _bits_from_memory_str(memory_str: str) -> list[int]:
    cleaned = memory_str.replace(" ", "")
    if any(ch not in {"0", "1"} for ch in cleaned):
        raise ValueError(f"Non-binary record encountered: {memory_str!r}")
    return [int(ch) for ch in cleaned[::-1]]


def _unique_run_paths(base_path: str | Path, run_tag: str) -> tuple[Path, Path, Path, Path]:
    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base.parent / f"{base.stem}_{run_tag}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / base.name, run_dir / "raw_counts.json", run_dir / "runtime_metadata.json", run_dir


def _require_encoded_bits(bits: list[int], rounds: int) -> None:
    required = (2 * rounds) + 3
    if len(bits) != required:
        raise ValueError(f"Encoded record has {len(bits)} bits, expected {required} for rounds={rounds}")


def _decode_final_data_majority_bit(bits: list[int], rounds: int) -> int:
    _require_encoded_bits(bits, rounds)
    data_start = 2 * rounds
    data_bits = bits[data_start : data_start + 3]
    return 1 if sum(data_bits) >= 2 else 0


def _syndrome_rounds_from_bits(bits: list[int], rounds: int) -> list[tuple[int, int]]:
    _require_encoded_bits(bits, rounds)
    return [(bits[2 * r], bits[2 * r + 1]) for r in range(rounds)]


def _detection_events_from_bits(bits: list[int], rounds: int) -> list[tuple[int, int]]:
    syndrome = _syndrome_rounds_from_bits(bits, rounds)
    data_start = 2 * rounds
    d0, d1, d2 = bits[data_start : data_start + 3]
    final_parity = (d0 ^ d1, d1 ^ d2)

    det: list[tuple[int, int]] = []
    prev = (0, 0)
    for s in syndrome:
        det.append((prev[0] ^ s[0], prev[1] ^ s[1]))
        prev = s
    det.append((prev[0] ^ final_parity[0], prev[1] ^ final_parity[1]))
    return det


def _state_bits(state: int) -> tuple[int, int, int]:
    return (state & 1, (state >> 1) & 1, (state >> 2) & 1)


def _state_parity(state: int) -> tuple[int, int]:
    d0, d1, d2 = _state_bits(state)
    return (d0 ^ d1, d1 ^ d2)


def _hamming_bits(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return sum(int(x != y) for x, y in zip(a, b))


def _decode_history_matching_bit(bits: list[int], rounds: int) -> int:
    _require_encoded_bits(bits, rounds)
    det_obs = _detection_events_from_bits(bits, rounds)
    data_start = 2 * rounds
    final_meas = tuple(bits[data_start : data_start + 3])

    # Fixed weights that are declared once and not tuned on evaluation data.
    p_data = 0.02
    p_det = 0.04
    p_readout = 0.10
    w_data = math.log((1.0 - p_data) / p_data)
    w_det = math.log((1.0 - p_det) / p_det)
    w_readout = math.log((1.0 - p_readout) / p_readout)

    states = list(range(8))
    inf = float("inf")

    def hypothesis_cost(logical_bit: int) -> float:
        init_bits = (logical_bit, logical_bit, logical_bit)
        dp: dict[int, float] = {}

        # Round 0: from hypothesis boundary to first measured round.
        for cur in states:
            cur_bits = _state_bits(cur)
            cur_parity = _state_parity(cur)
            flip_cost = _hamming_bits(init_bits, cur_bits) * w_data
            det_cost = _hamming_bits(det_obs[0], cur_parity) * w_det
            dp[cur] = flip_cost + det_cost

        # Interior rounds: parity-change matching graph along time.
        for t in range(1, rounds):
            next_dp: dict[int, float] = {}
            for cur in states:
                best = inf
                cur_bits = _state_bits(cur)
                cur_parity = _state_parity(cur)
                for prev in states:
                    prev_bits = _state_bits(prev)
                    prev_parity = _state_parity(prev)
                    det_exp = (prev_parity[0] ^ cur_parity[0], prev_parity[1] ^ cur_parity[1])
                    det_cost = _hamming_bits(det_obs[t], det_exp) * w_det
                    trans_cost = _hamming_bits(prev_bits, cur_bits) * w_data
                    total = dp[prev] + det_cost + trans_cost
                    if total < best:
                        best = total
                next_dp[cur] = best
            dp = next_dp

        # Final boundary and readout fit.
        best = inf
        for fin in states:
            fin_bits = _state_bits(fin)
            fin_parity = _state_parity(fin)
            readout_cost = _hamming_bits(fin_bits, final_meas) * w_readout
            for prev in states:
                prev_bits = _state_bits(prev)
                prev_parity = _state_parity(prev)
                det_exp = (prev_parity[0] ^ fin_parity[0], prev_parity[1] ^ fin_parity[1])
                det_cost = _hamming_bits(det_obs[rounds], det_exp) * w_det
                trans_cost = _hamming_bits(prev_bits, fin_bits) * w_data
                total = dp[prev] + det_cost + trans_cost + readout_cost
                if total < best:
                    best = total
        return best

    cost0 = hypothesis_cost(0)
    cost1 = hypothesis_cost(1)
    return 1 if cost1 < cost0 else 0


def _decode_encoded_shot(bits: list[int], rounds: int, prepared_logical_bit: int | None = None) -> int:
    return _decode_history_matching_bit(bits, rounds)


def _decode_unencoded_shot(bits: list[int], prepared_logical_bit: int | None = None) -> int:
    if len(bits) != 1:
        raise ValueError(f"Unencoded record has {len(bits)} bits, expected 1")
    return int(bits[0])


def _assert_counts_sum(counts: dict[str, int], shots: int, label: str) -> None:
    total = int(sum(int(v) for v in counts.values()))
    if total != shots:
        raise RuntimeError(f"Count total mismatch for {label}: expected {shots}, got {total}")


def _evaluate_encoded_counts(spec: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    rounds = int(spec["rounds"])
    expected = int(spec["logical_bit"])
    maj_successes = 0
    hist_successes = 0
    both_correct = 0
    maj_only = 0
    hist_only = 0
    both_wrong = 0

    for bitstring, n_raw in counts.items():
        n = int(n_raw)
        bits = _bits_from_memory_str(bitstring)
        maj = _decode_final_data_majority_bit(bits, rounds)
        hist = _decode_history_matching_bit(bits, rounds)
        maj_ok = int(maj == expected)
        hist_ok = int(hist == expected)
        maj_successes += n * maj_ok
        hist_successes += n * hist_ok

        if maj_ok and hist_ok:
            both_correct += n
        elif maj_ok and not hist_ok:
            maj_only += n
        elif hist_ok and not maj_ok:
            hist_only += n
        else:
            both_wrong += n

    return {
        "majority_successes": maj_successes,
        "history_successes": hist_successes,
        "paired_both_correct": both_correct,
        "paired_majority_only": maj_only,
        "paired_history_only": hist_only,
        "paired_both_wrong": both_wrong,
    }


def _evaluate_unencoded_counts(spec: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    expected = int(spec["logical_bit"])
    successes = 0
    for bitstring, n_raw in counts.items():
        n = int(n_raw)
        bits = _bits_from_memory_str(bitstring)
        decoded = _decode_unencoded_shot(bits)
        successes += n * int(decoded == expected)
    total = int(sum(counts.values()))
    return {
        "majority_successes": successes,
        "history_successes": successes,
        "paired_both_correct": successes,
        "paired_majority_only": 0,
        "paired_history_only": 0,
        "paired_both_wrong": total - successes,
    }


def _successes_from_counts(spec: dict, counts: dict[str, int]) -> int:
    if spec["kind"] == "encoded":
        return int(_evaluate_encoded_counts(spec, counts)["history_successes"])
    return int(_evaluate_unencoded_counts(spec, counts)["history_successes"])


def _wilson_ci(successes: int, shots: int, z: float = 1.96) -> tuple[float, float]:
    if shots <= 0:
        return 0.0, 0.0
    phat = successes / shots
    denom = 1.0 + (z**2 / shots)
    center = (phat + (z**2 / (2 * shots))) / denom
    radius = (z / denom) * math.sqrt((phat * (1 - phat) / shots) + (z**2 / (4 * shots * shots)))
    return max(0.0, center - radius), min(1.0, center + radius)


def _git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _encoded_initial_layout(path_five: Sequence[int]) -> list[int]:
    if len(path_five) != 5:
        raise ValueError("physical_path must contain 5 IDs: [data0, anc0, data1, anc1, data2]")
    data0, anc0, data1, anc1, data2 = [int(x) for x in path_five]
    return [data0, data1, data2, anc0, anc1]


def _control_physical_qubit(path_five: Sequence[int], control_data_index: int) -> int:
    if control_data_index not in {0, 1, 2}:
        raise ValueError("control_data_index must be 0, 1, or 2")
    return int([path_five[0], path_five[2], path_five[4]][control_data_index])


def _measured_physical_qubits_from_circuit(circuit) -> list[int]:
    qubits: set[int] = set()
    for inst in circuit.data:
        if inst.operation.name == "measure":
            for q in inst.qubits:
                qubits.add(int(circuit.find_bit(q).index))
    return sorted(qubits)


def _expected_measured_physical_qubits(spec: dict, physical_path: Sequence[int]) -> list[int]:
    path = [int(x) for x in physical_path]
    if spec["kind"] == "encoded":
        return sorted(set(path))
    return [int(_control_physical_qubit(path, int(spec.get("control_data_index", 0))))]


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
    delay_dt: int = 0,
    circuit_specs: Sequence[dict] | None = None,
    physical_path: Sequence[int] | None = None,
    seed_transpiler: int = 7,
    shuffle_circuit_order: bool = False,
    shuffle_seed: int = 31415,
    out_csv: str | Path = "results/ibm_hardware_syndrome_validation_results.csv",
    out_job_json: str | Path = "results/ibm_hardware_syndrome_validation_job_metadata.json",
    out_transpile_json: str | Path = "results/ibm_hardware_syndrome_transpile_summary.json",
) -> dict:
    if shots <= 0:
        raise ValueError("shots must be positive")

    token, instance = validate_ibm_environment()
    service = _build_service(token=token, instance=instance)
    backend = _pick_backend(service, min_num_qubits=5, backend_name=backend_name)

    if physical_path is None:
        physical_path = [0, 1, 2, 3, 4]

    selected = _normalize_corrected_specs(circuit_specs=circuit_specs, delay_dt=delay_dt)

    if shuffle_circuit_order:
        rng = random.Random(shuffle_seed)
        rng.shuffle(selected)

    try:
        durations = backend.target.durations()
    except Exception as exc:
        raise RuntimeError("Backend target durations unavailable; cannot compute memory intervals.") from exc

    duration_estimates_dt: dict[tuple[int, int], int] = {}
    encoded_intervals: dict[tuple[int, int], dict[int, int]] = {}
    for spec in selected:
        if spec["kind"] != "encoded":
            continue
        layout = _encoded_initial_layout(physical_path)
        tqc = _transpile_for_hardware(spec["circuit"], backend, seed_transpiler=seed_transpiler, initial_layout=layout)
        spec["_pretranspiled"] = tqc
        key = (int(spec["rounds"]), int(spec["logical_bit"]))
        duration_estimates_dt[key] = _duration_dt_or_raise(
            tqc,
            label=spec["label"],
            backend=backend,
        )
        data_phys = [int(physical_path[0]), int(physical_path[2]), int(physical_path[4])]
        encoded_intervals[key] = {
            int(pq): _scheduled_memory_interval_dt(tqc, int(pq), int(spec["logical_bit"]), durations)
            for pq in data_phys
        }

    for spec in selected:
        if spec["kind"] != "unencoded":
            continue
        key = (int(spec["rounds"]), int(spec["logical_bit"]))
        if key not in encoded_intervals:
            raise RuntimeError(f"Missing encoded reference interval for control condition {key}")
        control_data_index = int(spec.get("control_data_index", 0))
        control_pq = _control_physical_qubit(physical_path, control_data_index)
        if control_pq not in encoded_intervals[key]:
            raise RuntimeError(f"No encoded interval available for physical qubit {control_pq}")
        target_interval = int(encoded_intervals[key][control_pq])
        matched_circuit, matched_tqc, matched_total_delay_dt, matched_interval_dt, matched_total_dt = _match_control_memory_interval(
            backend=backend,
            rounds=int(spec["rounds"]),
            logical_bit=int(spec["logical_bit"]),
            delay_dt_hint=int(spec["delay_dt"]),
            target_interval_dt=target_interval,
            physical_qubit=control_pq,
            seed_transpiler=seed_transpiler,
            durations=durations,
        )
        spec["total_delay_dt"] = int(matched_total_delay_dt)
        spec["circuit"] = matched_circuit
        spec["_pretranspiled"] = matched_tqc
        spec["transpiled_duration_dt"] = int(matched_total_dt)
        spec["memory_interval_dt"] = int(matched_interval_dt)
        spec["reference_interval_dt"] = int(target_interval)
        spec["control_physical_qubit"] = int(control_pq)

    transpiled = []
    for idx, spec in enumerate(selected):
        if spec["kind"] == "encoded":
            layout = _encoded_initial_layout(physical_path)
        else:
            layout = [_control_physical_qubit(physical_path, int(spec["control_data_index"]))]
        tqc = spec.get("_pretranspiled")
        if tqc is None:
            tqc = _transpile_for_hardware(spec["circuit"], backend, seed_transpiler=seed_transpiler, initial_layout=layout)
        spec["transpiled_duration_dt"] = _duration_dt_or_raise(tqc, label=spec["label"], backend=backend)
        circuit_id = f"{idx:02d}:{spec['label']}"
        spec["circuit_id"] = circuit_id
        expected_measured = _expected_measured_physical_qubits(spec, physical_path)
        spec["expected_measured_physical_qubits"] = expected_measured
        tqc.metadata = {
            "circuit_id": circuit_id,
            "kind": spec["kind"],
            "rounds": int(spec["rounds"]),
            "logical_bit": int(spec["logical_bit"]),
            "control_data_index": spec.get("control_data_index"),
            "expected_measured_physical_qubits": expected_measured,
            "expected_num_clbits": int(tqc.num_clbits),
        }
        transpiled.append(tqc)

    transpile_rows = []
    for spec, tqc in zip(selected, transpiled):
        transpile_rows.append(
            {
                "label": spec["label"],
                "kind": spec["kind"],
                "rounds": spec["rounds"],
                "logical_bit": spec["logical_bit"],
                "delay_dt": spec["delay_dt"],
                "total_delay_dt": spec.get("total_delay_dt"),
                "control_data_index": spec.get("control_data_index"),
                "depth": int(tqc.depth()),
                "size": int(tqc.size()),
                "num_clbits": int(tqc.num_clbits),
                "estimated_duration_dt": int(spec["transpiled_duration_dt"]),
                "ops": {k: int(v) for k, v in tqc.count_ops().items()},
                "layout": str(getattr(tqc, "layout", None)),
            }
        )

    sampler = SamplerV2(mode=backend)
    scheduler_timing_enabled = False
    try:
        sampler.options.experimental = {"execution": {"scheduler_timing": True}}
        scheduler_timing_enabled = True
    except Exception:
        scheduler_timing_enabled = False

    job = sampler.run(transpiled, shots=shots)
    sampler_result = job.result()
    job_metrics = {}
    try:
        job_metrics = job.metrics()
    except Exception:
        job_metrics = {}

    counts_list = []
    per_pub_metadata = []
    for idx, spec in enumerate(selected):
        per_pub_metadata.append(_extract_pub_runtime_metadata(sampler_result[idx]))
        counts = _extract_counts_from_sampler_pub(sampler_result[idx], register_name="m")
        _assert_counts_sum(counts, shots, spec["label"])
        counts_list.append(counts)

    pub_association = []
    association_ok = True
    for idx, spec in enumerate(selected):
        returned_meta = per_pub_metadata[idx] if idx < len(per_pub_metadata) else {}
        cm = returned_meta.get("circuit_metadata") if isinstance(returned_meta, dict) else None
        returned_id = cm.get("circuit_id") if isinstance(cm, dict) else None
        expected_id = spec.get("circuit_id")
        measured = _measured_physical_qubits_from_circuit(transpiled[idx])
        expected_measured = spec.get("expected_measured_physical_qubits")
        id_match = None if returned_id is None else (returned_id == expected_id)
        measured_match = measured == expected_measured
        if measured_match is False or id_match is False:
            association_ok = False
        pub_association.append(
            {
                "index": idx,
                "label": spec["label"],
                "expected_circuit_id": expected_id,
                "returned_circuit_id": returned_id,
                "circuit_id_match": id_match,
                "measured_physical_qubits": measured,
                "expected_measured_physical_qubits": expected_measured,
                "measured_qubits_match": measured_match,
            }
        )

    rows = []
    for idx, spec in enumerate(selected):
        counts = counts_list[idx]
        if spec["kind"] == "encoded":
            eval_result = _evaluate_encoded_counts(spec, counts)
        else:
            eval_result = _evaluate_unencoded_counts(spec, counts)

        majority_successes = int(eval_result["majority_successes"])
        history_successes = int(eval_result["history_successes"])

        majority_success = majority_successes / shots
        history_success = history_successes / shots

        maj_ci_low, maj_ci_high = _wilson_ci(successes=majority_successes, shots=shots)
        hist_ci_low, hist_ci_high = _wilson_ci(successes=history_successes, shots=shots)

        error_rate = 1.0 - history_success
        error_ci_low = 1.0 - hist_ci_high
        error_ci_high = 1.0 - hist_ci_low

        rows.append(
            {
                "layer": "layer3",
                "experiment": "ibm_hardware_syndrome_validation",
                "label": spec["label"],
                "kind": spec["kind"],
                "rounds": spec["rounds"],
                "logical_bit": spec["logical_bit"],
                "delay_dt": spec["delay_dt"],
                "total_delay_dt": spec.get("total_delay_dt"),
                "control_data_index": spec.get("control_data_index"),
                "transpiled_duration_dt": int(spec["transpiled_duration_dt"]),
                "duration_match_delta_dt": int(
                    spec["transpiled_duration_dt"]
                    - duration_estimates_dt.get((int(spec["rounds"]), int(spec["logical_bit"])), int(spec["transpiled_duration_dt"]))
                ),
                "shots": shots,
                "backend": _backend_name(backend),
                "successes": history_successes,
                "logical_success_probability": history_success,
                "logical_error_rate": error_rate,
                "majority_successes": majority_successes,
                "history_successes": history_successes,
                "majority_success_probability": majority_success,
                "history_success_probability": history_success,
                "majority_error_rate": 1.0 - majority_success,
                "history_error_rate": 1.0 - history_success,
                "paired_both_correct": int(eval_result["paired_both_correct"]),
                "paired_majority_only": int(eval_result["paired_majority_only"]),
                "paired_history_only": int(eval_result["paired_history_only"]),
                "paired_both_wrong": int(eval_result["paired_both_wrong"]),
                "majority_success_ci95_low": maj_ci_low,
                "majority_success_ci95_high": maj_ci_high,
                "history_success_ci95_low": hist_ci_low,
                "history_success_ci95_high": hist_ci_high,
                "success_ci95_low": hist_ci_low,
                "success_ci95_high": hist_ci_high,
                "error_rate_ci95_low": error_ci_low,
                "error_rate_ci95_high": error_ci_high,
                "ci95_low": hist_ci_low,
                "ci95_high": hist_ci_high,
            }
        )

    run_csv, raw_counts_path, runtime_meta_path, run_dir = _unique_run_paths(out_csv, "syndrome_validation")
    ensure_project_dirs(run_csv.resolve().parents[1])
    pd.DataFrame(rows).to_csv(run_csv, index=False)

    raw_counts_payload = {spec["label"]: dict(counts) for spec, counts in zip(selected, counts_list)}
    raw_counts_path.write_text(json.dumps(raw_counts_payload, indent=2), encoding="utf-8")

    circuits_dir = run_dir / "circuits"
    circuits_dir.mkdir(parents=True, exist_ok=True)
    for idx, spec in enumerate(selected):
        with open(circuits_dir / f"{idx:02d}_{spec['label']}_original.qpy", "wb") as fh:
            qpy.dump(spec["circuit"], fh)
        with open(circuits_dir / f"{idx:02d}_{spec['label']}_transpiled.qpy", "wb") as fh:
            qpy.dump(transpiled[idx], fh)

    mapping = {
        "physical_path_logical_order": list(physical_path),
        "builder_qubit_order": ["data0", "data1", "data2", "anc0", "anc1"],
        "flat_register": "m",
        "syndrome_map_per_round": {"s01_index": "2*r", "s12_index": "2*r+1"},
        "final_data_indices": {"d0": "2*rounds", "d1": "2*rounds+1", "d2": "2*rounds+2"},
    }
    (run_dir / "bit_mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")

    run_transpile_summary = run_dir / "transpile_summary.json"
    run_transpile_summary.write_text(json.dumps(transpile_rows, indent=2), encoding="utf-8")

    out_transpile_json = Path(out_transpile_json)
    out_transpile_json.parent.mkdir(parents=True, exist_ok=True)
    out_transpile_json.write_text(json.dumps(transpile_rows, indent=2), encoding="utf-8")

    dt_seconds = None
    try:
        cfg = backend.configuration()
        dt_seconds = getattr(cfg, "dt", None)
    except Exception:
        dt_seconds = None

    calibration = {
        "backend_properties_last_update": None,
        "data_qubit_metrics": {},
        "path_cx_metrics": {},
    }
    try:
        props = backend.properties()
        calibration["backend_properties_last_update"] = str(getattr(props, "last_update_date", None))
        path = list(physical_path)
        data_phys = [path[0], path[2], path[4]]
        for q in data_phys:
            qprops = {item.name: item.value for item in props.qubits[q]}
            calibration["data_qubit_metrics"][str(q)] = {
                "T1": qprops.get("T1"),
                "T2": qprops.get("T2"),
                "readout_error": qprops.get("readout_error"),
            }
        path_edges = [(path[0], path[1]), (path[1], path[2]), (path[2], path[3]), (path[3], path[4])]
        for a, b in path_edges:
            gate_vals = None
            try:
                gate_vals = props.gate_property("cx", [a, b])
            except Exception:
                try:
                    gate_vals = props.gate_property("cx", [b, a])
                except Exception:
                    gate_vals = None
            calibration["path_cx_metrics"][f"{a}-{b}"] = {
                "gate_error": (gate_vals.get("gate_error", [None])[0] if gate_vals else None),
                "gate_length": (gate_vals.get("gate_length", [None])[0] if gate_vals else None),
            }
    except Exception:
        pass

    timing_table = []
    for spec in selected:
        key = (int(spec["rounds"]), int(spec["logical_bit"]))
        encoded_ref_dt = int(duration_estimates_dt.get(key, spec["transpiled_duration_dt"]))
        duration_dt = int(spec["transpiled_duration_dt"])
        row = {
            "label": spec["label"],
            "kind": spec["kind"],
            "rounds": int(spec["rounds"]),
            "logical_bit": int(spec["logical_bit"]),
            "reference_encoded_duration_dt": encoded_ref_dt,
            "actual_duration_dt": duration_dt,
            "duration_match_delta_dt": int(duration_dt - encoded_ref_dt),
            "dt_seconds": dt_seconds,
        }
        if spec["kind"] == "encoded":
            row["memory_interval_dt_by_physical_qubit"] = {
                str(k): int(v) for k, v in encoded_intervals.get(key, {}).items()
            }
        else:
            mi = int(spec.get("memory_interval_dt"))
            ref = int(spec.get("reference_interval_dt"))
            row["control_physical_qubit"] = int(spec.get("control_physical_qubit"))
            row["memory_interval_dt"] = mi
            row["reference_encoded_interval_dt"] = ref
            row["memory_interval_delta_dt"] = int(mi - ref)
            row["memory_interval_delta_seconds"] = ((mi - ref) * dt_seconds) if dt_seconds else None
        timing_table.append(row)
    (run_dir / "timing_comparison.json").write_text(json.dumps(timing_table, indent=2), encoding="utf-8")

    pub_association_path = run_dir / "pub_association_check.json"
    pub_association_path.write_text(json.dumps(pub_association, indent=2), encoding="utf-8")
    if not association_ok:
        raise RuntimeError(
            f"PUB association check failed; see {pub_association_path}. "
            "Measured physical qubits or returned circuit identifiers did not match the submitted circuits."
        )

    meta = {
        "status": "completed",
        "backend": _backend_name(backend),
        "job_id": job.job_id(),
        "shots": shots,
        "num_circuits": len(selected),
        "instance_provided": bool(instance),
        "transpile_summary": str(out_transpile_json),
        "output_csv": str(run_csv),
        "raw_counts_path": str(raw_counts_path),
        "runtime_metadata": str(runtime_meta_path),
        "run_dir": str(run_dir),
        "scheduler_timing_enabled": scheduler_timing_enabled,
        "scheduler_timing_returned": any(bool(m) for m in per_pub_metadata),
        "scheduler_pub_metadata": per_pub_metadata,
        "job_metrics": job_metrics,
        "seed_transpiler": seed_transpiler,
        "physical_path_logical_order": list(physical_path),
        "dt_seconds": dt_seconds,
        "timing_comparison_path": str(run_dir / "timing_comparison.json"),
        "pub_association_check_path": str(pub_association_path),
        "matching_defined_over": "data_qubit_memory_interval",
        # Interval match is computed from local transpiler op_start_times, not the returned device pulse trace.
        "interval_match_basis": "transpiler_schedule_op_start_times",
        "run_transpile_summary": str(run_transpile_summary),
        "calibration": calibration,
        "decoder_description": "history_based_heuristic_dynamic_programming",
        "commit": _git_commit_hash(),
    }
    out_job_json = Path(out_job_json)
    out_job_json.parent.mkdir(parents=True, exist_ok=True)
    out_job_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    runtime_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
