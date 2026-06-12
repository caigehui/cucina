#!/usr/bin/env python3
"""
Export a daily US equities Markdown report to a dark, image-rich PDF.

The primary renderer uses ReportLab when it is installed because ReportLab wraps
Chinese/English mixed paragraphs inside real PDF frames. A matplotlib renderer is
kept as a no-install fallback and uses the same aurora-dark visual language.

Examples:
  python scripts/export_report.py --input output/reports/美股研报_2026-06-12.md --out output/reports/美股研报_2026-06-12.pdf --append-glossary
  python scripts/export_report.py --input output/reports/美股研报_2026-06-12.md --out output/reports/美股研报_2026-06-12.pdf --append-glossary --update-md --engine auto
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image as PILImage


PAGE_W, PAGE_H = 8.27, 11.69  # A4, inches
MARGIN_L, MARGIN_R = 0.62, 0.62
MARGIN_T, MARGIN_B = 0.72, 0.62
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
GLOSSARY_RE = re.compile(r"^##+\s*(?:\d+\.\s*)?(?:术语解释|Glossary)\b", re.M)
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
FONT_CACHE_DIR = Path.home() / ".cache" / "cucina" / "fonts"

BG = "#030807"
PANEL = "#07110f"
PANEL_2 = "#0b1815"
STROKE = "#1f4f43"
TEXT = "#FFFFFF"
MUTED = "#FFFFFF"
ACCENT = "#62f0bd"
ACCENT_2 = "#8aa7ff"
WARN = "#f5c56a"
RED = "#ff6b6b"


DEFAULT_GLOSSARY = [
    ("Risk-on / Risk-off", "市场风险偏好。risk-on 偏追逐股票、信用和高 beta; risk-off 偏防守、美元、美债或现金。"),
    ("VIX", "Cboe 标普 500 隐含波动率指数, 常被当作美股波动和避险情绪温度计。"),
    ("美债收益率", "美国国债利率。长端收益率上行通常压制高估值成长股, 但方向要结合通胀、财政和增长预期看。"),
    ("DXY / 美元指数", "衡量美元相对一篮子主要货币的强弱。美元走强常对大宗商品、海外收入和风险资产形成压力。"),
    ("CPI / PCE / NFP", "美国通胀和就业数据。CPI/PCE 影响通胀路径,NFP 影响就业与增长判断,都可能改变降息预期。"),
    ("FOMC", "美联储议息会议。日报里重点看利率决议、点阵图、声明和主席发布会口径。"),
    ("FedWatch / 降息概率", "市场基于利率期货推算的政策路径概率, 是市场定价, 不是美联储承诺。"),
    ("四巫日", "股指期货、股指期权、个股期货、个股期权集中到期日, 可能放大成交和调仓噪音。"),
    ("Mag7", "美股七大科技权重股常用简称。日报中用它观察指数集中度和 AI/成长风格。"),
    ("Semis / 半导体", "半导体链条, 包括 GPU、代工、存储、设备、EDA、封测和光互连等环节。"),
    ("AI 供应链卡点", "沿需求反推到最紧缺、最难扩产或最能卡住交付的环节, 用来寻找市场可能低估的信息差。"),
    ("Hyperscaler", "超大规模云厂商或互联网基础设施客户, 常是 AI 服务器、GPU 和光模块需求的核心买方。"),
    ("CapEx", "资本开支。云厂商或半导体公司 CapEx 变化会影响 AI 基建需求和供应链订单。"),
    ("WSB / wallstreetbets", "Reddit 高风险交易社区 r/wallstreetbets。日报中只作为散户情绪样本, 不能等同于全市场共识。"),
    ("X / Twitter 热度", "X/Twitter 上围绕 ticker、cashtag 或核心叙事的讨论扩散度, 需标注抓取窗口和样本限制。"),
    ("HYPE 阶段", "社媒热度生命周期判断, 常分早期、中期、末期和退潮。它衡量拥挤度和传播阶段, 不是涨跌预测。"),
    ("YOLO", "高风险集中下注语境, 常见于 WSB。YOLO 增多通常代表拥挤度和回撤风险上升。"),
    ("0DTE", "当天到期的期权。0DTE 讨论增多通常代表短线投机和盘中波动风险更高。"),
    ("FOMO", "Fear of Missing Out, 害怕错过导致追高或跟风。"),
    ("Bag-holder", "高位接盘后被套的持有人语境。亏损截图和自嘲变多常见于 HYPE 退潮阶段。"),
    ("Thesis", "投资或研究假设。必须有触发条件和证伪条件, 不能当成事实。"),
    ("触发条件", "使某个预案值得重新评估的价格、数据、财报、政策或新闻条件。不是自动交易指令。"),
    ("证伪条件", "一旦出现就推翻当前判断或降低信念档的事实或信号。"),
    ("as-of", "数据截至时间。行情、新闻、期权、持仓、宏观数据和社媒样本都必须标注 as-of。"),
]


def find_font_path() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/NotoSansCJKsc-Regular.otf"),
        Path("C:/Windows/Fonts/NotoSansCJK-Regular.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arialuni.ttf"),
    ]
    return next((path for path in candidates if path.exists()), None)


def ensure_variable_font_instance(source: Path, cached: Path, weight: int = 700) -> Path | None:
    if cached.exists():
        return cached
    if not source.exists():
        return None
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer

        FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        font = TTFont(str(source))
        instancer.instantiateVariableFont(font, {"wght": weight}, inplace=True)
        font.save(str(cached))
        return cached
    except Exception:
        return None


def ensure_noto_bold_font() -> Path | None:
    return ensure_variable_font_instance(
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        FONT_CACHE_DIR / "NotoSansSC-Black.ttf",
        weight=900,
    )


def ensure_noto_display_bold_font() -> Path | None:
    return ensure_variable_font_instance(
        Path("C:/Windows/Fonts/NotoSerifSC-VF.ttf"),
        FONT_CACHE_DIR / "NotoSerifSC-ExtraBold.ttf",
        weight=800,
    )


def find_bold_font_path() -> Path | None:
    candidates = [
        ensure_noto_bold_font(),
        FONT_CACHE_DIR / "NotoSansSC-ExtraBold.ttf",
        FONT_CACHE_DIR / "NotoSansSC-Bold.ttf",
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
    ]
    return next((path for path in candidates if path and path.exists()), None)


def find_display_font_path() -> Path | None:
    candidates = [
        ensure_noto_display_bold_font(),
        FONT_CACHE_DIR / "NotoSerifSC-Bold.ttf",
        Path("C:/Windows/Fonts/NotoSerifSC-VF.ttf"),
        ensure_noto_bold_font(),
        FONT_CACHE_DIR / "NotoSansSC-ExtraBold.ttf",
        FONT_CACHE_DIR / "NotoSansSC-Bold.ttf",
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
    ]
    return next((path for path in candidates if path.exists()), None)


def find_cjk_font():
    from matplotlib.font_manager import FontProperties

    path = find_bold_font_path() or find_font_path()
    return FontProperties(fname=str(path)) if path else FontProperties()


def find_display_cjk_font():
    from matplotlib.font_manager import FontProperties

    path = find_display_font_path() or find_bold_font_path() or find_font_path()
    return FontProperties(fname=str(path)) if path else FontProperties()


def visual_width(text: str) -> int:
    width = 0
    for ch in text:
        width += 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
    return width


def wrap_visual(text: str, max_units: int) -> list[str]:
    text = text.strip()
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    current_width = 0
    last_space = -1

    for ch in text:
        ch_width = 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
        if ch.isspace():
            last_space = len(current)
        if current and current_width + ch_width > max_units:
            if last_space > 8:
                line = current[:last_space].rstrip()
                rest = current[last_space:].lstrip()
                lines.append(line)
                current = rest + ch
                current_width = visual_width(current)
            else:
                lines.append(current.rstrip())
                current = ch.lstrip()
                current_width = visual_width(current)
            last_space = -1
        else:
            current += ch
            current_width += ch_width
    if current.strip():
        lines.append(current.rstrip())
    return lines


def strip_unsupported_symbols(text: str) -> str:
    # Windows CJK fonts used for PDF export generally do not include emoji.
    # Dropping supplementary-plane symbols avoids tofu boxes in the final PDF.
    replacements = {
        "\ufe0f": "",
        "⚠": "",
        "⚫": "",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF)


def strip_inline_markdown(text: str) -> str:
    text = strip_unsupported_symbols(text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text


def inline_markdown_to_reportlab(text: str) -> str:
    text = strip_unsupported_symbols(text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<font name='CucinaMono'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 <font color='#FFFFFF'>\2</font>", escaped)
    return escaped


def natural_heading(text: str) -> str:
    text = strip_inline_markdown(text).strip()
    return re.sub(r"^(?:\d+[\.\)、]\s*|[①②③④⑤⑥⑦⑧⑨⑩]\s*)", "", text).strip()


def has_glossary(text: str) -> bool:
    return bool(GLOSSARY_RE.search(text))


def next_glossary_heading(text: str) -> str:
    nums = []
    for match in re.finditer(r"^##\s+(\d+)\.", text, re.M):
        try:
            nums.append(int(match.group(1)))
        except ValueError:
            pass
    return f"## {max(nums) + 1}. 术语解释" if nums else "## 术语解释"


def glossary_markdown(text: str) -> str:
    heading = next_glossary_heading(text)
    lines = ["", heading, ""]
    for term, definition in DEFAULT_GLOSSARY:
        lines.append(f"- **{term}**: {definition}")
    return "\n".join(lines) + "\n"


def ensure_glossary(text: str) -> tuple[str, bool]:
    if has_glossary(text):
        missing = []
        for term, definition in DEFAULT_GLOSSARY:
            if f"**{term}**" not in text:
                missing.append((term, definition))
        if not missing:
            return text, False
        lines = [""]
        for term, definition in missing:
            lines.append(f"- **{term}**: {definition}")
        return text.rstrip() + "\n" + "\n".join(lines) + "\n", True
    return text.rstrip() + "\n" + glossary_markdown(text), True


def resolve_image(md_path: Path, image_path: str) -> Path:
    raw = image_path.strip().strip('"').strip("'")
    if raw.startswith("file://"):
        raw = raw[7:]
    path = Path(raw)
    return path if path.is_absolute() else (md_path.parent / path).resolve()


def is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and TABLE_SEP_RE.match(lines[index + 1]) is not None
    )


def split_table_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [cell.strip() for cell in cells]


def table_rows_to_readable_lines(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    headers = rows[0]
    readable: list[str] = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        pairs = []
        for header, cell in zip(headers, padded):
            header = strip_inline_markdown(header).strip()
            cell = strip_inline_markdown(cell).strip()
            if header and cell:
                pairs.append(f"{header}: {cell}")
            elif cell:
                pairs.append(cell)
        if pairs:
            readable.append("；".join(pairs))
    if readable:
        return readable
    return ["；".join(strip_inline_markdown(cell).strip() for cell in headers if cell.strip())]


def render_reportlab(md_path: Path, text: str, out: Path) -> tuple[int, int, str]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Image as RLImage
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise RuntimeError(f"reportlab unavailable: {exc}") from exc

    font_path = find_font_path()
    bold_font_path = find_bold_font_path() or font_path
    display_font_path = find_display_font_path()
    font_name = "Helvetica"
    bold_name = "Helvetica-Bold"
    display_name = "Helvetica-Bold"
    mono_name = "Courier"
    if font_path:
        pdfmetrics.registerFont(TTFont("CucinaCJK", str(font_path)))
        font_name = "CucinaCJK"
        mono_name = "CucinaCJK"
    if bold_font_path:
        pdfmetrics.registerFont(TTFont("CucinaCJKBold", str(bold_font_path)))
        bold_name = "CucinaCJKBold"
    if display_font_path:
        pdfmetrics.registerFont(TTFont("CucinaDisplay", str(display_font_path)))
        display_name = "CucinaDisplay"
    else:
        display_name = bold_name
    if mono_name != "Courier":
        # Paragraph inline spans need this name to exist; using CJK font avoids
        # missing glyphs for mixed Chinese/code snippets on Windows.
        pdfmetrics.registerFont(TTFont("CucinaMono", str(bold_font_path or font_path)))
    else:
        mono_name = "Courier"
        pdfmetrics.registerFontFamily("CucinaMono", normal="Courier")

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=62,
        bottomMargin=46,
        title=md_path.stem,
        author="Cucina",
    )
    width = doc.width

    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "CucinaBody",
        parent=base["BodyText"],
        fontName=bold_name,
        fontSize=11.0,
        leading=17.2,
        textColor=colors.HexColor(TEXT),
        spaceAfter=7,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    bullet = ParagraphStyle(
        "CucinaBullet",
        parent=body,
        leftIndent=13,
        firstLineIndent=-7,
        fontName=bold_name,
        fontSize=10.2,
        leading=16.0,
        spaceAfter=5.5,
    )
    h1 = ParagraphStyle(
        "CucinaH1",
        parent=body,
        fontName=display_name,
        fontSize=24,
        leading=31,
        textColor=colors.HexColor(TEXT),
        spaceAfter=18,
        wordWrap="CJK",
    )
    h2 = ParagraphStyle(
        "CucinaH2",
        parent=body,
        fontName=display_name,
        fontSize=16.5,
        leading=21.5,
        textColor=colors.HexColor(TEXT),
        spaceBefore=12,
        spaceAfter=10,
        borderWidth=0.6,
        borderColor=colors.HexColor(STROKE),
        borderPadding=(6, 8, 6, 8),
        backColor=colors.HexColor(PANEL),
        wordWrap="CJK",
    )
    h3 = ParagraphStyle(
        "CucinaH3",
        parent=body,
        fontName=display_name,
        fontSize=13.2,
        leading=17.2,
        textColor=colors.HexColor(TEXT),
        spaceBefore=8,
        spaceAfter=6,
        wordWrap="CJK",
    )
    caption = ParagraphStyle(
        "CucinaCaption",
        parent=body,
        fontName=bold_name,
        fontSize=9.2,
        leading=12.2,
        textColor=colors.HexColor(TEXT),
        alignment=TA_CENTER,
        spaceBefore=3,
        spaceAfter=8,
        wordWrap="CJK",
    )

    story = []
    images = 0
    lines = text.splitlines()
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not stripped:
            story.append(Spacer(1, 4))
            i += 1
            continue

        image_match = IMAGE_RE.search(line)
        if image_match:
            alt, target = image_match.groups()
            image_path = resolve_image(md_path, target)
            if image_path.exists():
                try:
                    with PILImage.open(image_path) as img:
                        iw, ih = img.size
                    draw_w = width
                    draw_h = draw_w * ih / max(iw, 1)
                    max_h = 4.55 * inch
                    if draw_h > max_h:
                        draw_h = max_h
                        draw_w = draw_h * iw / ih
                    story.append(Spacer(1, 6))
                    story.append(RLImage(str(image_path), width=draw_w, height=draw_h, hAlign="CENTER"))
                    if alt:
                        story.append(Paragraph(inline_markdown_to_reportlab(alt), caption))
                    images += 1
                except Exception as exc:
                    story.append(Paragraph(f"<font color='{RED}'>[image render failed: {html.escape(str(image_path))} ({html.escape(str(exc))})]</font>", body))
            else:
                story.append(Paragraph(f"<font color='{RED}'>[image missing: {html.escape(str(image_path))}]</font>", body))
            i += 1
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match and not in_fence:
            level = len(heading_match.group(1))
            heading_text = inline_markdown_to_reportlab(natural_heading(heading_match.group(2)))
            if level == 1:
                story.append(Paragraph(heading_text, h1))
            elif level == 2:
                story.append(Paragraph(heading_text, h2))
            else:
                story.append(Paragraph(heading_text, h3))
            i += 1
            continue

        if is_table_start(lines, i):
            rows = [split_table_row(lines[i])]
            i += 2
            while i < len(lines) and "|" in lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            if rows:
                col_count = max(len(row) for row in rows)
                if col_count > 5:
                    for readable_line in table_rows_to_readable_lines(rows):
                        story.append(Paragraph(inline_markdown_to_reportlab(readable_line), bullet))
                    story.append(Spacer(1, 8))
                    continue
                col_w = [width / col_count] * col_count
                table_data = []
                for row in rows:
                    padded = row + [""] * (col_count - len(row))
                    table_data.append([Paragraph(inline_markdown_to_reportlab(cell), body) for cell in padded])
                table = Table(table_data, colWidths=col_w, hAlign="LEFT", repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2a23")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(TEXT)),
                    ("FONTNAME", (0, 0), (-1, -1), bold_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10.0),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#244d43")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
                story.append(Spacer(1, 8))
            continue

        if stripped.startswith(("- ", "* ")):
            story.append(Paragraph("• " + inline_markdown_to_reportlab(stripped[2:].strip()), bullet))
        elif re.match(r"^\d+\.\s+", stripped):
            story.append(Paragraph(inline_markdown_to_reportlab(stripped), bullet))
        else:
            story.append(Paragraph(inline_markdown_to_reportlab(stripped), body if not in_fence else bullet))
        i += 1

    def on_page(canvas, doc_):
        page_w, page_h = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(BG))
        canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#09241d"))
        canvas.rect(0, page_h - 92, page_w, 92, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0f6b51"))
        canvas.setFillAlpha(0.18)
        for x in range(28, int(page_w), 31):
            for y in range(int(page_h - 86), int(page_h - 16), 17):
                if (x * 7 + y * 3 + doc_.page * 11) % 5 == 0:
                    canvas.circle(x, y, 0.9, fill=1, stroke=0)
        canvas.setFillAlpha(1)
        canvas.setStrokeColor(colors.HexColor(ACCENT))
        canvas.setLineWidth(0.8)
        canvas.line(42, page_h - 49, page_w - 42, page_h - 49)
        canvas.setFillColor(colors.HexColor(TEXT))
        canvas.setFont(display_name, 9.5)
        canvas.drawString(42, page_h - 36, "CUCINA MARKET INTELLIGENCE")
        canvas.setFillColor(colors.HexColor(TEXT))
        canvas.setFont(bold_name, 8.5)
        canvas.drawRightString(page_w - 42, page_h - 36, "MACRO / SOCIAL / PORTFOLIO")
        canvas.setStrokeColor(colors.HexColor("#12382f"))
        canvas.setLineWidth(0.5)
        canvas.roundRect(24, 22, page_w - 48, page_h - 44, 12, fill=0, stroke=1)
        canvas.setFillColor(colors.HexColor(TEXT))
        canvas.setFont(bold_name, 8.5)
        canvas.drawCentredString(page_w / 2, 24, f"{doc_.page}  |  generated by daily-report")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return doc.page, images, "reportlab"


class MatplotlibRenderer:
    def __init__(self, out: Path):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        self.plt = plt
        self.out = out
        self.font = find_cjk_font()
        self.display_font = find_display_cjk_font()
        self.pdf = PdfPages(out)
        self.page_no = 0
        self.fig = None
        self.ax = None
        self.y = 0.0
        self.pages = 0
        self.images = 0
        self._new_page()

    def close(self) -> None:
        self._save_page()
        self.pdf.close()

    def _new_page(self) -> None:
        if self.fig is not None:
            self._save_page()
        self.page_no += 1
        self.fig = self.plt.figure(figsize=(PAGE_W, PAGE_H), dpi=170, facecolor=BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, PAGE_W)
        self.ax.set_ylim(0, PAGE_H)
        self.ax.axis("off")
        self.ax.set_facecolor(BG)
        self.ax.add_patch(self.plt.Rectangle((0, PAGE_H - 1.08), PAGE_W, 1.08, color="#09241d", alpha=0.98))
        self.ax.plot([MARGIN_L, PAGE_W - MARGIN_R], [PAGE_H - 0.62, PAGE_H - 0.62], color=ACCENT, lw=0.8, alpha=0.8)
        for x in [MARGIN_L + n * 0.32 for n in range(int(CONTENT_W / 0.32))]:
            for y in [PAGE_H - 0.98 + n * 0.16 for n in range(5)]:
                if (int(x * 100) + int(y * 100) + self.page_no) % 7 == 0:
                    self.ax.scatter([x], [y], s=2, color=ACCENT, alpha=0.22)
        self.ax.text(MARGIN_L, PAGE_H - 0.42, "CUCINA MARKET INTELLIGENCE", fontsize=9.2, color=TEXT, fontproperties=self.display_font, weight="black")
        self.ax.text(PAGE_W - MARGIN_R, PAGE_H - 0.42, "MACRO / SOCIAL / PORTFOLIO", fontsize=8.4, color=TEXT, fontproperties=self.font, ha="right", weight="black")
        self.y = PAGE_H - MARGIN_T - 0.28

    def _save_page(self) -> None:
        if self.fig is None or self.ax is None:
            return
        self.ax.text(
            PAGE_W / 2,
            0.30,
            f"{self.page_no}  |  generated by daily-report",
            ha="center",
            va="center",
            fontsize=8.0,
            color=TEXT,
            fontproperties=self.font,
            fontweight="black",
        )
        self.pdf.savefig(self.fig, facecolor=BG)
        self.pages += 1
        self.plt.close(self.fig)
        self.fig = None
        self.ax = None

    def _need_space(self, inches: float) -> None:
        if self.y - inches < MARGIN_B:
            self._new_page()

    def add_gap(self, inches: float) -> None:
        self.y -= inches
        if self.y < MARGIN_B:
            self._new_page()

    def add_text(
        self,
        text: str,
        size: float = 10.2,
        color: str = TEXT,
        weight: str = "black",
        indent: float = 0.0,
        display: bool = False,
    ) -> None:
        text = strip_inline_markdown(text)
        if not text.strip():
            self.add_gap(0.08)
            return
        max_units = max(18, int((CONTENT_W - indent) * 72 / (size * 0.70)))
        line_h = size / 72 * 1.45
        lines = wrap_visual(text, max_units)
        self._need_space(line_h * len(lines) + 0.04)
        for line in lines:
            self._need_space(line_h)
            assert self.ax is not None
            self.ax.text(
                MARGIN_L + indent,
                self.y,
                line,
                ha="left",
                va="top",
                fontsize=size,
                color=color,
                fontproperties=self.display_font if display else self.font,
                fontweight="black",
                clip_on=True,
            )
            self.y -= line_h
        self.y -= 0.025

    def add_heading(self, level: int, text: str) -> None:
        if level == 1:
            self.add_gap(0.04)
            self.add_text(natural_heading(text), size=20.5, color=TEXT, weight="black", display=True)
            self.add_gap(0.04)
        elif level == 2:
            text = natural_heading(text)
            self.add_gap(0.08)
            self._need_space(0.34)
            assert self.ax is not None
            self.ax.add_patch(self.plt.Rectangle((MARGIN_L - 0.05, self.y - 0.31), CONTENT_W + 0.10, 0.39, color=PANEL, ec=STROKE, lw=0.5))
            self.ax.text(MARGIN_L + 0.08, self.y - 0.01, text, ha="left", va="top", fontsize=14.4, color=TEXT, fontproperties=self.display_font, fontweight="black", clip_on=True)
            self.y -= 0.52
        else:
            self.add_gap(0.04)
            self.add_text(natural_heading(text), size=12.2, color=TEXT, weight="black", display=True)

    def add_image(self, path: Path, alt: str) -> None:
        if not path.exists():
            self.add_text(f"[image missing: {path}]", size=8, color=RED)
            return
        try:
            with PILImage.open(path) as img:
                img = img.convert("RGB")
                img_w, img_h = img.size
                height = CONTENT_W * img_h / img_w
                max_h = PAGE_H - MARGIN_T - MARGIN_B - 1.10
                if height > max_h:
                    height = max_h
                self._need_space(height + 0.34)
                assert self.ax is not None
                x0 = MARGIN_L
                x1 = MARGIN_L + CONTENT_W
                y1 = self.y
                y0 = self.y - height
                self.ax.add_patch(self.plt.Rectangle((x0 - 0.03, y0 - 0.03), CONTENT_W + 0.06, height + 0.06, color=PANEL_2, ec=STROKE, lw=0.5))
                self.ax.imshow(img, extent=(x0, x1, y0, y1), aspect="auto")
                self.y = y0 - 0.06
                if alt:
                    self.add_text(alt, size=6.8, color=MUTED)
                self.add_gap(0.08)
                self.images += 1
        except Exception as exc:
            self.add_text(f"[image render failed: {path} ({exc})]", size=8, color=RED)


def render_matplotlib(md_path: Path, text: str, out: Path) -> tuple[int, int, str]:
    renderer = MatplotlibRenderer(out)
    in_fence = False
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not stripped:
            renderer.add_gap(0.07)
            i += 1
            continue

        image_match = IMAGE_RE.search(line)
        if image_match:
            alt, target = image_match.groups()
            renderer.add_image(resolve_image(md_path, target), alt)
            i += 1
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match and not in_fence:
            level = len(heading_match.group(1))
            renderer.add_heading(level, strip_inline_markdown(heading_match.group(2)))
            i += 1
            continue

        if not in_fence and is_table_start(lines, i):
            rows = [split_table_row(lines[i])]
            i += 2
            while i < len(lines) and "|" in lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            for readable_line in table_rows_to_readable_lines(rows):
                renderer.add_text(readable_line, size=9.4, indent=0.12)
            renderer.add_gap(0.05)
            continue

        if stripped.startswith(("- ", "* ")):
            renderer.add_text("• " + stripped[2:].strip(), size=10.0, indent=0.16)
        elif re.match(r"^\d+\.\s+", stripped):
            renderer.add_text(stripped, size=10.0, indent=0.12)
        else:
            renderer.add_text(stripped, size=10.0 if in_fence else 10.4)
        i += 1

    renderer.close()
    return renderer.pages, renderer.images, "matplotlib"


def render_markdown(md_path: Path, text: str, out: Path, engine: str) -> tuple[int, int, str]:
    if engine in {"auto", "reportlab"}:
        try:
            return render_reportlab(md_path, text, out)
        except Exception as exc:
            if engine == "reportlab":
                raise
            print(f"ReportLab renderer unavailable, falling back to matplotlib: {exc}", file=sys.stderr)
    return render_matplotlib(md_path, text, out)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a daily US equities Markdown report to PDF.")
    parser.add_argument("--input", required=True, help="Input Markdown report path.")
    parser.add_argument("--out", required=True, help="Output PDF path.")
    parser.add_argument("--append-glossary", action="store_true", help="Append the standard glossary to the PDF when the Markdown report lacks it.")
    parser.add_argument("--update-md", action="store_true", help="Also append the standard glossary to the Markdown file when missing.")
    parser.add_argument("--engine", choices=["auto", "reportlab", "matplotlib"], default="auto", help="PDF rendering engine. auto prefers ReportLab and falls back to matplotlib.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    md_path = Path(args.input).resolve()
    out = Path(args.out).resolve()
    if not md_path.exists():
        print(f"Input Markdown does not exist: {md_path}", file=sys.stderr)
        return 2

    text = md_path.read_text(encoding="utf-8-sig")
    glossary_added = False
    if args.append_glossary or args.update_md:
        text, glossary_added = ensure_glossary(text)
        if args.update_md and glossary_added:
            md_path.write_text(text, encoding="utf-8", newline="\n")

    out.parent.mkdir(parents=True, exist_ok=True)
    pages, images, engine = render_markdown(md_path, text, out, args.engine)
    print(
        f"Wrote PDF: {out} | profile=daily-report engine={engine} pages={pages} images={images} "
        f"glossary={'added' if glossary_added else 'present'} md_updated={bool(args.update_md and glossary_added)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
