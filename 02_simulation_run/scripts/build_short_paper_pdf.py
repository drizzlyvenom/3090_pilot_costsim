from __future__ import annotations

import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def find_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "results" / "primary_case_summary.csv").exists() and (parent / "figures").exists():
            return parent
        if (parent / "02_simulation_run" / "results" / "primary_case_summary.csv").exists():
            return parent
    raise RuntimeError("Could not locate 3090_pilot_costsim root.")


ROOT = find_root()
if (ROOT / "02_simulation_run").exists():
    RESULTS_DIR = ROOT / "02_simulation_run" / "results"
    FIGURES_DIR = ROOT / "03_results_summary" / "figures"
    PAPER_DIR = ROOT / "03_results_summary" / "short_papers"
else:
    RESULTS_DIR = ROOT / "results"
    FIGURES_DIR = ROOT / "figures"
    PAPER_DIR = ROOT / "reports" / "short_papers"

MALGUN = Path(r"C:\Windows\Fonts\malgun.ttf")
MALGUN_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def register_fonts() -> tuple[str, str]:
    if MALGUN.exists():
        pdfmetrics.registerFont(TTFont("Malgun", str(MALGUN)))
        regular = "Malgun"
        if MALGUN_BOLD.exists():
            pdfmetrics.registerFont(TTFont("MalgunBold", str(MALGUN_BOLD)))
            return regular, "MalgunBold"
        return regular, regular
    return "Helvetica", "Helvetica-Bold"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_manifest() -> dict:
    candidates = [ROOT / "manifest.json", ROOT / "02_simulation_run" / "manifest.json"]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise RuntimeError("manifest.json not found.")


def metrics() -> dict:
    primary = read_csv(RESULTS_DIR / "primary_case_summary.csv")
    by = {row["baseline"]: row for row in primary}
    interp = read_manifest()["interpretation"]
    return {
        "primary": primary,
        "b1_tokens": int(by["B1"]["visual_tokens"]),
        "b2_tokens": int(by["B2"]["visual_tokens"]),
        "b1_peak": float(by["B1"]["estimated_peak_memory_gb"]),
        "b7_peak": float(by["B7-lite"]["estimated_peak_memory_gb"]),
        "b4_adapter_gb": float(by["B4-lite"]["resident_adapter_memory_mb"]) / 1024,
        "b5_adapter_gb": float(by["B5-lite"]["resident_adapter_memory_mb"]) / 1024,
        "b7_adapter_gb": float(by["B7-lite"]["resident_adapter_memory_mb"]) / 1024,
        "token_reduction": interp["token_reduction_b2"],
        "peak_reduction": interp["peak_reduction_b7"],
        "adapter_reduction_b5": interp["adapter_reduction_b5"],
        "adapter_reduction_b7": interp["adapter_reduction_b7"],
        "b4_fail_runs": interp["b4_fail_runs"],
        "b7_fail_runs": interp["b7_fail_runs"],
        "b7_adjusted_runs": interp["b7_adjusted_runs"],
        "b7_total_runs": interp["b7_total_runs"],
    }


def styles(lang: str):
    regular, bold = register_fonts()
    sample = getSampleStyleSheet()
    sample.add(ParagraphStyle(name="TitleX", fontName=bold, fontSize=15.5, leading=20, alignment=TA_CENTER, spaceAfter=8))
    sample.add(ParagraphStyle(name="SubX", fontName=regular, fontSize=9, leading=12, alignment=TA_CENTER, spaceAfter=8))
    sample.add(ParagraphStyle(name="H1X", fontName=bold, fontSize=12, leading=15, spaceBefore=3, spaceAfter=5))
    sample.add(ParagraphStyle(name="H2X", fontName=bold, fontSize=10.2, leading=13, spaceBefore=3, spaceAfter=4))
    sample.add(ParagraphStyle(name="BodyX", fontName=regular, fontSize=8.8, leading=12.2, alignment=TA_LEFT, spaceAfter=4))
    sample.add(ParagraphStyle(name="CapX", fontName=regular, fontSize=7.8, leading=10, alignment=TA_CENTER, textColor=colors.HexColor("#444444"), spaceAfter=3))
    sample.add(ParagraphStyle(name="RefX", fontName=regular, fontSize=7.8, leading=10.5, alignment=TA_LEFT, spaceAfter=2))
    return sample, regular, bold


