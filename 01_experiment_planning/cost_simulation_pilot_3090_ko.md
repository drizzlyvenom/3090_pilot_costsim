# RTX 3090 기반 VRAM Cost Simulation 파일럿 계획

제목: Budget-Conditioned Foveated Adapter Policy의 1차 비용 시뮬레이션  
상태: v0.1, 로컬 RTX 3090 24GB 기준 초안  
작성일: 2026-05-13  
위치: `/3090_pilot_costsim/01_experiment_planning/cost_simulation_pilot_3090_ko.md`

## 1. 목적

이 문서는 실제 LoRA 학습이나 전체 HydraLoRA 구현 전에, 제안 구조가 VRAM 절약 관점에서 실험 가치가 있는지 빠르게 확인하기 위한 1차 파일럿 계획이다.

핵심 질문은 다음 하나로 둔다.

" Full-resolution vision inference와 naive adapter bank 대비,
low-resolution global view + ROI crop + budget-conditioned adapter residency가
RTX 3090 24GB 제약에서 peak VRAM과 adapter resident memory를 줄일 가능성이 있는가? "


## 2. 현재 가능한 범위

로컬 RTX 3090 24GB에서 먼저 가능한 일:

- full-resolution 입력과 low-resolution + ROI crop 입력의 token/memory cost 비교
- adapter bank를 실제 LoRA 학습 없이 cost table로 모델링
- independent adapter bank와 HydraLoRA-style shared structure의 resident memory 비교
- budget-conditioned policy가 keep / evict / hold 결정을 어떻게 바꾸는지 로그화
- visual token count, estimated KV cache, adapter resident memory, peak memory estimate, p95 latency proxy 기록
- 필요하면 PyTorch CUDA allocation으로 단순 sanity check 수행

이번 단계에서 하지 않을 일:

- 대형 VLM full fine-tuning
- HydraLoRA 전체 논문급 재현
- Simula synthetic curriculum 생성
- planner, world model, verifier, orchestration LLM의 완전체 동시 실행
- 정확도 우위 주장

## 3. 실험 가설

### H1. Foveated input cost 절감

full-resolution 한 장을 그대로 넣는 것보다, 작은 global view와 필요한 ROI crop 몇 개만 처리하면 visual token 수와 activation/KV cache 비용이 줄어든다.

### H2. Adapter resident memory 절감

independent LoRA bank는 선택 가능한 adapter 수가 늘어날수록 resident memory가 선형적으로 커진다. HydraLoRA-style shared structure는 공통 부분을 공유한다고 가정하면 resident memory 증가율을 낮출 수 있다.

### H3. Budget-conditioned residency의 효과

항상 top-k adapter를 올리는 방식보다, 남은 memory budget과 재사용 가능성을 보고 keep / evict / hold를 결정하면 peak memory violation과 load/unload thrashing을 줄일 수 있다.

## 4. 비교군

| ID | 이름 | 설명 | 이번 파일럿에서의 구현 |
| --- | --- | --- | --- |
| B0 | Low-res only | 작은 global view만 사용 | token/memory cost 계산 |
| B1 | Full-res | full-resolution 입력 사용 | 강한 비용 기준선 |
| B2 | Foveated ROI | low-res global + K개 ROI crop | crop 수 K별 비용 계산 |
| B4-lite | Independent adapter bank | adapter를 서로 독립 weight로 가정 | adapter cost table 합산 |
| B5-lite | HydraLoRA-style shared bank | shared-A + per-skill branch로 가정 | 공유 구조 cost table |
| B7-lite | Budget-conditioned residency | B2 + B5-lite + keep/evict/hold policy | 규칙 기반 simulator |

`lite` 표기는 실제 학습된 LoRA를 사용하지 않고, adapter의 memory/load/latency cost를 표로 둔 시뮬레이션임을 뜻한다.

## 5. Cost Model

