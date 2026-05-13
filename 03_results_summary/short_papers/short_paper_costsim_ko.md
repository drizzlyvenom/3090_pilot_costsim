# 24GB GPU 메모리 제약에서의 Budget-Conditioned Foveated Adapter Residency 비용 시뮬레이션 연구

후속 연구 논의를 위한 1차 소논문 초안

## 초록

피지컬 AI 시스템에서는 perception, planning, verification, world model 계층이 제한된 GPU 메모리를 함께 사용해야 한다. 본 초안은 실제 VLM 학습이나 HydraLoRA 계열 fine-tuning을 수행하기 전에, budget-conditioned foveated adapter residency 정책이 후속 연구 가치가 있는지 비용 시뮬레이션으로 확인한다. RTX 3090 24GB 환경을 기준으로 cost simulator를 만들고, low-resolution global input, full-resolution input, foveated ROI input, independent adapter residency, shared adapter residency, budget-conditioned policy의 여섯 비교군을 평가했다. 총 4,032개 조건에서 대표 조건의 foveated input은 visual token을 75.0% 줄였고, 최종 B7-lite 구조는 full-resolution 기준선 대비 estimated peak memory를 21.9% 줄였다. 또한 shared-bank와 budgeted variant는 independent bank 대비 resident adapter memory를 각각 67.36%, 89.24% 줄였다. 이 결과는 task accuracy를 증명하지는 않지만, 실제 VLM profiling과 LoRA loading 실험을 위한 초기 가능성 근거를 제공한다.

### 핵심어

foveated inference; adapter residency; LoRA; GPU memory; cost simulation; physical AI

## 1. 서론

배치 관점의 피지컬 AI 루프는 가장 큰 비전 모델 하나를 띄우는 문제가 아니다. 실제 시스템에서는 perception 모델이 planner, verifier, orchestration layer, world model이 사용할 메모리 여유를 남겨야 한다. 따라서 이 연구는 어디를 볼지, 어떤 lightweight adapter를 활성화할지, 그리고 언제 유지하거나 내릴지를 메모리 예산 아래에서 결정하는 정책 문제로 접근한다.

제안 방향은 세 가지 생각을 결합한다. 첫째, foveated visual reasoning은 저해상도 전역 관측에서 시작하고 필요한 영역에 대해서만 고해상도 증거를 요청함으로써 입력 비용을 줄인다. 둘째, LoRA 계열 adapter는 국소 skill을 선택적으로 올릴 수 있는 단위로 볼 수 있다. 셋째, HydraLoRA식 공유 구조는 adapter bank의 메모리가 skill 수에 완전히 선형으로 증가하지 않을 가능성을 준다. 본 초안의 질문은 작다. 비싼 모델 학습 전에, 이 구조가 시뮬레이션 상에서 측정 가능한 메모리 비용 이득을 만드는가를 본다.

### 기여

- visual-token cost, adapter resident memory, temporary load buffer, orchestration reserve를 분리한 작은 cost model을 정의했다.

- full-resolution inference와 foveated ROI inference, independent adapter bank와 shared adapter bank를 비교했다.

- budget-conditioned residency가 simulator 안에서 reserve failure를 줄일 수 있음을 stress grid로 확인했다.

## 2. 방법

시뮬레이터는 RTX 3090 24GB 위의 proxy 7B VLM memory profile을 사용한다. 대표 조건은 base model 12GB, orchestration reserve target 4GB, full-resolution 1344 x 1344, global view 336 x 336, ROI crop 336 x 336 세 개, 후보 adapter 16개, active top-k=2로 둔다. visual token은 14픽셀 patch size로 추정한다. 전체 메모리는 base model memory, visual activation/KV proxy cost, resident adapter memory, temporary load buffer, reserve constraint로 계산한다.

비교군은 여섯 개다. B0는 저해상도 global view만 쓴다. B1은 full-resolution 입력을 쓰는 비용 기준선이다. B2는 adapter 없이 ROI crop을 추가한다. B4-lite는 independent adapter bank가 모두 상주한다고 가정한다. B5-lite는 shared common component와 skill별 branch를 가정한다. B7-lite는 reserve target을 넘을 위험이 있으면 top-k를 줄이고, ROI 수를 줄이거나, adapter load를 hold하는 규칙 기반 budget controller를 추가한다.

