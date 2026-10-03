from math import comb


def effective_error_over_idle_steps(p: float, idle_steps: int = 4) -> float:
    """Effective single-qubit flip probability after repeated iid flip opportunities."""
    return 0.5 * (1 - (1 - 2 * p) ** idle_steps)


def repetition_fail_probability(code_size: int, p_eff: float) -> float:
    threshold = (code_size + 1) // 2
    fail = 0.0
    for k in range(threshold, code_size + 1):
        fail += comb(code_size, k) * (p_eff**k) * ((1 - p_eff) ** (code_size - k))
    return fail


def repetition_success_probability(code_size: int, p: float, idle_steps: int = 4) -> float:
    p_eff = effective_error_over_idle_steps(p, idle_steps=idle_steps)
    return 1.0 - repetition_fail_probability(code_size, p_eff)
