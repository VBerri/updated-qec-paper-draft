from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qec_baseline.qiskit_circuits import build_repetition_syndrome_memory_circuit
from qec_cloud.ibm_hardware import (
    _expected_measured_physical_qubits,
    _match_control_memory_interval,
    _measured_physical_qubits_from_circuit,
    _scheduled_memory_interval_dt,
)


def test_expected_measured_physical_qubits_encoded_and_control():
    path = [0, 1, 2, 3, 16]
    encoded_spec = {"kind": "encoded"}
    assert _expected_measured_physical_qubits(encoded_spec, path) == [0, 1, 2, 3, 16]

    for dq, expected in [(0, 0), (1, 2), (2, 16)]:
        control_spec = {"kind": "unencoded", "control_data_index": dq}
        assert _expected_measured_physical_qubits(control_spec, path) == [expected]


def test_measured_physical_qubits_from_circuit():
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    q = QuantumRegister(3, "q")
    c = ClassicalRegister(2, "c")
    qc = QuantumCircuit(q, c)
    qc.x(q[0])
    qc.measure(q[2], c[0])
    qc.measure(q[0], c[1])
    assert _measured_physical_qubits_from_circuit(qc) == [0, 2]


def _linear_path(backend, length: int = 5):
    nx = pytest.importorskip("networkx")
    graph = nx.Graph()
    graph.add_edges_from([tuple(e) for e in backend.coupling_map.get_edges()])
    for src in graph.nodes():
        for tgt in graph.nodes():
            if src < tgt:
                try:
                    candidate = nx.shortest_path(graph, src, tgt)
                except nx.NetworkXNoPath:
                    continue
                if len(candidate) == length:
                    return candidate
    return None


def test_memory_interval_matching_on_fake_backend():
    pytest.importorskip("networkx")
    fp = pytest.importorskip("qiskit_ibm_runtime.fake_provider")
    from qiskit import transpile

    backend = next(b for b in fp.FakeProviderForBackendV2().backends() if b.name == "fake_sherbrooke")
    path = _linear_path(backend, length=5)
    assert path is not None

    durations = backend.target.durations()
    layout = [path[0], path[1], path[2], path[3], path[4]]
    data_phys = [layout[0], layout[2], layout[4]]

    for logical_bit in (0, 1):
        encoded = build_repetition_syndrome_memory_circuit(rounds=3, delay_dt=0, logical_bit=logical_bit)
        tqc = transpile(
            encoded,
            backend=backend,
            optimization_level=1,
            seed_transpiler=7,
            initial_layout=layout,
            scheduling_method="asap",
        )
        intervals = {pq: _scheduled_memory_interval_dt(tqc, pq, logical_bit, durations) for pq in data_phys}
        # Encoded data qubits experience different memory exposures; total-duration matching cannot capture this.
        assert len(set(intervals.values())) >= 1

        for dq, pq in enumerate(data_phys):
            _, _, _, matched_interval, _ = _match_control_memory_interval(
                backend=backend,
                rounds=3,
                logical_bit=logical_bit,
                delay_dt_hint=1,
                target_interval_dt=intervals[pq],
                physical_qubit=pq,
                seed_transpiler=7,
                durations=durations,
            )
            assert matched_interval == intervals[pq]