평가 grid는 세 가지 model profile, 세 가지 reserve target, 여러 해상도, ROI 수, adapter 수, active top-k 값을 포함한다. 측정값은 visual-token count, estimated peak memory, resident adapter memory, reserve pass/fail, load/evict/hold count, latency proxy다. 본 실험은 cost simulation이므로 정확도 주장은 하지 않는다.

## 3. 결과

대표 조건에서 B1 full-resolution 입력은 9216 visual token과 17.30GB estimated peak memory를 사용했다. B2 foveated ROI 입력은 2304 token을 사용해 token 수를 75.0% 줄였다. B7-lite는 13.51GB estimated peak memory를 기록했으며, 이는 B1 대비 21.9% 감소다.

| 비교군 | 토큰 | Peak GB | Adapter GB | Reserve | Latency |
| --- | --- | --- | --- | --- | --- |
| B0 | 576 | 12.07 | 0.00 | pass | 48.3 |
| B1 | 9216 | 17.30 | 0.00 | pass | 143.4 |
| B2 | 2304 | 13.11 | 0.00 | pass | 67.3 |
| B4-lite | 2304 | 16.02 | 2.81 | pass | 103.3 |
| B5-lite | 2304 | 14.12 | 0.92 | pass | 83.3 |
| B7-lite | 2304 | 13.51 | 0.30 | pass | 83.3 |

표 1. 대표 조건의 시뮬레이션 결과.

그림 1. 대표 조건에서 비교군별 estimated peak memory.

adapter residency에서는 구조적 차이가 더 분명하다. B4-lite는 resident adapter memory 2.81GB를 사용했고, B5-lite는 0.92GB, B7-lite는 0.30GB를 사용했다. 전체 grid에서 B4-lite는 reserve failure 396건을 보였지만, B7-lite는 reserve failure 0건을 유지했고 1296건 중 148건에서 top-k, ROI, adapter hold 조정을 수행했다.

## 4. 논의

결과는 두 개의 자원 제어 축을 분리해 볼 수 있음을 보여준다. foveated input selection은 visual token과 activation 계열 비용을 줄이고, shared 또는 budgeted adapter residency는 skill specialization에 묶인 resident memory를 줄인다. 또한 policy formulation이 필요한 이유도 드러난다. naive independent bank는 쉬운 조건에서는 통과하지만, reserve target이 커지거나 model profile이 무거워질수록 실패한다. 반면 budget controller는 adapter 폭이나 ROI 수를 조정해 reserve safety를 확보한다.

### 한계

이 시뮬레이터는 profiler가 아니다. 실제 kernel-level memory allocation, VLM attention behavior, adapter loading overhead, task accuracy를 측정하지 않는다. adapter cost도 1차 가정값이므로 target VLM과 LoRA rank가 정해지면 parameter count 또는 profiler 기반 측정값으로 교체해야 한다. 따라서 본 결과는 성능 주장이라기보다 feasibility note로 해석해야 한다.

### 결론과 다음 단계

24GB GPU cost simulation은 budget-conditioned foveated adapter residency가 실제 모델 실험으로 검증할 가치가 있음을 보여준다. 다음 단계는 작은 VLM을 대상으로 full-resolution 입력과 foveated 입력의 실제 peak memory를 측정하고, simulated adapter table을 실제 LoRA loading/residency cost로 교체하는 것이다. 추가 compute 지원을 받으면 동일 프로토콜을 task accuracy와 co-resident physical-AI module 검증으로 확장할 수 있다.

### 참고문헌

Hu, E. J. 외 (2021). LoRA: Low-Rank Adaptation of Large Language Models. arXiv:2106.09685.

Tian, C. 외 (2024). HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning. arXiv:2404.19245.

Maes, L. 외 (2026). LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels. arXiv:2603.19312.

Davidson, T. R. 외 (2026). Reasoning-Driven Synthetic Data Generation and Evaluation. arXiv:2603.29791.
