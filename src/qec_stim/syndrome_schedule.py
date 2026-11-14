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
    p_cx: float = 0.0
    p_meas_ancilla: float = 0.0
    p_reset_ancilla: float = 0.0
    p_final_data_meas: float = 0.0


@dataclass(frozen=True)
class InjectedFault:
    stage: str
    qubit: int
    round_index: int | None = None


def odd_flip_probability(p_tick: float, ticks: int) -> float:
    """Probability of net odd flips after `ticks` independent symmetric flip opportunities."""
    if ticks <= 0 or p_tick <= 0:
        return 0.0
    return float((1.0 - (1.0 - 2.0 * p_tick) ** ticks) / 2.0)


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


def _append_cx_layer(circuit: stim.Circuit, pairs: list[tuple[int, int]], p_cx: float) -> None:
    if not pairs:
        return
    targets: list[int] = []
    for c, t in pairs:
        targets.extend([c, t])
    circuit.append("CX", targets)
    if p_cx > 0:
        circuit.append("DEPOLARIZE2", targets, [p_cx])


def _apply_injected_faults(
    circuit: stim.Circuit,
    faults: Iterable[InjectedFault] | None,
    stage: str,
    data_qubits: list[int],
    round_index: int | None = None,
) -> None:
    if faults is None:
        return
    allowed = set(data_qubits)
    for fault in faults:
        if fault.stage != stage:
            continue
        if fault.round_index != round_index:
            continue
        if fault.qubit not in allowed:
            raise ValueError(f"Injected fault qubit {fault.qubit} is not a data qubit")
        circuit.append("X_ERROR", [fault.qubit], [1.0])


def plan_fixed_duration_schedule(spec: FixedDurationSpec, cost_model: ScheduleCostModel | None = None) -> dict[str, int | list[int]]:
    model = cost_model or ScheduleCostModel()

    if spec.rounds < 0:
        raise ValueError("rounds must be non-negative")
    if spec.target_duration_ticks < 0:
        raise ValueError("target_duration_ticks must be non-negative")

    base_per_data = spec.rounds * (2 * model.cx_ticks + model.ancilla_measure_ticks + model.ancilla_reset_ticks)
    if spec.target_duration_ticks < base_per_data:
        raise ValueError(
            f"Target duration {spec.target_duration_ticks} cannot fit base duration {base_per_data} for rounds={spec.rounds}"
        )

    extra_idle = spec.target_duration_ticks - base_per_data
    slots = spec.rounds + 1
    per_slot = extra_idle // slots
    rem = extra_idle % slots

    idle_before_round = [per_slot + (1 if i < rem else 0) for i in range(spec.rounds)]
    idle_tail = per_slot
    return {
        "base_duration_ticks": base_per_data,
        "extra_idle_ticks": extra_idle,
        "idle_before_round": idle_before_round,
        "idle_tail": idle_tail,
    }


def build_data_qubit_timeline(spec: FixedDurationSpec, cost_model: ScheduleCostModel | None = None) -> dict[str, object]:
    model = cost_model or ScheduleCostModel()
    plan = plan_fixed_duration_schedule(spec=spec, cost_model=model)
    data, _ancilla = _data_and_ancilla_qubits(spec.distance)

    # Round-level participation sets for data qubits.
    left_active = {data[i] for i in range(spec.distance - 1)}
    right_active = {data[i + 1] for i in range(spec.distance - 1)}

    segments: list[dict[str, object]] = []
    for r in range(spec.rounds):
        idle = int(plan["idle_before_round"][r])
        if idle > 0:
            segments.append(
                {
                    "segment": f"round{r}_idle_before",
                    "duration": idle,
                    "active_data": set(),
                    "kind": "idle_before_round",
                    "round": r,
                }
            )
        segments.append(
            {
                "segment": f"round{r}_cx_left",
                "duration": model.cx_ticks,
                "active_data": set(left_active),
                "kind": "cx_left",
                "round": r,
            }
        )
        segments.append(
            {
                "segment": f"round{r}_cx_right",
                "duration": model.cx_ticks,
                "active_data": set(right_active),
                "kind": "cx_right",
                "round": r,
            }
        )
        segments.append(
            {
                "segment": f"round{r}_anc_measure",
                "duration": model.ancilla_measure_ticks,
                "active_data": set(),
                "kind": "ancilla_measure",
                "round": r,
            }
        )
        segments.append(
            {
                "segment": f"round{r}_anc_reset",
                "duration": model.ancilla_reset_ticks,
                "active_data": set(),
                "kind": "ancilla_reset",
                "round": r,
            }
        )

    idle_tail = int(plan["idle_tail"])
    if idle_tail > 0:
        segments.append(
            {
                "segment": "idle_tail",
                "duration": idle_tail,
                "active_data": set(),
                "kind": "idle_tail",
                "round": None,
            }
        )

    timelines: dict[int, list[dict[str, int | str]]]= {q: [] for q in data}
    for q in data:
        t0 = 0
        for seg in segments:
            duration = int(seg["duration"])
            if duration <= 0:
                continue
            is_active = q in seg["active_data"]
            timelines[q].append(
                {
                    "segment": str(seg["segment"]),
                    "kind": str(seg["kind"]),
                    "start": t0,
                    "end": t0 + duration,
                    "duration": duration,
                    "active": int(is_active),
                    "idle": int(not is_active),
                }
            )
            t0 += duration

    return {
        "plan": plan,
        "segments": segments,
        "timelines": timelines,
    }


