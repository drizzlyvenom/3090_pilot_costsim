# RTX 3090 Cost Simulation Pilot

이 폴더는 `Budget-Conditioned Foveated Adapter Policy`의 0차 비용 시뮬레이션 패키지입니다. 실제 VLM 학습 없이 RTX 3090 24GB 기준 cost simulator로 VRAM 절약 가능성을 확인하고, 교수님께 공유할 수 있는 결과 보고서와 5페이지 소논문 초안을 함께 정리했습니다.

## 폴더 구조

```text
01_experiment_planning/
  실험 기획 문서

02_simulation_run/
  실행 설정, 스크립트, 원본 결과 데이터, 의존성 감사 기록

03_results_summary/
  그래프, 기술 보고서, 영문/국문 소논문 DOCX/PDF
```

## 빠른 확인

교수님께 바로 보여주기 좋은 파일:

- `03_results_summary/short_papers/short_paper_costsim_en.pdf`
- `03_results_summary/short_papers/short_paper_costsim_ko.pdf`
- `03_results_summary/technical_report/results_report_ko.pdf`

수정용 원본:

- `03_results_summary/short_papers/short_paper_costsim_en.docx`
- `03_results_summary/short_papers/short_paper_costsim_ko.docx`
- `03_results_summary/technical_report/results_report_ko.docx`

## 핵심 결과

- 총 `4032`개 조건 시뮬레이션
- B1 full-resolution 대비 B2 foveated ROI visual token `75.0%` 감소
- B1 대비 B7-lite estimated peak memory `21.9%` 감소
- B4-lite 대비 B7-lite resident adapter memory `89.24%` 감소
- 전체 grid에서 B4-lite reserve fail `396건`, B7-lite reserve fail `0건`
- B7-lite는 `1296건 중 148건`에서 top-k, ROI, adapter hold 조정을 수행

## 재실행

```powershell
python .\02_simulation_run\scripts\run_costsim_pipeline.py
python .\02_simulation_run\scripts\build_short_paper_docx.py
python .\02_simulation_run\scripts\build_short_paper_pdf.py
```

## 주의

이번 결과는 실제 VLM profiler 결과가 아니라 cost model 기반 feasibility study입니다. 성능 우위 주장이 아니라, 실제 VLM inference와 LoRA loading 실험으로 확장할 가치가 있는지를 보여주는 초기 근거 자료로 해석해야 합니다.