1차 시뮬레이션은 실제 GPU profiler 결과와 완전히 같다고 주장하지 않는다. 대신 baseline 간 상대 비교가 가능하도록 같은 계산 규칙을 적용한다.

### 5.1 입력 비용

```text
image_tokens = ceil(width / patch_size) * ceil(height / patch_size)

global_tokens = tokens(low_res_global)
roi_tokens = sum(tokens(roi_i) for i in selected_rois)
total_visual_tokens = global_tokens + roi_tokens
```

예시 조건:

| 조건 | 해상도 예시 | 목적 |
| --- | --- | --- |
| full-res | 1344 x 1344 또는 1024 x 1024 | B1 기준선 |
| low-res global | 336 x 336 또는 448 x 448 | 전체 문맥 유지 |
| ROI crop | 336 x 336 또는 448 x 448 | 필요한 국소 증거만 추가 |

### 5.2 메모리 비용

```text
estimated_peak_memory =
  base_model_memory
  + visual_activation_cost(total_visual_tokens)
  + kv_cache_cost(total_visual_tokens, output_tokens)
  + resident_adapter_memory
  + temporary_load_buffer
  + safety_margin
```

3090 기준 초기 budget:

```text
total_gpu_memory = 24 GB
runtime_budget = 22 GB
safety_margin = 2 GB
orchestration_reserve_target = 4 GB
```

여기서 `orchestration_reserve_target`은 나중에 planner, verifier, world model, orchestration LLM이 같이 떠 있어야 한다는 주장을 수치화하기 위한 자리다. 이번 파일럿에서는 실제 모듈을 띄우지 않고 reserve pass/fail만 계산한다.

### 5.3 Adapter 비용

Independent adapter bank:

```text
resident_adapter_memory_B4 =
  sum(memory(adapter_i) for adapter_i in active_adapters)
```

HydraLoRA-style shared bank:

```text
resident_adapter_memory_B5 =
  shared_A_memory
  + sum(branch_memory(adapter_i) for adapter_i in active_adapters)
```

초기 cost table 예시:

| adapter type | memory cost | load cost | 설명 |
| --- | ---: | ---: | --- |
| independent rank-8 | 180 MB | 1.0x | naive LoRA adapter |
| independent rank-16 | 360 MB | 1.3x | 더 큰 adapter |
| shared-A common | 220 MB | 1.0x | HydraLoRA-style 공통부 |
| shared branch rank-8 | 45 MB | 0.4x | skill별 branch |
| shared branch rank-16 | 90 MB | 0.6x | 더 큰 branch |

수치는 1차 가정값이다. 실제 모델과 LoRA rank가 정해지면 파라미터 수 기반으로 다시 계산한다.

## 6. Budget Policy

B7-lite는 학습된 policy가 아니라 규칙 기반 controller로 시작한다.

### 6.1 Adapter utility

```text
utility(adapter_i) =
  tag_match_score
  + confidence_score
  + reuse_bonus
  - lambda_memory * memory_cost
  - lambda_latency * load_cost
```

### 6.2 Residency action

| action | 의미 | 조건 예시 |
| --- | --- | --- |
| keep | 이미 올라간 adapter를 유지 | 재사용 가능성이 높고 budget 여유가 있음 |
| evict | adapter를 내림 | utility가 낮거나 budget 초과 위험이 있음 |
| hold | 새 adapter를 올리지 않음 | evidence가 약하거나 reserve를 침범함 |
| load | adapter를 새로 올림 | utility가 높고 budget 안에 들어옴 |

### 6.3 Budget rule

```text
if estimated_peak_memory + orchestration_reserve_target <= runtime_budget:
    allow selected ROI and adapter set
else:
    reduce top-k
    reduce ROI count K
    evict lowest-utility adapter
    if still over budget:
        hold adapter load and use base model only
```