def build_fixed_duration_memory_circuit(
    spec: FixedDurationSpec,
    noise: NoiseModel | None = None,
    cost_model: ScheduleCostModel | None = None,
    injected_faults: Iterable[InjectedFault] | None = None,
) -> tuple[stim.Circuit, dict[str, int | float | str]]:
    noise = noise or NoiseModel()
    model = cost_model or ScheduleCostModel()
    timeline = build_data_qubit_timeline(spec=spec, cost_model=model)

    data, ancilla = _data_and_ancilla_qubits(spec.distance)
    anc_count = len(ancilla)
    data_count = len(data)

    left_pairs = [(data[i], ancilla[i]) for i in range(anc_count)]
    right_pairs = [(data[i + 1], ancilla[i]) for i in range(anc_count)]

    circuit = stim.Circuit()
    circuit.append("R", data + ancilla)
    if spec.logical_bit == 1:
        circuit.append("X", data)

    for seg in timeline["segments"]:
        kind = str(seg["kind"])
        duration = int(seg["duration"])
        round_index = seg["round"]

        idle_data = [q for q in data if q not in seg["active_data"]]
        p_idle = odd_flip_probability(noise.p_idle_tick, duration)
        if p_idle > 0 and idle_data:
            circuit.append("X_ERROR", idle_data, [p_idle])

        if kind == "idle_before_round":
            _append_ticks(circuit, duration)
        elif kind == "cx_left":
            _apply_injected_faults(circuit, injected_faults, "before_round", data, round_index=round_index)
            if noise.p_data_round > 0:
                circuit.append("X_ERROR", data, [noise.p_data_round])
            _append_cx_layer(circuit, left_pairs, p_cx=noise.p_cx)
            _append_ticks(circuit, duration)
        elif kind == "cx_right":
            _append_cx_layer(circuit, right_pairs, p_cx=noise.p_cx)
            _append_ticks(circuit, duration)
        elif kind == "ancilla_measure":
            if noise.p_meas_ancilla > 0:
                circuit.append("X_ERROR", ancilla, [noise.p_meas_ancilla])
            circuit.append("M", ancilla)
            _append_ticks(circuit, duration)

            if int(round_index) == 0:
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
        elif kind == "ancilla_reset":
            circuit.append("R", ancilla)
            if noise.p_reset_ancilla > 0:
                circuit.append("X_ERROR", ancilla, [noise.p_reset_ancilla])
            _append_ticks(circuit, duration)
        elif kind == "idle_tail":
            _append_ticks(circuit, duration)
        else:
            raise RuntimeError(f"Unsupported timeline segment kind: {kind}")

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

    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)

    timelines = timeline["timelines"]
    per_qubit_active = {str(q): int(sum(row["duration"] for row in timelines[q] if row["active"] == 1)) for q in data}
    per_qubit_idle = {str(q): int(sum(row["duration"] for row in timelines[q] if row["idle"] == 1)) for q in data}
    per_qubit_total = {str(q): per_qubit_active[str(q)] + per_qubit_idle[str(q)] for q in data}

    # Structural idle counts idle that is not from user-inserted padding.
    plan = timeline["plan"]
    inserted_idle = int(plan["extra_idle_ticks"])
    structural_idle_total = spec.target_duration_ticks - inserted_idle

    audit = {
        "distance": spec.distance,
        "rounds": spec.rounds,
        "logical_bit": spec.logical_bit,
        "target_duration_ticks": spec.target_duration_ticks,
        "base_duration_ticks": int(plan["base_duration_ticks"]),
        "inserted_idle_ticks": inserted_idle,
        "structural_duration_ticks": structural_idle_total,
        "accounted_total_ticks": spec.target_duration_ticks,
        "idle_tail_ticks": int(plan["idle_tail"]),
        "num_detectors": circuit.num_detectors,
        "num_observables": circuit.num_observables,
        "mwpm_applicable": int(circuit.num_detectors > 0),
        "per_qubit_active_ticks_json": json.dumps(per_qubit_active, sort_keys=True),
        "per_qubit_idle_ticks_json": json.dumps(per_qubit_idle, sort_keys=True),
        "per_qubit_total_ticks_json": json.dumps(per_qubit_total, sort_keys=True),
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

    failure_masks: dict[str, np.ndarray] = {}

    maj_pred = final_data_majority_predictions(measurements, final_cols)
    maj_fail = maj_pred.reshape(-1) != logical_bit
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


def _run_grid(
    output_dir: str | Path,
    *,
    target_duration_ticks: int,
    shots: int,
    seed: int,
    distances: Iterable[int],
    rounds_set: Iterable[int],
    logical_inputs: Iterable[int],
    noise: NoiseModel,
    export_dem: bool,
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
            "p_data_round": noise.p_data_round,
            "p_idle_tick": noise.p_idle_tick,
            "p_cx": noise.p_cx,
            "p_meas_ancilla": noise.p_meas_ancilla,
            "p_reset_ancilla": noise.p_reset_ancilla,
            "p_final_data_meas": noise.p_final_data_meas,
        },
        "export_dem": export_dem,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    timing_rows = []
    method_rows = []
    pairwise_rows = []
    counts_rows = []
    seed_rows = []

    circuit_dir = out_dir / "circuits"
    dem_dir = out_dir / "dem"
    circuit_dir.mkdir(parents=True, exist_ok=True)
    if export_dem:
        dem_dir.mkdir(parents=True, exist_ok=True)

    for d in distances:
        for r in rounds_set:
            for lb in logical_inputs:
                per_case_seed = seed + d * 100 + r * 10 + lb
                spec = FixedDurationSpec(
                    distance=d,
                    rounds=r,
                    logical_bit=lb,
                    target_duration_ticks=target_duration_ticks,
                )
                circuit, audit = build_fixed_duration_memory_circuit(spec=spec, noise=noise)
                circuit_path = circuit_dir / f"d{d}_r{r}_l{lb}.stim"
                circuit_path.write_text(str(circuit), encoding="utf-8")

                if export_dem:
                    dem_path = dem_dir / f"d{d}_r{r}_l{lb}.dem"
                    if circuit.num_detectors > 0:
                        dem = circuit.detector_error_model(decompose_errors=True)
                        dem_path.write_text(str(dem), encoding="utf-8")
                    else:
                        dem_path.write_text("# no detectors for R=0\n", encoding="utf-8")

                timing_rows.append(audit)
                seed_rows.append(
                    {
                        "distance": d,
                        "rounds": r,
                        "logical_bit": lb,
                        "seed": per_case_seed,
                    }
                )

                methods_df, pairwise_df, counts_df = evaluate_fixed_duration_decoders(
                    circuit=circuit,
                    logical_bit=lb,
                    shots=shots,
                    seed=per_case_seed,
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
    pd.DataFrame(seed_rows).to_csv(out_dir / "seeds.csv", index=False)

    return out_dir


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
    return _run_grid(
        output_dir=output_dir,
        target_duration_ticks=target_duration_ticks,
        shots=shots,
        seed=seed,
        distances=distances,
        rounds_set=rounds_set,
        logical_inputs=logical_inputs,
        noise=NoiseModel(),
        export_dem=False,
    )


def run_syndrome_schedule_model_check(
    output_dir: str | Path,
    *,
    target_duration_ticks: int = 30,
    shots: int = 200,
    seed: int = 20261114,
    distances: Iterable[int] = (3, 5),
    rounds_set: Iterable[int] = (0, 1, 3, 5),
    logical_inputs: Iterable[int] = (0, 1),
    noise: NoiseModel | None = None,
) -> Path:
    model_noise = noise or NoiseModel(
        p_data_round=0.002,
        p_idle_tick=0.001,
        p_cx=0.004,
        p_meas_ancilla=0.003,
        p_reset_ancilla=0.002,
        p_final_data_meas=0.002,
    )
    return _run_grid(
        output_dir=output_dir,
        target_duration_ticks=target_duration_ticks,
        shots=shots,
        seed=seed,
        distances=distances,
        rounds_set=rounds_set,
        logical_inputs=logical_inputs,
        noise=model_noise,
        export_dem=True,
    )
