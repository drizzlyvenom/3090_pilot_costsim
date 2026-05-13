# Dependency Audit - 2026-05-13

작업 목적: 3090 cost simulation 후속 작업에서 자주 쓸 시각화/분석 의존성을 정리하고, NumPy/PyTorch 경고와 공급망 리스크를 확인한다.

## 확인한 출처

- PyPI package index: `matplotlib`, `numpy`, `pandas`, `opencv-python-headless`
- OSV API: PyPI package/version 단위 취약점 조회
- PyTorch official install guide: CUDA wheel 계열 확인

## 조치 전 주요 상태

```text
matplotlib==3.6.3
numpy==2.2.6
pandas==1.5.3
opencv-python-headless==4.13.0.92
torch==1.13.1+cu117
torchvision==0.14.1+cu117
pip==26.1
```

문제:

- `pandas 1.5.3`은 `numpy 2.2.6`과 ABI 불일치가 발생했다.
- `torch 1.13.1+cu117`은 NumPy 2.x와 경고가 날 수 있는 오래된 조합이다.
- `pip check`에서 `gradio`, `scipy`, `numba`, `blendmodes`가 `numpy 2.2.6`과 충돌했다.
- OSV 조회에서 `torch 1.13.1`은 알려진 취약점 10건이 있었다.

## 적용한 조치

```text
matplotlib: 3.6.3 -> 3.10.9
pandas: 1.5.3 -> 2.3.3
numpy: 2.2.6 -> 1.26.4
opencv-python-headless: 4.13.0.92 -> 4.11.0.86
pip: 26.1 -> 26.1.1
```

적용 원칙:

- `--only-binary=:all:`로 wheel만 설치하고 소스 빌드를 피했다.
- `--no-cache-dir`로 stale cache 사용을 피했다.
- OSV 조회에서 0건으로 확인된 버전만 적용했다.
- PyTorch 대형 업데이트는 전역 환경 영향이 커서 이번 조치에서 제외했다.

## 조치 후 상태

```text
blendmodes==2022
gradio==3.41.2
matplotlib==3.10.9
numba==0.60.0
numpy==1.26.4
opencv-python==4.7.0.68
opencv-python-headless==4.11.0.86
pandas==2.3.3
pip==26.1.1
scipy==1.10.0
torch==1.13.1+cu117
torchvision==0.14.1+cu117
```

검증 결과:

```text
python -m pip check
=> No broken requirements found.
```

Import smoke test:

```text
numpy: 1.26.4
pandas: 2.3.3
matplotlib: 3.10.9
cv2: 4.11.0
torch: 1.13.1+cu117
torch cuda: true
```

Cost simulation pipeline:

```text
python .\02_simulation_run\scripts\run_costsim_pipeline.py
=> status ok, rows 4032, pdf_pages_rendered 4, docx_readable true
```

## 남은 주의점

`torch 1.13.1+cu117`은 CUDA는 정상 인식하지만 OSV에서 취약점이 잡힌 오래된 버전이다. 전역 Python에서 바로 `torch 2.x`로 올리면 다른 로컬 AI 도구가 깨질 수 있으므로, 다음 단계에서는 별도 venv를 만들고 공식 PyTorch CUDA wheel로 새 실험 환경을 구성하는 편이 안전하다.
