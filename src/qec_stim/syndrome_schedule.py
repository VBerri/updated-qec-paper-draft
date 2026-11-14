from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import stim

from .mwpm_decode import decode_syndrome_batch


@dataclass(frozen=True)
class ScheduleCostModel:
    cx_ticks: int = 1
    ancilla_measure_ticks: int = 1
    ancilla_reset_ticks: int = 1


@dataclass(frozen=True)
class FixedDurationSpec:
    distance: int
    rounds: int
    logical_bit: int
    target_duration_ticks: int


@dataclass(frozen=True)
class NoiseModel:
    p_data_round: float = 0.0
    p_idle_tick: float = 0.0
    p_meas_ancilla: float = 0.0
    p_reset_ancilla: float = 0.0
    p_final_data_meas: float = 0.0


@dataclass(frozen=True)
class InjectedFault:
    stage: str
    qubit: int
    round_index: int | None = None


def _data_and_ancilla_qubits(distance: int) -> tuple[list[int], list[int]]:
    if distance < 2:
        raise ValueError("distance must be at least 2")
    if distance % 2 == 0:
        raise ValueError("distance must be odd for repetition code")
    data = [2 * i for i in range(distance)]
    ancilla = [2 * i + 1 for i in range(distance - 1)]
    return data, ancilla


def _append_ticks(circuit: stim.Circuit, num_ticks: int) -> None:
    for _ in range(num_ticks):
        circuit.append("TICK")


def _segment_probability(p_tick: float, ticks: int) -> float:
    if ticks <= 0 or p_tick <= 0:
        return 0.0
    return float(1.0 - (1.0 - p_tick) ** ticks)


def plan_fixed_duration_schedule(spec: FixedDurationSpec, cost_model: ScheduleCostModel | None = None) -> dict[str, int | list[int]]:
    model = cost_model or ScheduleCostModel()
    rounds = spec.rounds

    if rounds < 0:
        raise ValueError("rounds must be non-negative")
    if spec.target_duration_ticks < 0:
        raise ValueError("target_duration_ticks must be non-negative")

    base_per_data = rounds * (2 * model.cx_ticks + model.ancilla_measure_ticks + model.ancilla_reset_ticks)
    if spec.target_duration_ticks < base_per_data:
        raise ValueError(
            f"Target duration {spec.target_duration_ticks} cannot fit base duration {base_per_data} for rounds={rounds}"
        )

    extra_idle = spec.target_duration_ticks - base_per_data
    slots = rounds + 1
    per_slot = extra_idle // slots
    rem = extra_idle % slots

    idle_before_round = [per_slot + (1 if i < rem else 0) for i in range(rounds)]
    idle_tail = per_slot

    return {
        "base_duration_ticks": base_per_data,
        "extra_idle_ticks": extra_idle,
        "idle_before_round": idle_before_round,
        "idle_tail": idle_tail,
    }


def _apply_injected_faults(
    circuit: stim.Circuit,
    faults: Iterable[InjectedFault] | None,
    stage: str,
    data_qubits: list[int],
    round_index: int | None = None,
) -> None:
    if faults is None:
        return
    data_set = set(data_qubits)
    for fault in faults:
        if fault.stage != stage:
            continue
        if fault.round_index != round_index:
            continue
        if fault.qubit not in data_set:
            raise ValueError(f"Injected fault qubit {fault.qubit} is not a data qubit")
        circuit.append("X_ERROR", [fault.qubit], [1.0])