def result_table(data: dict, lang: str, sty: dict) -> Table:
    regular = sty["font_regular"]
    bold = sty["font_bold"]
    headers = ["Baseline", "Tokens", "Peak GB", "Adapter GB", "Reserve", "Latency"] if lang == "en" else ["비교군", "토큰", "Peak GB", "Adapter GB", "Reserve", "Latency"]
    rows = [headers]
    for row in data["primary"]:
        rows.append([
            row["baseline"],
            row["visual_tokens"],
            f"{float(row['estimated_peak_memory_gb']):.2f}",
            f"{float(row['resident_adapter_memory_mb']) / 1024:.2f}",
            "pass" if row["reserve_pass"] == "True" else "fail",
            f"{float(row['latency_proxy_ms']):.1f}",
        ])
    table = Table(rows, hAlign="CENTER", repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C1CC")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def refs(lang: str) -> list[str]:
    if lang == "en":
        return [
            "Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. arXiv:2106.09685.",
            "Tian, C. et al. (2024). HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning. arXiv:2404.19245.",
            "Maes, L. et al. (2026). LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels. arXiv:2603.19312.",
            "Davidson, T. R. et al. (2026). Reasoning-Driven Synthetic Data Generation and Evaluation. arXiv:2603.29791.",
        ]
    return [
        "Hu, E. J. 외 (2021). LoRA: Low-Rank Adaptation of Large Language Models. arXiv:2106.09685.",
        "Tian, C. 외 (2024). HydraLoRA: An Asymmetric LoRA Architecture for Efficient Fine-Tuning. arXiv:2404.19245.",
        "Maes, L. 외 (2026). LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels. arXiv:2603.19312.",
        "Davidson, T. R. 외 (2026). Reasoning-Driven Synthetic Data Generation and Evaluation. arXiv:2603.29791.",
    ]


def build_pdf(lang: str, data: dict) -> Path:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    style_sheet, regular, bold = styles(lang)
    sty = {
        "TitleX": style_sheet["TitleX"],
        "SubX": style_sheet["SubX"],
        "H1X": style_sheet["H1X"],
        "H2X": style_sheet["H2X"],
        "BodyX": style_sheet["BodyX"],
        "CapX": style_sheet["CapX"],
        "RefX": style_sheet["RefX"],
        "font_regular": regular,
        "font_bold": bold,
    }
    title = (
        "A Cost-Simulation Feasibility Study of Budget-Conditioned Foveated Adapter Residency under 24GB GPU Memory"
        if lang == "en"
        else "24GB GPU 메모리 제약에서의 Budget-Conditioned Foveated Adapter Residency 비용 시뮬레이션 연구"
    )
    subtitle = "Preliminary short-paper draft for research discussion" if lang == "en" else "후속 연구 논의를 위한 1차 소논문 초안"
    out = PAPER_DIR / ("short_paper_costsim_en.pdf" if lang == "en" else "short_paper_costsim_ko.pdf")
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=1.55 * cm, rightMargin=1.55 * cm, topMargin=1.45 * cm, bottomMargin=1.45 * cm)
    story = []

    def p(text: str, style: str = "BodyX") -> Paragraph:
        return Paragraph(text, sty[style])

    story += [p(title, "TitleX"), p(subtitle, "SubX"), p("Abstract" if lang == "en" else "초록", "H1X")]
    story.append(p(
        (
            "Physical-AI systems often require perception, planning, verification, and world-model components to share a limited GPU memory budget. "
            "This note evaluates whether a budget-conditioned foveated adapter residency policy is worth pursuing before implementing full VLM training or HydraLoRA-style fine-tuning. "
            f"Across 4,032 simulated configurations, the foveated input reduced visual tokens by {data['token_reduction']:.1f}% in the primary case, while the final budgeted variant reduced estimated peak memory by {data['peak_reduction']:.1f}% relative to full-resolution input. "
            f"The shared-bank and budgeted variants reduced resident adapter memory by {data['adapter_reduction_b5']:.2f}% and {data['adapter_reduction_b7']:.2f}%, respectively, compared with an independent bank."
        )
        if lang == "en"
        else (
            "피지컬 AI 시스템에서는 perception, planning, verification, world model 계층이 제한된 GPU 메모리를 함께 사용해야 한다. "
            "본 초안은 실제 VLM 학습이나 HydraLoRA 계열 fine-tuning을 수행하기 전에, budget-conditioned foveated adapter residency 정책이 후속 연구 가치가 있는지 비용 시뮬레이션으로 확인한다. "
            f"총 4,032개 조건에서 대표 조건의 foveated input은 visual token을 {data['token_reduction']:.1f}% 줄였고, 최종 B7-lite 구조는 full-resolution 기준선 대비 estimated peak memory를 {data['peak_reduction']:.1f}% 줄였다. "
            f"또한 shared-bank와 budgeted variant는 independent bank 대비 resident adapter memory를 각각 {data['adapter_reduction_b5']:.2f}%, {data['adapter_reduction_b7']:.2f}% 줄였다."
        )
    ))
    story.append(p("Keywords: foveated inference; adapter residency; LoRA; GPU memory; cost simulation; physical AI" if lang == "en" else "핵심어: foveated inference; adapter residency; LoRA; GPU memory; cost simulation; physical AI", "H2X"))
    story.append(PageBreak())

    story.append(p("1. Introduction" if lang == "en" else "1. 서론", "H1X"))
    story.append(p(
        "A deployment-oriented physical-AI loop is not only a question of running the largest possible vision model. The perception model must leave memory for planning, verification, orchestration, and possibly a world model. This motivates a policy view: the system should decide where to look, which lightweight adapter to activate, and when to keep or evict that adapter under a memory budget."
        if lang == "en"
        else "배치 관점의 피지컬 AI 루프는 가장 큰 비전 모델 하나를 띄우는 문제가 아니다. 실제 시스템에서는 perception 모델이 planner, verifier, orchestration layer, world model이 사용할 메모리 여유를 남겨야 한다. 따라서 이 연구는 어디를 볼지, 어떤 lightweight adapter를 활성화할지, 그리고 언제 유지하거나 내릴지를 메모리 예산 아래에서 결정하는 정책 문제로 접근한다."
    ))
    story.append(p(
        "The proposed direction combines foveated input selection, LoRA-style local skill adapters, and HydraLoRA-style sharing. The central question is modest: before expensive model training, does this structure produce a measurable memory-cost advantage in simulation?"
        if lang == "en"
        else "제안 방향은 foveated input selection, LoRA 계열 local skill adapter, HydraLoRA식 공유 구조를 결합한다. 본 초안의 질문은 작다. 비싼 모델 학습 전에, 이 구조가 시뮬레이션 상에서 측정 가능한 메모리 비용 이득을 만드는가를 본다."
    ))
    story.append(p("Contributions" if lang == "en" else "기여", "H2X"))
    for item in (
        [
            "A cost model separates visual-token cost, adapter resident memory, temporary load buffers, and orchestration reserve.",
            "The study compares full-resolution inference against foveated ROI inference and independent adapter banks against shared adapter banks.",
            "A stress grid shows that budget-conditioned residency can remove reserve failures in this simulator.",
        ]
        if lang == "en"
        else [
            "visual-token cost, adapter resident memory, temporary load buffer, orchestration reserve를 분리한 작은 cost model을 정의했다.",
            "full-resolution inference와 foveated ROI inference, independent adapter bank와 shared adapter bank를 비교했다.",
            "budget-conditioned residency가 simulator 안에서 reserve failure를 줄일 수 있음을 stress grid로 확인했다.",
        ]
    ):
        story.append(p("• " + item))
    story.append(PageBreak())

    story.append(p("2. Method" if lang == "en" else "2. 방법", "H1X"))
    story.append(p(
        "The simulator uses a proxy 7B VLM memory profile on an RTX 3090 24GB GPU. The primary case assumes a 12GB base model, a 4GB orchestration reserve target, a 1344 x 1344 full-resolution input, a 336 x 336 global view, three 336 x 336 ROI crops, sixteen candidate adapters, and top-k=2 active adapters."
        if lang == "en"
        else "시뮬레이터는 RTX 3090 24GB 위의 proxy 7B VLM memory profile을 사용한다. 대표 조건은 base model 12GB, orchestration reserve target 4GB, full-resolution 1344 x 1344, global view 336 x 336, ROI crop 336 x 336 세 개, 후보 adapter 16개, active top-k=2로 둔다."
    ))
    story.append(p(
        "Six baselines are evaluated: B0 low-resolution global view, B1 full-resolution input, B2 foveated ROI without adapters, B4-lite independent adapter residency, B5-lite shared adapter residency, and B7-lite budget-conditioned residency with top-k, ROI, or adapter-hold actions."
        if lang == "en"
        else "비교군은 여섯 개다. B0는 저해상도 global view만 쓰고, B1은 full-resolution 입력을 쓰는 비용 기준선이다. B2는 adapter 없이 ROI crop을 추가한다. B4-lite는 independent adapter bank가 모두 상주한다고 가정한다. B5-lite는 shared common component와 skill별 branch를 가정한다. B7-lite는 top-k, ROI, adapter-hold 조정을 수행하는 budget-conditioned controller를 추가한다."
    ))
    story.append(p(
        "The evaluation grid spans model profiles, reserve targets, input resolutions, ROI counts, adapter counts, and active top-k values. Because this is a cost simulation, no task-accuracy claim is made."
        if lang == "en"
        else "평가 grid는 model profile, reserve target, 해상도, ROI 수, adapter 수, active top-k 값을 포함한다. 본 실험은 cost simulation이므로 정확도 주장은 하지 않는다."
    ))
    story.append(PageBreak())

    story.append(p("3. Results" if lang == "en" else "3. 결과", "H1X"))
    story.append(p(
        f"In the primary case, B1 full-resolution input used {data['b1_tokens']} visual tokens and {data['b1_peak']:.2f}GB estimated peak memory. B2 foveated ROI input used {data['b2_tokens']} tokens, a {data['token_reduction']:.1f}% token reduction. B7-lite reached {data['b7_peak']:.2f}GB estimated peak memory, a {data['peak_reduction']:.1f}% reduction relative to B1."
        if lang == "en"
        else f"대표 조건에서 B1 full-resolution 입력은 {data['b1_tokens']} visual token과 {data['b1_peak']:.2f}GB estimated peak memory를 사용했다. B2 foveated ROI 입력은 {data['b2_tokens']} token을 사용해 token 수를 {data['token_reduction']:.1f}% 줄였다. B7-lite는 {data['b7_peak']:.2f}GB estimated peak memory를 기록했으며, 이는 B1 대비 {data['peak_reduction']:.1f}% 감소다."
    ))
    story.append(result_table(data, lang, sty))
    story.append(Spacer(1, 4))
    story.append(p("Table 1. Primary-case simulation results." if lang == "en" else "표 1. 대표 조건의 시뮬레이션 결과.", "CapX"))
    story.append(Image(str(FIGURES_DIR / "primary_peak_memory_bars.png"), width=14.2 * cm, height=8.5 * cm))
    story.append(p("Figure 1. Estimated peak memory by baseline in the primary case." if lang == "en" else "그림 1. 대표 조건에서 비교군별 estimated peak memory.", "CapX"))
    story.append(p(
        f"In the full grid, B4-lite produced {data['b4_fail_runs']} reserve failures, whereas B7-lite produced {data['b7_fail_runs']} reserve failures and adjusted {data['b7_adjusted_runs']} of {data['b7_total_runs']} runs through top-k, ROI, or adapter-hold decisions."
        if lang == "en"
        else f"전체 grid에서 B4-lite는 reserve failure {data['b4_fail_runs']}건을 보였지만, B7-lite는 reserve failure {data['b7_fail_runs']}건을 유지했고 {data['b7_total_runs']}건 중 {data['b7_adjusted_runs']}건에서 top-k, ROI, adapter hold 조정을 수행했다."
    ))
    story.append(PageBreak())

    story.append(p("4. Discussion" if lang == "en" else "4. 논의", "H1X"))
    story.append(p(
        "The result supports the feasibility of separating two resource-control levers: foveated input selection reduces visual-token and activation-related cost, while shared or budgeted adapter residency reduces memory tied to skill specialization. A policy formulation is useful because it can trade adapter breadth or ROI count for reserve safety."
        if lang == "en"
        else "결과는 두 개의 자원 제어 축을 분리해 볼 수 있음을 보여준다. foveated input selection은 visual token과 activation 계열 비용을 줄이고, shared 또는 budgeted adapter residency는 skill specialization에 묶인 resident memory를 줄인다. policy formulation은 adapter 폭이나 ROI 수를 조정해 reserve safety를 확보할 수 있다는 점에서 유용하다."
    ))
    story.append(p("Limitations" if lang == "en" else "한계", "H2X"))
    story.append(p(
        "The simulator is not a profiler. It does not measure kernel-level memory allocation, real VLM attention behavior, adapter loading overhead, or task accuracy. The adapter costs are first-pass assumptions and must be replaced with measured values once a target VLM and LoRA rank are selected."
        if lang == "en"
        else "이 시뮬레이터는 profiler가 아니다. 실제 kernel-level memory allocation, VLM attention behavior, adapter loading overhead, task accuracy를 측정하지 않는다. adapter cost도 1차 가정값이므로 target VLM과 LoRA rank가 정해지면 실제 측정값으로 교체해야 한다."
    ))
    story.append(p("Conclusion and Next Step" if lang == "en" else "결론과 다음 단계", "H2X"))
    story.append(p(
        "The 24GB GPU cost simulation indicates that budget-conditioned foveated adapter residency is worth validating with real model runs. The immediate next step is to profile a small VLM under full-resolution and foveated inputs, then replace the simulated adapter table with measured LoRA loading and residency costs."
        if lang == "en"
        else "24GB GPU cost simulation은 budget-conditioned foveated adapter residency가 실제 모델 실험으로 검증할 가치가 있음을 보여준다. 다음 단계는 작은 VLM을 대상으로 full-resolution 입력과 foveated 입력의 실제 peak memory를 측정하고, simulated adapter table을 실제 LoRA loading/residency cost로 교체하는 것이다."
    ))
    story.append(p("References" if lang == "en" else "참고문헌", "H2X"))
    for ref in refs(lang):
        story.append(p(ref, "RefX"))
    doc.build(story)
    return out


def main() -> int:
    data = metrics()
    en = build_pdf("en", data)
    ko = build_pdf("ko", data)
    print(json.dumps({"english_pdf": str(en), "korean_pdf": str(ko)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
