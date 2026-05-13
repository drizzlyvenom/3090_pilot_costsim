# A Cost-Simulation Feasibility Study of Budget-Conditioned Foveated Adapter Residency under 24GB GPU Memory

Preliminary short-paper draft for research discussion

## Abstract

Physical-AI systems often require perception, planning, verification, and world-model components to share a limited GPU memory budget. This note evaluates whether a budget-conditioned foveated adapter residency policy is worth pursuing before implementing full VLM training or HydraLoRA-style fine-tuning. We build a cost simulator for an RTX 3090 24GB environment and compare six baselines: low-resolution global input, full-resolution input, foveated ROI input, independent adapter residency, shared adapter residency, and a budget-conditioned policy. Across 4,032 simulated configurations, the foveated input reduced visual tokens by 75.0% in the primary case, while the final budgeted variant reduced estimated peak memory by 21.9% relative to full-resolution input. The shared-bank and budgeted variants reduced resident adapter memory by 67.36% and 89.24%, respectively, compared with an independent bank. These results do not establish task accuracy, but they provide a compact feasibility signal for requesting resources for real VLM profiling and LoRA loading experiments.

### Keywords

foveated inference; adapter residency; LoRA; GPU memory; cost simulation; physical AI

## 1. Introduction

A deployment-oriented physical-AI loop is not only a question of running the largest possible vision model. In a practical stack, a perception model must leave memory for planning, verification, orchestration, and possibly a world model. This motivates a policy view: the system should decide where to look, which lightweight adapter to activate, and when to keep or evict that adapter under a memory budget.

The proposed direction combines three ideas. First, foveated visual reasoning reduces input cost by starting with a low-resolution global observation and requesting high-resolution evidence only for selected regions. Second, LoRA-style adapters represent local skills that may be loaded selectively. Third, HydraLoRA-style sharing suggests that adapter banks need not scale linearly with the number of skills. The central question of this note is therefore modest: before expensive model training, does the structure produce a measurable memory-cost advantage in simulation?

### Contributions

- We define a small cost model that separates visual-token cost, adapter resident memory, temporary load buffers, and orchestration reserve.

- We compare full-resolution inference against foveated ROI inference and independent adapter banks against shared adapter banks.

- We report an initial stress-grid result showing that budget-conditioned residency can eliminate reserve failures in this simulator.

## 2. Method

The simulator uses a proxy 7B VLM memory profile on an RTX 3090 24GB GPU. The primary case assumes a 12GB base model, a 4GB orchestration reserve target, a 1344 x 1344 full-resolution input, a 336 x 336 global view, three 336 x 336 ROI crops, sixteen candidate adapters, and top-k=2 active adapters. Visual tokens are estimated from a 14-pixel patch size. Memory is modeled as base model memory plus visual activation/KV proxy cost, resident adapter memory, temporary load buffer, and reserve constraints.

Six baselines are evaluated. B0 uses only the low-resolution global view. B1 uses full-resolution input and serves as the expensive reference. B2 adds ROI crops without adapters. B4-lite assumes an independent adapter bank in which all candidate adapter weights are resident. B5-lite assumes a shared common component plus per-skill branches. B7-lite adds a rule-based budget controller that reduces top-k, reduces ROI count, or holds adapter loading when the reserve target would be violated.

The evaluation grid spans three model profiles, three reserve targets, multiple input resolutions, ROI counts, adapter counts, and active top-k values. The output metrics are visual-token count, estimated peak memory, resident adapter memory, reserve pass/fail, load/evict/hold counts, and a latency proxy. Because this is a cost simulation, no accuracy claim is made.

## 3. Results

In the primary case, B1 full-resolution input used 9216 visual tokens and 17.30GB estimated peak memory. B2 foveated ROI input used 2304 tokens, a 75.0% token reduction. B7-lite reached 13.51GB estimated peak memory, a 21.9% reduction relative to B1.

| Baseline | Tokens | Peak GB | Adapter GB | Reserve | Latency |
| --- | --- | --- | --- | --- | --- |
| B0 | 576 | 12.07 | 0.00 | pass | 48.3 |
| B1 | 9216 | 17.30 | 0.00 | pass | 143.4 |
| B2 | 2304 | 13.11 | 0.00 | pass | 67.3 |
| B4-lite | 2304 | 16.02 | 2.81 | pass | 103.3 |
| B5-lite | 2304 | 14.12 | 0.92 | pass | 83.3 |
| B7-lite | 2304 | 13.51 | 0.30 | pass | 83.3 |

Table 1. Primary-case simulation results.

Figure 1. Estimated peak memory by baseline in the primary case.

Adapter residency shows the clearest structural separation. B4-lite used 2.81GB resident adapter memory, B5-lite used 0.92GB, and B7-lite used 0.30GB. In the full grid, B4-lite produced 396 reserve failures, whereas B7-lite produced 0 reserve failures and adjusted 148 of 1296 runs through top-k, ROI, or adapter-hold decisions.

## 4. Discussion

The result supports the feasibility of separating two resource-control levers: foveated input selection reduces visual-token and activation-related cost, while shared or budgeted adapter residency reduces memory tied to skill specialization. The simulation also shows why a policy formulation is useful. A naive independent bank can pass in easy settings but fail under larger reserve targets or heavier model profiles. A budget controller can trade adapter breadth or ROI count for reserve safety.

### Limitations

The simulator is not a profiler. It does not measure kernel-level memory allocation, real VLM attention behavior, adapter loading overhead, or task accuracy. The adapter costs are first-pass assumptions and must be replaced with parameter-count-derived or profiler-derived measurements once a target VLM and LoRA rank are selected. Therefore, the present result should be treated as a feasibility note, not as a performance claim.

### Conclusion and Next Step

The 24GB GPU cost simulation indicates that budget-conditioned foveated adapter residency is worth validating with real model runs. The immediate next step is to profile a small VLM under full-resolution and foveated inputs, then replace the simulated adapter table with measured LoRA loading and residency costs. If supported by additional compute resources, the same protocol can be extended to real task accuracy and co-resident physical-AI modules.

### References

Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. arXiv:2106.09685.

Tian, C. et al. (2024). HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning. arXiv:2404.19245.

Maes, L. et al. (2026). LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels. arXiv:2603.19312.

Davidson, T. R. et al. (2026). Reasoning-Driven Synthetic Data Generation and Evaluation. arXiv:2603.29791.
