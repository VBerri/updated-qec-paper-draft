# From Baseline Repetition Codes to Detector-Aware Decoding and IBM Hardware Validation

## Abstract

We study repetition-code quantum memory in three connected stages: an original baseline simulation, a circuit-level Stim decoder comparison, and a constrained IBM Quantum hardware validation. The first stage establishes the primary scientific claim that increasing the code size improves logical success under bit-flip, phase-flip, and depolarizing noise. The second stage evaluates how strongly decoder choice alters performance when the same repetition-memory idea is represented in a detector-model circuit-level setting. The third stage tests whether the same underlying logic remains stable under a minimal real-device execution protocol. These stages are not competing datasets; they are cumulative layers of the same investigation. The original baseline remains the foundation of the work, while the later Stim and hardware experiments deepen the interpretation by showing that decoder quality and practical device execution are essential ingredients alongside code size.

## 1. Introduction

Quantum error correction is required because qubits are highly susceptible to environmental noise and imperfect control. Repetition codes are among the simplest and most informative testbeds for studying the effectiveness of redundancy in quantum memory. By encoding a logical degree of freedom across multiple physical qubits, repetition codes allow the system to suppress the effect of local noise and recover the intended state through decoding.

This project began with an original Qiskit Aer baseline designed to test a basic repetition-code prediction: larger codes should reduce logical failure probability under realistic noise models. That baseline was subsequently extended in two directions. First, the project moved to Stim-generated circuit-level simulations and compared majority-vote decoding against detector-model matching. Second, a minimal hardware validation was executed on IBM Quantum hardware to evaluate whether the same logic survives real cloud execution under controlled runtime conditions.

The manuscript is therefore organized as a three-stage study. The first stage establishes the baseline claim. The second stage quantifies the contribution of decoder quality in a realistic detector model. The third stage checks whether the same qualitative behavior remains stable in hardware. This structure makes the scientific logic explicit: the baseline defines the physical trend, the decoder comparison measures how much algorithmic information matters, and the hardware check tests whether the workflow remains operational in a real-device setting.

## 2. Data provenance and experiment structure

The experiments in this paper were generated in separate but related stages. The original baseline was created first and is preserved in the project’s baseline outputs. The Stim decoder comparison was then added as a more realistic extension using detector-model decoding. The IBM hardware validation was performed last as a practical device-level check. The data from each stage are stored separately in the project repository, which makes the distinction between the original baseline evidence and the later extension evidence explicit.

This provenance matters because it keeps the scientific story honest. The baseline result is not replaced by the later results; rather, the later results refine and extend the interpretation of the same underlying phenomenon.

## 3. Stage 1: original Qiskit Aer baseline

The original baseline study used Qiskit Aer to compare the unprotected single-qubit case against 3-qubit and 5-qubit repetition codes. The circuits used the standard repetition-code encoding under bit-flip, phase-flip, and depolarizing noise. The dominant measurement was the logical success probability as a function of the physical error rate $p$.

The original public baseline repository reproduces the expected ordering of performance: the 5-qubit repetition code outperformed the 3-qubit code, and both outperformed the unprotected baseline. At a representative physical error rate near $p = 0.10$, the baseline values remained substantially lower than the repetition-code values, while the 5-qubit case consistently achieved the highest logical success. This was the core original result of the project and remains the foundation of the current manuscript.

The baseline also showed the expected symmetry between X- and Z-type errors. The bit-flip and phase-flip experiments produced nearly identical performance trends when the logical qubit was encoded in the correct basis. Under depolarizing noise, the repetition encoding continued to improve logical success even though the noise channel contained both X and Z error components.

In short, the original baseline study established the main phenomenon: repetition coding improves logical reliability as the code size increases.

## 4. Stage 2: Stim decoder comparison

The second stage moved from simple majority decoding to a more realistic detector-model decoding approach. Instead of interpreting raw measurement outcomes with a simple majority rule, the Stim circuits were converted into a detector error model and decoded using a minimum-weight perfect matching algorithm.

This stage was designed to answer a different but related question: how much of the observed performance difference comes from code size, and how much comes from decoder quality? The answer is substantial. The comparison showed that a detector-aware decoder greatly reduces the logical error rate relative to a simple majority-vote decoder, even when the underlying repetition-memory circuit family is otherwise comparable.

For example, at distance 11 and $p = 0.02$, the majority-vote decoder produced a logical error rate near 0.2244, while the detector-model MWPM decoder reduced the error rate to approximately 0.0006. This more than two-order-of-magnitude improvement demonstrates that decoder design is not a secondary detail; it is a major determinant of logical performance in realistic syndrome-based settings.

The unweighted MWPM comparison further clarified the point. Because the weighted detector-model decoder uses syndrome-graph information more effectively than the unweighted variant, it provides a cleaner indication that the decoder should be interpreted as part of the physical performance story, not as a post-processing afterthought.

## 5. Stage 3: IBM hardware validation

The third stage tested a constrained hardware implementation on IBM Quantum hardware. The hardware protocol used a minimal repetition-memory setting with three validation circuits and 1000 shots per circuit. The same core validation was repeated across three hardware jobs on backend `ibm_fez`.

The measured hardware outcomes were highly stable. The latest run reported logical-success probabilities of 0.999 for `z_idle_2`, 1.000 for `z_idle_4`, and 1.000 for `x_idle_4`. Across the three runs, the maximum per-circuit run-to-run variation was only 0.001. This suggests that the cloud execution path is operational and that the measurement process remains stable on this reduced test circuit set.

This stage does not claim a full hardware threshold or a large-scale benchmark. Instead, it demonstrates that the same repetition-memory concept remains feasible under a real hardware execution environment, and that the workflow is stable enough to be treated as a meaningful device-level validation of the local theory.

