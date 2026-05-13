# 3090 VRAM Cost Simulation 실험 계획서

작성일: 2026-05-13  
목표: 실제 VLM 학습 없이 cost simulator 기반으로 실험 계획서, 실행 결과, 결과 보고서 DOCX/PDF를 생성한다.

## 1. 실험 목적

이번 파일럿은 `Budget-Conditioned Foveated Adapter Policy`가 실제로 VRAM 절약 구조를 만들 가능성이 있는지 확인하기 위한 0차 검증이다.

아직 실제 VLM 학습, LoRA 학습, HydraLoRA 전체 구현은 하지 않는다. 대신 다음 비용 요소를 숫자 기반으로 분해한다.

- full-resolution vision input의 visual token 비용
- low-resolution global view + ROI crop의 visual token 비용
- independent adapter bank의 resident memory
- HydraLoRA-style shared bank의 resident memory
- budget-conditioned keep / evict / hold policy가 reserve pass rate에 주는 영향

## 2. 실행 환경

기본 가정:

- GPU: NVIDIA GeForce RTX 3090
- VRAM: 24GB
- runtime budget: 22.5GB 내외
- orchestration reserve target: 2GB, 4GB, 6GB

실행 시점에 `torch.cuda`와 `nvidia-smi`로 실제 GPU 인식 여부를 확인하고, 결과 파일에 기록한다.

## 3. 비교군

| ID | 이름 | 의미 |
| --- | --- | --- |
| B0 | Low-res only | 작은 global view만 처리 |
| B1 | Full-res | full-resolution 입력을 처리하는 비용 기준선 |
| B2 | Foveated ROI | low-res global + K개 ROI crop |
| B4-lite | Independent bank | 모든 independent adapter가 상주한다고 가정 |
| B5-lite | Shared bank | shared common + skill branch 구조가 상주한다고 가정 |
| B7-lite | Budget policy | shared bank에서 budget에 따라 top-k, ROI, adapter load를 조절 |

`lite`는 실제 LoRA weight를 로드하지 않고 cost table로 계산한다는 뜻이다.

## 4. 주요 변수

| 변수 | 값 |
| --- | --- |
| model profile | compact 7B proxy, mid 7B proxy, heavy 13B proxy |
| full-res | 1024 x 1024, 1344 x 1344 |
| global view | 336 x 336, 448 x 448 |
| ROI crop | 336 x 336, 448 x 448 |
| ROI count K | 1, 3, 5 |
| adapter count N | 4, 8, 16, 32 |
| active top-k | 1, 2, 4 |
| reserve target | 2GB, 4GB, 6GB |

보고서 대표 조건은 `mid_7b_vlm`, reserve 4GB, full-res 1344, global 336, ROI 336, K=3, N=16, top-k=2로 둔다.

## 5. 측정 항목

- visual token count
- estimated visual memory
- resident adapter memory
- estimated peak memory
- orchestration reserve pass/fail
- load / evict / hold count
- latency proxy
- budget policy decision trace

## 6. 성공 기준

1차 성공 기준:

- B1 대비 B2 또는 B7-lite의 visual token 수와 estimated peak memory가 감소한다.
- B4-lite 대비 B5-lite의 resident adapter memory가 감소한다.
- B7-lite가 B4/B5보다 reserve pass rate를 높이거나 peak violation을 줄인다.
- 결과가 CSV/JSONL/그래프/보고서 형태로 재현 가능하게 남는다.

실패해도 의미 있는 기준:

- token은 줄었지만 peak memory가 줄지 않으면 base model/KV cache 병목이 더 크다는 근거가 된다.
- adapter memory는 줄었지만 latency proxy가 튀면 residency hysteresis가 필요하다는 근거가 된다.
- reserve target 6GB에서 실패가 많으면 추가 GPU 지원 필요성을 설명할 수 있다.

## 7. 산출물

예상 산출물:

- `02_simulation_run/config/simulation_config.json`
- `02_simulation_run/config/adapter_cost_table.json`
- `02_simulation_run/scripts/run_costsim_pipeline.py`
- `02_simulation_run/results/results.jsonl`
- `02_simulation_run/results/summary.csv`
- `02_simulation_run/results/aggregate_summary.csv`
- `03_results_summary/figures/primary_peak_memory_bars.png`
- `03_results_summary/figures/primary_adapter_memory_bars.png`
- `03_results_summary/figures/reserve_pass_rate.png`
- `03_results_summary/technical_report/results_report_ko.md`
- `03_results_summary/technical_report/results_report_ko.docx`
- `03_results_summary/technical_report/results_report_ko.pdf`
- `03_results_summary/short_papers/short_paper_costsim_en.docx`
- `03_results_summary/short_papers/short_paper_costsim_en.pdf`
- `03_results_summary/short_papers/short_paper_costsim_ko.docx`
- `03_results_summary/short_papers/short_paper_costsim_ko.pdf`

