# RTX 3090 기반 VRAM Cost Simulation 결과 보고서

작성일: 2026-05-13

## 1. 요약

이번 파일럿은 실제 VLM 학습 없이 숫자 기반 cost simulator로 `Budget-Conditioned Foveated Adapter Policy`의 비용 절감 가능성을 확인했다.

- B1 full-res 대비 B2 foveated ROI는 visual token을 75.0% 줄였다.
- 대표 조건에서 B1 대비 B7-lite의 estimated peak memory 감소율은 21.9%였다.
- B4-lite independent bank 대비 B5-lite shared bank의 resident adapter memory 감소율은 67.36%였다.
- B4-lite 대비 B7-lite budget policy의 resident adapter memory 감소율은 89.24%였다.
- 전체 grid에서 B4-lite는 reserve fail 396건을 보였고, B7-lite는 fail 0건으로 유지됐다.
- B7-lite는 1296건 중 148건에서 top-k/ROI/adapter hold 조정을 수행했다.

따라서 이 구조는 최소한 비용 모델 상에서 `full-res 입력 비용 절감`과 `adapter resident memory 절감`이라는 두 축을 분리해서 보여줄 수 있다.

## 2. 실행 환경 확인

```json
{
  "checked_at": "2026-05-13T18:33:27",
  "nvidia_smi": "NVIDIA GeForce RTX 3090, 24576 MiB, 596.21",
  "torch": {
    "torch_version": "1.13.1+cu117",
    "cuda_available": true,
    "device_name": "NVIDIA GeForce RTX 3090",
    "total_memory_mb": 24575.5,
    "free_memory_mb_before": 23336.0,
    "sanity_note": "CUDA device was detected; allocation stress test was skipped to keep the report run non-invasive."
  },
  "cuda_sanity_allocation": null,
  "errors": []
}
```

## 3. 대표 조건 결과표

| baseline | visual tokens | peak GB | adapter GB | reserve | load | evict | latency proxy ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 576 | 12.07 | 0.00 | pass | 0 | 0 | 48.3 |
| B1 | 9216 | 17.30 | 0.00 | pass | 0 | 0 | 143.4 |
| B2 | 2304 | 13.11 | 0.00 | pass | 0 | 0 | 67.3 |
| B4-lite | 2304 | 16.02 | 2.81 | pass | 2 | 0 | 103.3 |
| B5-lite | 2304 | 14.12 | 0.92 | pass | 2 | 0 | 83.3 |
| B7-lite | 2304 | 13.51 | 0.30 | pass | 2 | 0 | 83.3 |

## 4. Reserve Pass Rate 요약

| baseline | runs | pass rate | mean peak GB | mean adapter GB |
| --- | --- | --- | --- | --- |
| B0 | 2 | 100.0% | 12.20 | 0.00 |
| B1 | 2 | 100.0% | 16.17 | 0.00 |
| B2 | 12 | 100.0% | 13.66 | 0.00 |
| B4-lite | 144 | 81.2% | 16.39 | 2.64 |
| B5-lite | 144 | 100.0% | 14.62 | 0.87 |
| B7-lite | 144 | 100.0% | 14.09 | 0.32 |

## 5. 그래프

![Estimated Peak Memory](C:/Users/user/Documents/New project 2/output/experiment/3090_pilot_costsim/03_results_summary/figures/primary_peak_memory_bars.png)

![Resident Adapter Memory](C:/Users/user/Documents/New project 2/output/experiment/3090_pilot_costsim/03_results_summary/figures/primary_adapter_memory_bars.png)

![Reserve Pass Rate](C:/Users/user/Documents/New project 2/output/experiment/3090_pilot_costsim/03_results_summary/figures/reserve_pass_rate.png)

## 6. 해석

1차 결과는 foveated ROI 구조가 full-resolution 기준선보다 visual token과 peak memory를 줄일 수 있음을 보여준다. 특히 B2는 adapter를 전혀 쓰지 않아도 입력 비용 절감 축을 분리해서 확인할 수 있다.

adapter 측면에서는 independent bank를 모두 상주시킨 B4-lite가 adapter 수에 따라 resident memory가 빠르게 커진다. 반면 B5-lite는 shared common과 branch 구조를 가정하기 때문에 같은 adapter count에서도 resident memory 증가율이 낮다.

B7-lite의 대표 policy trace는 `allow_initial_plan`이다. 대표 조건에서는 초기 계획이 budget 안에 들어왔지만, 전체 grid에서는 148건에서 reduce_top_k, reduce_roi_count, hold_adapter_load 같은 조정 행동이 실제로 기록되었다.

## 7. 한계

- 이 결과는 실제 VLM profiler 결과가 아니라 cost model 기반 추정이다.
- adapter memory 값은 실제 target model과 LoRA rank가 정해지면 파라미터 수 기반으로 다시 계산해야 한다.
- latency는 실제 커널 실행 시간이 아니라 token 수와 load/evict 횟수 기반 proxy다.
- 정확도는 아직 측정하지 않았으므로, 이 보고서는 성능 우위가 아니라 비용 구조 검증 자료로 해석해야 한다.

## 8. 다음 단계

1. 실제 target VLM 후보를 정하고 parameter-count 기반 adapter memory table로 교체한다.
2. 작은 이미지 샘플에서 PyTorch CUDA profiler 또는 실제 inference peak memory를 측정한다.
3. budget policy가 top-k, ROI count, adapter load를 줄이는 stress case를 학교 제출용 그림으로 정리한다.
4. 장비 지원을 받으면 실제 VLM inference, LoRA loading, co-resident module 검증으로 확장한다.

## 9. 결론

RTX 3090 24GB 기반 0차 cost simulation은 제안 구조가 VRAM 절약 측면에서 검증할 가치가 있음을 보여준다. 특히 입력 비용 절감과 adapter resident memory 절감을 분리해 측정할 수 있으므로, 후속 장비 지원을 요청하기 위한 초기 근거 자료로 사용할 수 있다.