## 6. Comparison across the three stages

The three stages can be compared directly as follows.

First, the original Qiskit baseline establishes the fundamental repetition-code claim: larger codes improve logical success under common noise models. Second, the Stim decoder comparison shows that the same repetition-memory idea performs very differently when the detector information is used more effectively. Third, the IBM hardware validation demonstrates that the logical behavior remains stable under a real cloud execution path, even when the circuit family is intentionally small and constrained.

Taken together, the stages form a layered argument. The baseline shows the effect of redundancy. The Stim stage shows the effect of structured decoding. The hardware stage shows the effect of device execution under realistic constraints. Each stage addresses a different question, but each is consistent with the same underlying scientific theme: repetition-coded memory is a meaningful and interpretable candidate for error correction, and the performance depends on both encoding and decoding choices.

### 6.1 Direct comparison basis

To avoid an apples-to-oranges interpretation, we compare all three stages on a shared basis:
1. Same physical objective: preserve logical information in a repetition-memory setting.
2. Same family-level control variable: larger code distance or size should reduce logical failure.
3. Same outcome axis: logical success or logical error.
4. Same interpretation rule: compare directional trends and effect sizes, not raw absolute numbers across different execution models.

Under this basis, the three-stage comparison is:
1. Baseline (Qiskit Aer): establishes that redundancy improves logical reliability across bit-flip, phase-flip, and depolarizing channels.
2. Stim extension: quantifies how much additional performance depends on decoder quality once detector-graph structure is available.
3. Hardware extension: checks whether the same qualitative behavior and pipeline integrity survive real-device execution constraints.

### 6.2 Why Stim and hardware were necessary

The original baseline answered an important first question, but not the full experimental question.

Why Stim was necessary:
1. The baseline primarily compared channel variants and code sizes; it did not isolate decoder-information effects under detector-model circuitry.
2. Stim plus MWPM enables a circuit-level detector representation, which makes decoder-quality comparisons scientifically explicit.
3. This stage separates two sources of improvement that were previously coupled: encoding redundancy versus decoding sophistication.

Why hardware was necessary:
1. Simulation evidence alone cannot establish workflow viability under cloud runtime constraints.
2. Hardware runs test execution stability, metadata capture, and repeatability in a real backend context.
3. This stage provides practical validation that the method is operational beyond local simulation.

In this framing, Stim and hardware are not replacements of the original trials. They are required follow-on stages that answer two additional questions left open by the baseline: how much performance comes from better decoding, and whether the pipeline remains stable on real devices.

### 6.3 Explicit pairwise comparisons

For direct readability, we include two explicit pairwise comparisons on a common logical-error basis.

Stim vs Aer (simulation-to-simulation):
1. Shared basis: logical error rate versus physical error rate $p$.
2. Matched scale slice: Aer bit-flip $n=3$ versus Stim MWPM distance $d=3$.
3. Interpretation: this isolates the effect of simulation model and decoding assumptions while keeping code scale comparable.

Aer vs hardware (simulation-to-device):
1. Shared basis: logical error rate (lower is better).
2. Hardware points: measured logical error from constrained device circuits (`z_idle_2`, `z_idle_4`, `x_idle_4`).
3. Simulation anchors: Aer and Stim reference values at $p=0.01$ to provide context, not one-to-one equivalence.

The combined visualization is provided in `figures/aer_stim_hardware_comparison.png`. This figure is intentionally framed as a trend-and-context comparison, not a strict threshold-style benchmark, because circuit structure and execution conditions differ across layers.

## 7. Data integrity and scientific framing

The project preserves its evidence in separate saved artifacts. The original baseline results are in the baseline output tables from the public Qiskit project, while the later Stim and hardware results are stored separately in the project’s CSV and JSON outputs. This separation is important because it allows the paper to present the original baseline results as the first, primary evidence without suggesting that the later work replaced or erased the earlier results.

The scientific framing is therefore intentionally cumulative rather than adversarial. The baseline results were not discarded; they were the initial evidence. The Stim and hardware results were added later to test the same physical idea at a higher level of realism.

## 8. Discussion and limitations

This study has several limitations. The repetition code is intentionally simple and protects a restricted logical subspace. The original baseline assumes independent noise and does not capture all hardware non-idealities. The Stim decoder stage is more realistic but still evaluates a limited circuit family. The hardware stage is intentionally constrained to a tiny validation set and should not be interpreted as a large-scale hardware demonstration.

Still, the combination of all three stages is scientifically useful because it separates three distinct sources of improvement: code size, decoder quality, and hardware execution stability. This is the central value of the project.

## 9. Conclusion

This paper presents a three-stage study of repetition-code quantum memory. The original baseline shows that increasing code size improves logical success under common noise models. The Stim decoder comparison shows that detector-aware decoding can materially change performance in realistic circuit-level simulations. The IBM hardware validation shows that the same underlying logic remains stable under a constrained cloud-execution setting.

The manuscript should therefore be interpreted as a layered comparison of connected evidence rather than as a single merged dataset. The original baseline remains the primary evidence, while the Stim and hardware extensions deepen the interpretation by showing that the underlying effect is robust across simulation fidelity and real-device execution. The study is most convincing when the three stages are viewed together: redundancy matters, decoder quality matters, and real-device execution remains feasible under controlled conditions.

## 10. Future work

The natural next step is to expand the hardware validation to multiple backends and higher shot counts to quantify device-to-device variability more systematically. A broader decoder comparison could also evaluate additional matching strategies and learned decoding methods against the same repetition-memory circuits. Such work would sharpen the separation between the gains produced by encoding itself, the gains produced by the decoder, and the gains or losses associated with real hardware execution.