def build_fixed_duration_memory_circuit(
    spec: FixedDurationSpec,
    noise: NoiseModel | None = None,
    cost_model: ScheduleCostModel | None = None,
    injected_faults: Iterable[InjectedFault] | None = None,
) -> tuple[stim.Circuit, dict[str, int | float | str]]:
    model = cost_model or ScheduleCostModel()
    noise = noise or NoiseModel()
    plan = plan_fixed_duration_schedule(spec=spec, cost_model=model)

    data, ancilla = _data_and_ancilla_qubits(spec.distance)
    anc_count = len(ancilla)
    data_count = len(data)

    left_layer = [(data[i], ancilla[i]) for i in range(anc_count)]
    right_layer = [(data[i + 1], ancilla[i]) for i in range(anc_count)]

    circuit = stim.Circuit()
    circuit.append("R", data + ancilla)
    if spec.logical_bit == 1:
        circuit.append("X", data)

    for r in range(spec.rounds):
        idle_ticks = int(plan["idle_before_round"][r])
        _append_ticks(circuit, idle_ticks)
        p_idle = _segment_probability(noise.p_idle_tick, idle_ticks)
        if p_idle > 0:
            circuit.append("X_ERROR", data, [p_idle])

        _apply_injected_faults(circuit, injected_faults, "before_round", data, round_index=r)

        if noise.p_data_round > 0:
            circuit.append("X_ERROR", data, [noise.p_data_round])

        targets_l: list[int] = []
        for c, t in left_layer:
            targets_l.extend([c, t])
        circuit.append("CX", targets_l)

        targets_r: list[int] = []
        for c, t in right_layer:
            targets_r.extend([c, t])
        circuit.append("CX", targets_r)

        if noise.p_meas_ancilla > 0:
            circuit.append("X_ERROR", ancilla, [noise.p_meas_ancilla])
        circuit.append("MR", ancilla)
        if noise.p_reset_ancilla > 0:
            circuit.append("X_ERROR", ancilla, [noise.p_reset_ancilla])

        if r == 0:
            for j in range(anc_count):
                circuit.append("DETECTOR", [stim.target_rec(-(anc_count - j))])
        else:
            for j in range(anc_count):
                circuit.append(
                    "DETECTOR",
                    [
                        stim.target_rec(-(anc_count - j)),
                        stim.target_rec(-(2 * anc_count - j)),
                    ],
                )

    idle_tail = int(plan["idle_tail"])
    _append_ticks(circuit, idle_tail)
    p_idle_tail = _segment_probability(noise.p_idle_tick, idle_tail)
    if p_idle_tail > 0:
        circuit.append("X_ERROR", data, [p_idle_tail])

    _apply_injected_faults(circuit, injected_faults, "before_final_measure", data, round_index=None)

    if noise.p_final_data_meas > 0:
        circuit.append("X_ERROR", data, [noise.p_final_data_meas])
    circuit.append("M", data)

    if spec.rounds > 0:
        for j in range(anc_count):
            anc_offset = -(data_count + anc_count - j)
            left_data_offset = -(data_count - j)
            right_data_offset = -(data_count - (j + 1))
            circuit.append(
                "DETECTOR",
                [
                    stim.target_rec(anc_offset),
                    stim.target_rec(left_data_offset),
                    stim.target_rec(right_data_offset),
                ],
            )

    # This benchmark tracks computational-basis memory of the rightmost data qubit.
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)

    structural_idle = spec.rounds * (model.ancilla_measure_ticks + model.ancilla_reset_ticks)
    active_gate = spec.rounds * (2 * model.cx_ticks)
    inserted_idle = int(plan["extra_idle_ticks"])
    audit = {
        "distance": spec.distance,
        "rounds": spec.rounds,
        "logical_bit": spec.logical_bit,
        "target_duration_ticks": spec.target_duration_ticks,
        "base_duration_ticks": int(plan["base_duration_ticks"]),
        "inserted_idle_ticks": inserted_idle,
        "structural_idle_ticks": structural_idle,
        "active_gate_ticks": active_gate,
        "meas_reset_ticks": structural_idle,
        "accounted_total_ticks": active_gate + structural_idle + inserted_idle,
        "idle_tail_ticks": idle_tail,
        "num_detectors": circuit.num_detectors,
        "num_observables": circuit.num_observables,
        "mwpm_applicable": int(circuit.num_detectors > 0),
        "idle_before_round": ",".join(str(v) for v in plan["idle_before_round"]),
    }
    return circuit, audit


def _final_data_measurement_columns(circuit: stim.Circuit) -> list[int]:
    flat = circuit.flattened()
    measurement_col = 0
    final_cols: list[int] = []

    for name, targets, _ in flat.flattened_operations():
        if name in {"M", "MX", "MY", "MZ", "MR", "MRX", "MRY", "MRZ"}:
            cols = list(range(measurement_col, measurement_col + len(targets)))
            measurement_col += len(targets)
            if name in {"M", "MX", "MY", "MZ"}:
                final_cols = cols

    if not final_cols:
        raise RuntimeError("Unable to identify final data measurement columns")
    return final_cols


def sample_consistent_records(circuit: stim.Circuit, shots: int, seed: int | None = None):
    sampler = circuit.compile_sampler(seed=seed) if seed is not None else circuit.compile_sampler()
    measurements = sampler.sample(shots)
    converter = circuit.compile_m2d_converter()
    syndrome, actual_observables = converter.convert(measurements=measurements, separate_observables=True)
    return measurements, syndrome, actual_observables


def final_data_majority_predictions(measurements: np.ndarray, final_data_cols: list[int]) -> np.ndarray:
    final_data = measurements[:, final_data_cols].astype(np.uint8)
    logical_bit = (np.sum(final_data, axis=1) > (final_data.shape[1] / 2.0)).astype(np.uint8)
    return logical_bit.reshape(-1, 1)


