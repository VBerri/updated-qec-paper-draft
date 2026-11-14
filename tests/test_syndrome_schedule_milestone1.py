from __future__ import annotations

from pathlib import Path

import pytest

from qec_stim.syndrome_schedule import (
    FixedDurationSpec,
    InjectedFault,
    NoiseModel,
    build_fixed_duration_memory_circuit,
    evaluate_fixed_duration_decoders,
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
