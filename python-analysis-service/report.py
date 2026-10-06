"""
report.py - builds the PDF / CSV export from the analysis result JSON
(the same JSON the platform already produced and stored in AnalysisJob.resultJson).

No file re-upload needed. Charts are drawn with reportlab's own graphics,
so no extra dependency (no matplotlib).
"""
import io
from collections import Counter
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import ScatterPlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

PRIMARY = colors.HexColor("#4f46e5")
PINK = colors.HexColor("#ec4899")
LIGHT = colors.HexColor("#f4f4f8")
GREY = colors.HexColor("#71717a")


# ==================== SMALL HELPERS ====================

def _fmt(v, nd=2):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        if v != v:  # NaN
            return "-"
        if abs(v) >= 1e6 or (0 < abs(v) < 1e-3):
            return f"{v:.3g}"
        return f"{v:,.{nd}f}"
    return str(v)


def _short(s, n=18):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _table(data, col_widths=None, font_size=8):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d4d4d8")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ==================== CHARTS ====================

def _histogram(chart):
    labels = chart.get("labels") or []
    values = chart.get("values") or []
    if not values:
        return None
    d = Drawing(460, 230)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 45, 60, 395, 150
    bc.data = [values]
    bc.bars[0].fillColor = PRIMARY
    bc.bars[0].strokeColor = None
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.angle = 35
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.categoryAxis.labels.dy = -4
    bc.categoryAxis.labels.fontSize = 7
    bc.valueAxis.valueMin = 0
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.visibleGrid = True
    bc.valueAxis.gridStrokeColor = colors.HexColor("#e4e4e7")
    d.add(bc)
    d.add(String(230, 8, f"Distribution of '{_short(chart.get('column', ''), 30)}'",
                 fontSize=8, textAnchor="middle", fillColor=GREY))
    return d


def _scatter(chart):
    pts = [(float(p[0]), float(p[1])) for p in (chart.get("points") or []) if len(p) >= 2]
    if len(pts) < 2:
        return None
    d = Drawing(460, 250)
    sp = ScatterPlot()
    sp.x, sp.y, sp.width, sp.height = 50, 40, 390, 180
    sp.data = [pts]
    sp.lineLabelFormat = None   # no value label on every point
    sp.xLabel = ""
    sp.yLabel = ""
    sp.lines[0].strokeWidth = 0
    sp.lines[0].symbol = makeMarker("FilledCircle")
    sp.lines[0].symbol.size = 3.5
    sp.lines[0].symbol.fillColor = PINK
    sp.lines[0].symbol.strokeColor = None
    sp.xValueAxis.labels.fontSize = 7
    sp.yValueAxis.labels.fontSize = 7
    sp.xValueAxis.visibleGrid = True
    sp.yValueAxis.visibleGrid = True
    sp.xValueAxis.gridStrokeColor = colors.HexColor("#e4e4e7")
    sp.yValueAxis.gridStrokeColor = colors.HexColor("#e4e4e7")
    d.add(sp)
    d.add(String(245, 8, f"X: {_short(chart.get('x_column', ''), 25)}",
                 fontSize=8, textAnchor="middle", fillColor=GREY))
    d.add(String(8, 135, f"Y: {_short(chart.get('y_column', ''), 25)}",
                 fontSize=8, textAnchor="middle", fillColor=GREY))
    return d


def _boxplots(boxplots):
    if not boxplots:
        return None
    row_h = 46
    n = len(boxplots)
    d = Drawing(460, row_h * n + 10)
    x0, x1 = 130, 430
    for i, (col, b) in enumerate(boxplots.items()):
        y = (n - 1 - i) * row_h + 14
        lo, q1, med, q3, hi = (b.get(k) for k in ("min", "q1", "median", "q3", "max"))
        if None in (lo, q1, med, q3, hi):
            continue
        span = (hi - lo) or 1.0

        def sx(v):
            return x0 + (v - lo) / span * (x1 - x0)

        d.add(String(8, y + 8, _short(col, 20), fontSize=8, fillColor=colors.black))
        d.add(Line(sx(lo), y + 10, sx(hi), y + 10, strokeColor=GREY, strokeWidth=1))
        d.add(Line(sx(lo), y + 4, sx(lo), y + 16, strokeColor=GREY, strokeWidth=1))
        d.add(Line(sx(hi), y + 4, sx(hi), y + 16, strokeColor=GREY, strokeWidth=1))
        d.add(Rect(sx(q1), y, max(sx(q3) - sx(q1), 1), 20, fillColor=colors.HexColor("#c7d2fe"),
                   strokeColor=PRIMARY, strokeWidth=1))
        d.add(Line(sx(med), y, sx(med), y + 20, strokeColor=PINK, strokeWidth=2))
        d.add(String(sx(lo), y - 9, _fmt(lo), fontSize=6.5, textAnchor="middle", fillColor=GREY))
        d.add(String(sx(hi), y - 9, _fmt(hi), fontSize=6.5, textAnchor="middle", fillColor=GREY))
        d.add(String(sx(med), y + 23, _fmt(med), fontSize=6.5, textAnchor="middle", fillColor=PINK))
    return d