이 규칙은 단순하지만, 연구 질문에는 충분하다. 핵심은 policy가 budget을 사후 로그가 아니라 의사결정 조건으로 쓴다는 점이다.

## 7. 실험 매트릭스

1차로는 작은 grid만 돌린다.

| 변수 | 값 |
| --- | --- |
| ROI count K | 0, 1, 3, 5 |
| full-res size | 1024, 1344 |
| global size | 336, 448 |
| ROI size | 336, 448 |
| adapter count N | 4, 8, 16, 32 |
| active top-k | 1, 2, 4 |
| adapter structure | independent, shared |
| reserve target | 2GB, 4GB, 6GB |

처음 실행할 최소 조합:

```text
B0: global 336 only
B1: full 1024
B2: global 336 + ROI 336 x K where K in {1, 3, 5}
B4-lite: B2 + independent adapter top-k
B5-lite: B2 + shared adapter top-k
B7-lite: B2 + shared adapter + budget rule
```

## 8. 로그 스키마

실험 결과는 CSV 또는 JSONL로 남긴다.

```json
{
  "run_id": "string",
  "baseline": "B7-lite",
  "gpu": "RTX 3090",
  "total_vram_gb": 24,
  "runtime_budget_gb": 22,
  "reserve_target_gb": 4,
  "full_res": [1024, 1024],
  "global_res": [336, 336],
  "roi_res": [336, 336],
  "roi_count": 3,
  "visual_tokens": 1764,
  "adapter_structure": "shared",
  "adapter_count": 16,
  "active_top_k": 2,
  "resident_adapter_memory_mb": 310,
  "estimated_peak_memory_mb": 14200,
  "reserve_pass": true,
  "load_count": 2,
  "evict_count": 1,
  "hold_count": 0,
  "latency_proxy_ms": 83.4,
  "main_decision": "keep_shared_branch"
}
```

필수 결과표:

| baseline | visual tokens | est. peak memory | adapter resident memory | reserve pass | load/evict count | latency proxy |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| B0 | | | | | | |
| B1 | | | | | | |
| B2 | | | | | | |
| B4-lite | | | | | | |
| B5-lite | | | | | | |
| B7-lite | | | | | | |

## 9. 성공 기준

1차 성공 기준:

- B1 대비 B2의 visual token 수와 estimated peak memory가 감소한다.
- B4-lite 대비 B5-lite의 adapter resident memory가 감소한다.
- B5-lite 대비 B7-lite에서 reserve pass rate가 개선되거나, peak memory violation이 줄어든다.
- B7-lite가 top-k와 K를 줄이는 결정 로그를 남긴다.
- 결과표가 학교 제출용 제안서에 들어갈 수 있을 만큼 단순하고 재현 가능하다.

실패여도 의미 있는 경우:

- visual token은 줄었지만 peak memory가 거의 줄지 않으면, 병목이 KV cache나 base model weight 쪽에 있음을 보여준다.
- adapter resident memory는 줄었지만 load/evict가 너무 많으면, residency hysteresis가 필요하다는 근거가 된다.
- reserve target을 조금만 키워도 실패하면, 24GB 단일 GPU에서 완전체 co-residency가 어렵다는 지원 필요 근거가 된다.

## 10. 산출물 구성

이 파일럿이 끝나면 다음 3개를 묶어 제출 자료로 만들 수 있다.

1. 간단한 실험 제안서
   - 연구 질문
   - 왜 비용 시뮬레이션부터 하는지
   - RTX 3090 24GB에서 가능한 1차 검증 범위

2. 초기 결과표
   - B0/B1/B2/B4-lite/B5-lite/B7-lite 비교
   - visual token, estimated peak memory, adapter resident memory, reserve pass

3. 지원 필요성
   - 더 큰 GPU 또는 전용 장비가 있으면 실제 VLM inference, LoRA 학습, co-resident module 실행으로 확장 가능
   - 서버 GPU는 full experimental validation 환경으로 사용 가능

