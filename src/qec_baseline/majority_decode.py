from typing import Dict


def decode_majority_vote(bitstring: str) -> str:
    cleaned = bitstring.replace(" ", "")
    ones = cleaned.count("1")
    zeros = cleaned.count("0")
    return "1" if ones > zeros else "0"


def logical_success_from_counts(counts: Dict[str, int], expected_logical: str = "0") -> float:
    shots = sum(counts.values())
    if shots == 0:
        return 0.0
    correct = 0
    for bitstring, c in counts.items():
        if decode_majority_vote(bitstring) == expected_logical:
            correct += c
    return correct / shots
