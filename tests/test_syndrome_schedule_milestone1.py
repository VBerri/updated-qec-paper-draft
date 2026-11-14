from __future__ import annotations

import json
from math import comb
from pathlib import Path

import pytest

from qec_stim.syndrome_schedule import (
    FixedDurationSpec,
    InjectedFault,
    NoiseModel,
    build_fixed_duration_memory_circuit,
    evaluate_fixed_duration_decoders,
    odd_flip_probability,
    run_syndrome_schedule_model_check,
    run_syndrome_schedule_smoke,
)


def _method_error(df, method: str) -> float:
    row = df[df["method"] == method]
    assert not row.empty
    return float(row.iloc[0]["logical_error_rate"])


def test_no_noise_correctness_for_required_grid():
    for distance in (3, 5):
        for rounds in (0, 1, 3, 5):
            for logical_bit in (0, 1):
                spec = FixedDurationSpec(
                    distance=distance,
                    rounds=rounds,
                    logical_bit=logical_bit,
                    target_duration_ticks=30,
                )
                circuit, _audit = build_fixed_duration_memory_circuit(spec=spec, noise=NoiseModel())
                methods, _pairwise, _counts = evaluate_fixed_duration_decoders(
                    circuit=circuit,
                    logical_bit=logical_bit,
                    shots=128,
                    seed=4242,
                )
                assert _method_error(methods, "final_data_majority") == 0.0
                if rounds > 0:
                    assert _method_error(methods, "mwpm_oracle_informed") == 0.0


def test_injected_faults_are_deterministic_for_majority():
    base_spec = FixedDurationSpec(distance=3, rounds=0, logical_bit=0, target_duration_ticks=10)

    one_fault = [InjectedFault(stage="before_final_measure", qubit=0, round_index=None)]
    circuit1, _ = build_fixed_duration_memory_circuit(spec=base_spec, noise=NoiseModel(), injected_faults=one_fault)
    methods1, _p1, _c1 = evaluate_fixed_duration_decoders(circuit=circuit1, logical_bit=0, shots=1, seed=7)
    assert _method_error(methods1, "final_data_majority") == 0.0

    two_faults = [
        InjectedFault(stage="before_final_measure", qubit=0, round_index=None),
        InjectedFault(stage="before_final_measure", qubit=2, round_index=None),
    ]
    circuit2, _ = build_fixed_duration_memory_circuit(spec=base_spec, noise=NoiseModel(), injected_faults=two_faults)
    methods2, _p2, _c2 = evaluate_fixed_duration_decoders(circuit=circuit2, logical_bit=0, shots=1, seed=7)
    assert _method_error(methods2, "final_data_majority") == 1.0


def test_logical_bit_vs_observable_scoring_labels():
    spec = FixedDurationSpec(distance=3, rounds=1, logical_bit=1, target_duration_ticks=12)
    circuit, _ = build_fixed_duration_memory_circuit(spec=spec, noise=NoiseModel())
    methods, _pairwise, _counts = evaluate_fixed_duration_decoders(circuit=circuit, logical_bit=1, shots=32, seed=9)

    labels = {row["method"]: row["scoring_target"] for _, row in methods.iterrows()}
    assert labels["final_data_majority"] == "logical_bit"
    assert labels["mwpm_oracle_informed"] == "observable"


def test_time_accounting_and_reject_infeasible_schedule():
    with pytest.raises(ValueError, match="cannot fit"):
        build_fixed_duration_memory_circuit(
            spec=FixedDurationSpec(distance=5, rounds=5, logical_bit=0, target_duration_ticks=5),
            noise=NoiseModel(),
        )

    circuit, audit = build_fixed_duration_memory_circuit(
        spec=FixedDurationSpec(distance=5, rounds=3, logical_bit=0, target_duration_ticks=24),
        noise=NoiseModel(),
    )
    assert circuit.num_observables == 1
    assert int(audit["accounted_total_ticks"]) == 24


def test_odd_flip_probability_matches_binomial_for_small_t():
    p_tick = 0.07
    for ticks in range(1, 7):
        expected = 0.0
        for k in range(1, ticks + 1, 2):
            expected += comb(ticks, k) * (p_tick**k) * ((1 - p_tick) ** (ticks - k))
        assert odd_flip_probability(p_tick, ticks) == pytest.approx(expected, rel=0, abs=1e-12)


def test_structural_idle_noise_is_applied_without_inserted_padding():
    spec = FixedDurationSpec(distance=3, rounds=1, logical_bit=0, target_duration_ticks=4)
    circuit, audit = build_fixed_duration_memory_circuit(
        spec=spec,
        noise=NoiseModel(
            p_data_round=0.0,
            p_idle_tick=0.1,
            p_cx=0.0,
            p_meas_ancilla=0.0,
            p_reset_ancilla=0.0,
            p_final_data_meas=0.0,
        ),
    )
    assert int(audit["inserted_idle_ticks"]) == 0

    x_error_ops = [
        op
        for op in circuit.flattened().flattened_operations()
        if op[0] == "X_ERROR"
    ]
    # round1 has structural idles in cx_left, cx_right, anc_measure, anc_reset
    assert len(x_error_ops) >= 4


def test_per_qubit_timing_budget_for_rounds_and_logical_inputs():
    for rounds in (0, 1, 3, 5):
        audits = {}
        for logical_bit in (0, 1):
            spec = FixedDurationSpec(distance=5, rounds=rounds, logical_bit=logical_bit, target_duration_ticks=30)
            _circuit, audit = build_fixed_duration_memory_circuit(spec=spec, noise=NoiseModel())
            total = json.loads(str(audit["per_qubit_total_ticks_json"]))
            active = json.loads(str(audit["per_qubit_active_ticks_json"]))
            idle = json.loads(str(audit["per_qubit_idle_ticks_json"]))
            for q in total:
                assert int(total[q]) == 30
                assert int(active[q]) + int(idle[q]) == 30
            audits[logical_bit] = (total, active, idle)
        # Timing budget is schedule-defined and must not depend on prepared logical bit.
        assert audits[0] == audits[1]


def test_round_zero_has_no_mwpm_and_smoke_outputs(tmp_path: Path):
    spec = FixedDurationSpec(distance=3, rounds=0, logical_bit=1, target_duration_ticks=8)
    circuit, audit = build_fixed_duration_memory_circuit(spec=spec, noise=NoiseModel())
    assert int(audit["num_detectors"]) == 0

    methods, pairwise, _counts = evaluate_fixed_duration_decoders(circuit=circuit, logical_bit=1, shots=16, seed=3)
    assert set(methods["method"]) == {"final_data_majority"}
    assert pairwise.empty

    out_dir = run_syndrome_schedule_smoke(output_dir=tmp_path / "smoke", shots=20, seed=111, target_duration_ticks=24)
    assert (out_dir / "config.json").exists()
    assert (out_dir / "timing_audit.csv").exists()
    assert (out_dir / "decoder_metrics.csv").exists()
    assert (out_dir / "counts.csv").exists()


def test_model_check_exports_dem_and_seeds(tmp_path: Path):
    out_dir = run_syndrome_schedule_model_check(
        output_dir=tmp_path / "model_check",
        shots=20,
        seed=222,
        target_duration_ticks=24,
    )
    assert (out_dir / "config.json").exists()
    assert (out_dir / "timing_audit.csv").exists()
    assert (out_dir / "counts.csv").exists()
    assert (out_dir / "seeds.csv").exists()
    assert (out_dir / "dem" / "d3_r0_l0.dem").exists()
    assert (out_dir / "dem" / "d5_r5_l1.dem").exists()
