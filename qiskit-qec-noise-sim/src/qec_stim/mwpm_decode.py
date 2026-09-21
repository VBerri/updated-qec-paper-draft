from __future__ import annotations

import numpy as np
import pymatching
import stim


def matching_from_circuit(circuit: stim.Circuit, weight_mode: str = "detector_model") -> pymatching.Matching:
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    if weight_mode == "detector_model":
        return matching
    if weight_mode != "uniform":
        raise ValueError("weight_mode must be 'detector_model' or 'uniform'")

    uniform_matching = pymatching.Matching()
    for u, v, data in matching.edges():
        kwargs = {
            "fault_ids": data["fault_ids"],
            "weight": 1.0,
            "error_probability": data.get("error_probability", None),
        }
        if v is None:
            uniform_matching.add_boundary_edge(u, **kwargs)
        else:
            uniform_matching.add_edge(u, v, **kwargs)
    return uniform_matching


def decode_logical_error_rate(circuit: stim.Circuit, shots: int) -> float:
    matching = matching_from_circuit(circuit, weight_mode="detector_model")
    sampler = circuit.compile_detector_sampler()
    syndrome, actual_observables = sampler.sample(shots, separate_observables=True)
    predicted_observables = matching.decode_batch(syndrome)
    return float(np.mean(predicted_observables != actual_observables))


def decode_batch(circuit: stim.Circuit, shots: int):
    sampler = circuit.compile_detector_sampler()
    syndrome, actual_observables = sampler.sample(shots, separate_observables=True)
    matching = matching_from_circuit(circuit, weight_mode="detector_model")
    predicted_observables = matching.decode_batch(syndrome)
    return syndrome, actual_observables, predicted_observables


def decode_with_weight_mode(circuit: stim.Circuit, shots: int, weight_mode: str):
    sampler = circuit.compile_detector_sampler()
    syndrome, actual_observables = sampler.sample(shots, separate_observables=True)
    predicted_observables = decode_syndrome_batch(circuit, syndrome, weight_mode=weight_mode)
    return syndrome, actual_observables, predicted_observables


def decode_syndrome_batch(circuit: stim.Circuit, syndrome: np.ndarray, weight_mode: str):
    matching = matching_from_circuit(circuit, weight_mode=weight_mode)
    return matching.decode_batch(syndrome)