def evaluate_fixed_duration_decoders(
    *,
    circuit: stim.Circuit,
    logical_bit: int,
    shots: int,
    seed: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    measurements, syndrome, actual_observables = sample_consistent_records(circuit, shots=shots, seed=seed)
    final_cols = _final_data_measurement_columns(circuit)

    method_rows: list[dict[str, int | float | str]] = []
    pairwise_rows: list[dict[str, int | str]] = []

    preds: dict[str, np.ndarray] = {}
    preds["final_data_majority"] = final_data_majority_predictions(measurements, final_cols)

    failure_masks: dict[str, np.ndarray] = {}
    maj_fail = preds["final_data_majority"].reshape(-1) != logical_bit
    failure_masks["final_data_majority"] = maj_fail
    method_rows.append(
        {
            "method": "final_data_majority",
            "scoring_target": "logical_bit",
            "shots": shots,
            "failures": int(np.sum(maj_fail)),
            "logical_error_rate": float(np.mean(maj_fail)),
            "seed": seed,
        }
    )

    if circuit.num_detectors > 0:
        oracle_pred = decode_syndrome_batch(circuit, syndrome, weight_mode="detector_model")
        preds["mwpm_oracle_informed"] = oracle_pred
        oracle_fail = oracle_pred.reshape(-1) != actual_observables.reshape(-1)
        failure_masks["mwpm_oracle_informed"] = oracle_fail
        method_rows.append(
            {
                "method": "mwpm_oracle_informed",
                "scoring_target": "observable",
                "shots": shots,
                "failures": int(np.sum(oracle_fail)),
                "logical_error_rate": float(np.mean(oracle_fail)),
                "seed": seed,
            }
        )

    names = list(failure_masks.keys())
    for i, left_name in enumerate(names):
        left_mask = failure_masks[left_name]
        for j, right_name in enumerate(names):
            if i >= j:
                continue
            right_mask = failure_masks[right_name]
            pairwise_rows.append(
                {
                    "left_method": left_name,
                    "right_method": right_name,
                    "left_only_failures": int(np.sum(left_mask & ~right_mask)),
                    "right_only_failures": int(np.sum(right_mask & ~left_mask)),
                    "both_failures": int(np.sum(left_mask & right_mask)),
                    "both_success": int(np.sum(~left_mask & ~right_mask)),
                }
            )

    counts_rows: list[dict[str, int | str]] = []
    final_data = measurements[:, final_cols].astype(np.uint8)
    unique, counts = np.unique(final_data, axis=0, return_counts=True)
    for bits, count in zip(unique, counts):
        bitstring = "".join(str(int(b)) for b in bits.tolist())
        counts_rows.append({"bitstring": bitstring, "count": int(count)})

    return pd.DataFrame(method_rows), pd.DataFrame(pairwise_rows), pd.DataFrame(counts_rows)


def run_syndrome_schedule_smoke(
    output_dir: str | Path,
    *,
    target_duration_ticks: int = 30,
    shots: int = 200,
    seed: int = 20261114,
    distances: Iterable[int] = (3, 5),
    rounds_set: Iterable[int] = (0, 1, 3, 5),
    logical_inputs: Iterable[int] = (0, 1),
) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "target_duration_ticks": target_duration_ticks,
        "shots": shots,
        "seed": seed,
        "distances": list(distances),
        "rounds_set": list(rounds_set),
        "logical_inputs": list(logical_inputs),
        "noise_model": {
            "p_data_round": 0.0,
            "p_idle_tick": 0.0,
            "p_meas_ancilla": 0.0,
            "p_reset_ancilla": 0.0,
            "p_final_data_meas": 0.0,
        },
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    timing_rows = []
    method_rows = []
    pairwise_rows = []
    counts_rows = []

    for d in distances:
        for r in rounds_set:
            for lb in logical_inputs:
                spec = FixedDurationSpec(
                    distance=d,
                    rounds=r,
                    logical_bit=lb,
                    target_duration_ticks=target_duration_ticks,
                )
                circuit, audit = build_fixed_duration_memory_circuit(spec=spec, noise=NoiseModel())
                (out_dir / "circuits").mkdir(parents=True, exist_ok=True)
                circuit_path = out_dir / "circuits" / f"d{d}_r{r}_l{lb}.stim"
                circuit_path.write_text(str(circuit), encoding="utf-8")

                timing_rows.append(audit)

                methods_df, pairwise_df, counts_df = evaluate_fixed_duration_decoders(
                    circuit=circuit,
                    logical_bit=lb,
                    shots=shots,
                    seed=seed + d * 100 + r * 10 + lb,
                )
                methods_df.insert(0, "logical_bit", lb)
                methods_df.insert(0, "rounds", r)
                methods_df.insert(0, "distance", d)
                method_rows.append(methods_df)

                if not pairwise_df.empty:
                    pairwise_df.insert(0, "logical_bit", lb)
                    pairwise_df.insert(0, "rounds", r)
                    pairwise_df.insert(0, "distance", d)
                    pairwise_rows.append(pairwise_df)

                counts_df.insert(0, "logical_bit", lb)
                counts_df.insert(0, "rounds", r)
                counts_df.insert(0, "distance", d)
                counts_rows.append(counts_df)

    pd.DataFrame(timing_rows).to_csv(out_dir / "timing_audit.csv", index=False)
    pd.concat(method_rows, ignore_index=True).to_csv(out_dir / "decoder_metrics.csv", index=False)
    if pairwise_rows:
        pd.concat(pairwise_rows, ignore_index=True).to_csv(out_dir / "decoder_pairwise.csv", index=False)
    pd.concat(counts_rows, ignore_index=True).to_csv(out_dir / "counts.csv", index=False)

    return out_dir