def _heat_color(v):
    if v is None:
        return colors.HexColor("#e4e4e7")
    v = max(-1.0, min(1.0, float(v)))
    base = PRIMARY if v >= 0 else PINK
    a = abs(v)
    return colors.Color(1 - a * (1 - base.red), 1 - a * (1 - base.green), 1 - a * (1 - base.blue))


def _heatmap(hm):
    cols = (hm.get("columns") or [])[:10]
    data = hm.get("data") or []
    n = len(cols)
    if n < 2:
        return None
    rows = [[""] + [_short(c, 9) for c in cols]]
    for i in range(n):
        rows.append([_short(cols[i], 12)] + [_fmt(data[i][j], 2) for j in range(n)])
    cw = [70] + [min(40, 400 / n)] * n
    t = Table(rows, colWidths=cw)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.white),
    ]
    for i in range(n):
        for j in range(n):
            style.append(("BACKGROUND", (j + 1, i + 1), (j + 1, i + 1), _heat_color(data[i][j])))
    t.setStyle(TableStyle(style))
    return t


# ==================== PDF ====================

def build_pdf(result: dict, title: str = "Data Analysis Report", file_name: str = None) -> bytes:
    styles = getSampleStyleSheet()
    h_title = ParagraphStyle("T", parent=styles["Title"], fontSize=24, textColor=PRIMARY,
                             alignment=0, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=PRIMARY, spaceBefore=14, spaceAfter=8)
    normal = styles["Normal"]
    muted = ParagraphStyle("M", parent=normal, textColor=GREY, fontSize=8)

    story = []
    story.append(Paragraph(escape(title or "Data Analysis Report"), h_title))
    fname = file_name or result.get("file_name") or "-"
    story.append(Paragraph(f"<b>File:</b> {escape(str(fname))}", normal))
    story.append(Paragraph(f"<b>Analysed at:</b> {escape(str(result.get('timestamp') or '-'))}", normal))
    story.append(Paragraph(f"<b>Report generated:</b> {datetime.now():%Y-%m-%d %H:%M}", normal))

    # ---- Dataset overview + numeric stats
    stats = result.get("stats")
    if stats:
        story.append(Paragraph("Dataset Overview", h2))
        story.append(_table([
            ["Rows", "Columns"],
            [_fmt(stats.get("row_count")), _fmt(stats.get("column_count"))],
        ], col_widths=[120, 120], font_size=9))
        summary = stats.get("numeric_summary") or {}
        if summary:
            story.append(Paragraph("Numeric Summary", h2))
            keys = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
            rows = [["Column"] + keys]
            for col, s in list(summary.items())[:25]:
                rows.append([_short(col, 16)] + [_fmt(s.get(k)) for k in keys])
            story.append(_table(rows, col_widths=[85] + [48] * len(keys), font_size=7))

    # ---- Quality
    quality = result.get("quality")
    if quality:
        story.append(Paragraph("Data Quality", h2))
        q = quality.get("summary", {})
        story.append(_table([
            ["Metric", "Value"],
            ["Total rows", _fmt(q.get("total_rows"))],
            ["Total columns", _fmt(q.get("total_columns"))],
            ["Missing values", f"{_fmt(q.get('missing_values'))} ({_fmt(q.get('missing_pct'))}%)"],
            ["Duplicate rows", f"{_fmt(q.get('duplicate_rows'))} ({_fmt(q.get('duplicate_pct'))}%)"],
        ], col_widths=[160, 160], font_size=9))

        cstats = quality.get("column_stats") or []
        if cstats:
            story.append(Paragraph("Column Details", h2))
            rows = [["Column", "Type", "Missing %", "Unique", "Mean", "Min", "Max"]]
            for c in cstats[:40]:
                rows.append([_short(c.get("column"), 18), c.get("dtype"), _fmt(c.get("missing_pct")),
                             _fmt(c.get("unique")), _fmt(c.get("mean")), _fmt(c.get("min")),
                             _fmt(c.get("max"))])
            story.append(_table(rows, col_widths=[100, 55, 55, 50, 60, 60, 60], font_size=7))

        outliers = quality.get("outliers") or {}
        if outliers:
            story.append(Paragraph("Outliers (IQR method)", h2))
            rows = [["Column", "Outliers", "% of rows"]]
            for col, o in list(outliers.items())[:30]:
                rows.append([_short(col, 25), _fmt(o.get("count")), _fmt(o.get("percentage"))])
            story.append(_table(rows, col_widths=[180, 80, 80], font_size=8))

    # ---- ML
    ml = result.get("ml")
    if ml:
        story.append(Paragraph("Machine Learning - Clustering (K-Means)", h2))
        if ml.get("clusters"):
            counts = Counter(ml["clusters"])
            rows = [["Cluster", "Samples", "Share"]]
            total = sum(counts.values()) or 1
            for c in sorted(counts):
                rows.append([f"Cluster {c}", _fmt(counts[c]), f"{counts[c] / total * 100:.1f}%"])
            story.append(_table(rows, col_widths=[120, 100, 100], font_size=9))
        else:
            story.append(Paragraph(escape(str(ml.get("message", "No ML result."))), normal))

    # ---- Charts
    charts = result.get("chart_data") or {}
    if charts:
        story.append(PageBreak())
        story.append(Paragraph("Charts", ParagraphStyle("H1", parent=styles["Heading1"], textColor=PRIMARY)))

        def add_chart(heading, builder, payload):
            if not payload:
                return
            try:
                flowable = builder(payload)
            except Exception as e:  # never let one broken chart kill the whole PDF
                flowable = Paragraph(f"<i>Chart unavailable ({escape(str(e))})</i>", muted)
            if flowable is not None:
                story.append(KeepTogether([Paragraph(heading, h2), flowable, Spacer(1, 6)]))

        add_chart("Histogram", _histogram, charts.get("histogram"))
        add_chart("Box Plots (min / Q1 / median / Q3 / max)", _boxplots, charts.get("boxplots"))
        add_chart("Scatter Plot", _scatter, charts.get("scatter"))
        add_chart("Correlation Heatmap", _heatmap, charts.get("heatmap"))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(0.75 * inch, 0.5 * inch, "DataHub - Analysis Report")
        canvas.drawRightString(A4[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.85 * inch, title=title or "Report")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


# ==================== CSV ====================

def build_csv(result: dict, export_type: str = "stats") -> bytes:
    export_type = (export_type or "stats").lower()

    if export_type == "quality":
        cols = (result.get("quality") or {}).get("column_stats")
        if not cols:
            raise ValueError("No quality data in this analysis (run a STATS or BOTH analysis).")
        df = pd.DataFrame(cols)
    elif export_type == "outliers":
        out = (result.get("quality") or {}).get("outliers")
        if not out:
            raise ValueError("No outlier data in this analysis.")
        df = pd.DataFrame(out).T
        df.index.name = "column"
    elif export_type == "clusters":
        labels = (result.get("ml") or {}).get("clusters")
        if not labels:
            raise ValueError("No clustering result in this analysis (run an ML or BOTH analysis).")
        df = pd.DataFrame({"row": range(len(labels)), "cluster": labels})
    else:  # stats
        summary = (result.get("stats") or {}).get("numeric_summary")
        if not summary:
            raise ValueError("No numeric statistics in this analysis (run a STATS or BOTH analysis).")
        df = pd.DataFrame(summary).T
        df.index.name = "column"

    return df.to_csv().encode("utf-8-sig")  # utf-8-sig so Excel opens it correctly