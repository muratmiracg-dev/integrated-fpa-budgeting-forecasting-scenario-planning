"""Create a 12-page, vector-first FP&A executive report."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
OUT = ROOT / "Reports" / "Integrated_FPA_Executive_Report_12_Page_Vector_HD.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 960, 540
FONT = "DejaVu"
FONT_BOLD = "DejaVu-Bold"
pdfmetrics.registerFont(TTFont(FONT, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(
    TTFont(FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
)

C = {
    "navy": HexColor("#102A43"),
    "ink": HexColor("#101828"),
    "blue": HexColor("#2563EB"),
    "cyan": HexColor("#0EA5E9"),
    "teal": HexColor("#0F9D8B"),
    "green": HexColor("#16A34A"),
    "amber": HexColor("#D97706"),
    "red": HexColor("#DC2626"),
    "violet": HexColor("#7C3AED"),
    "white": HexColor("#FFFFFF"),
    "canvas": HexColor("#F7F9FC"),
    "line": HexColor("#D8E0EA"),
    "muted": HexColor("#667085"),
    "pale_blue": HexColor("#EAF2FF"),
    "pale_cyan": HexColor("#E9F8FE"),
    "pale_green": HexColor("#EAF8EF"),
    "pale_amber": HexColor("#FFF5E5"),
    "pale_red": HexColor("#FDECEC"),
    "pale_violet": HexColor("#F2EDFF"),
}


def df(name: str, dates: Iterable[str] = ()) -> pd.DataFrame:
    frame = pd.read_csv(DATA / name)
    for column in dates:
        frame[column] = pd.to_datetime(frame[column])
    return frame


annual = df("annual_pnl.csv")
variance = df("variance_analysis.csv")
scenarios = df("scenario_summary.csv")
risks = df("risk_summary.csv")
monthly = df("monthly_kpi_dashboard.csv", ("Month",))
business_units = df("business_unit_performance.csv", ("Month",))
departments = df("department_performance.csv", ("Month",))
models = df("forecast_model_comparison.csv")
headcount = df("headcount_summary.csv", ("Month",))
capex = df("capex_summary.csv", ("Month",))
insights = df("management_insights.csv")

fy26_f = annual[(annual.Year == 2026) & (annual.Version == "Forecast")].iloc[0]
fy26_b = annual[(annual.Year == 2026) & (annual.Version == "Budget")].iloc[0]
fy25 = annual[(annual.Year == 2025) & (annual.Version == "Actual")].iloc[0]
base = scenarios[scenarios.Scenario == "Base"].iloc[0]
stress = scenarios[scenarios.Scenario == "Stress"].iloc[0]
risk = risks.set_index("RiskMetric")["Value"].to_dict()

monthly_f = monthly[(monthly.Year == 2026) & (monthly.Version == "Forecast")].sort_values(
    "Month"
)
monthly_b = monthly[(monthly.Year == 2026) & (monthly.Version == "Budget")].sort_values(
    "Month"
)
h1 = variance[variance.Comparison == "H1 2026 Actual vs Budget"]
fy26_var = variance[variance.Comparison == "FY2026 Forecast vs Budget"]
champions = models[models.ChampionFlag].copy()

bu = business_units[
    (business_units.Year == 2026) & (business_units.Version == "Forecast")
].groupby("BusinessUnit", as_index=False)[
    ["RevenueTRY", "GrossProfitTRY", "EBITDATRY"]
].sum().sort_values("RevenueTRY", ascending=False)

dept = departments[
    (departments.Year == 2026) & (departments.Version == "Forecast")
].groupby("Department", as_index=False)[["OperatingExpenseTRY", "EBITDATRY"]].sum()
dept = dept.sort_values("OperatingExpenseTRY", ascending=False)

hc_f = headcount[
    (headcount.Version == "Forecast") & (headcount.Month.dt.year == 2026)
]
capex_f = capex[(capex.Version == "Forecast") & (capex.Month.dt.year == 2026)]


def m(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}TRY {abs(value) / 1_000_000:,.1f}M"


def b(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}TRY {abs(value) / 1_000_000_000:,.2f}B"


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def wrapped_lines(
    text: str, font: str, size: float, max_width: float
) -> list[str]:
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def text(
    c: Canvas,
    value: str,
    x: float,
    y: float,
    max_width: float,
    size: float = 12,
    color=C["ink"],
    bold: bool = False,
    leading: float | None = None,
    max_lines: int | None = None,
) -> float:
    font = FONT_BOLD if bold else FONT
    lines = wrapped_lines(value, font, size, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    leading = leading or size * 1.28
    c.setFont(font, size)
    c.setFillColor(color)
    current_y = y
    for line in lines:
        c.drawString(x, current_y, line)
        current_y -= leading
    return current_y


def panel(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    fill=C["white"],
    stroke=C["line"],
    radius: float = 9,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def header(c: Canvas, title: str, subtitle: str, page: int) -> None:
    c.setFillColor(C["canvas"])
    c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, "INTEGRATED FP&A | EXECUTIVE PLANNING SYSTEM", 36, 510, 500, 7.8, C["blue"], True)
    text(c, title, 36, 477, 610, 25, C["navy"], True)
    text(c, subtitle, 656, 480, 268, 8.8, C["muted"], False, 11, 3)
    c.setStrokeColor(C["blue"])
    c.setLineWidth(2)
    c.line(36, 451, 924, 451)
    text(c, f"{page:02d}", 900, 20, 24, 7.5, C["muted"], True)
    text(
        c,
        "Asteria Consumer Group | Synthetic portfolio dataset | TRY | 2023–2027 planning horizon",
        36,
        20,
        650,
        6.5,
        C["muted"],
    )


def metric(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    label: str,
    value: str,
    note: str,
    accent=C["blue"],
) -> None:
    panel(c, x, y, w, 96)
    c.setFillColor(accent)
    c.rect(x, y + 91, w, 5, fill=1, stroke=0)
    text(c, label.upper(), x + 13, y + 71, w - 26, 7.2, C["muted"], True)
    text(c, value, x + 13, y + 43, w - 26, 18, accent, True)
    text(c, note, x + 13, y + 17, w - 26, 7.3, C["muted"], False, 9, 2)


def insight(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    accent=C["blue"],
    fill=C["pale_blue"],
    body_size: float = 10,
) -> None:
    panel(c, x, y, w, h, fill, accent)
    c.setFillColor(accent)
    c.rect(x, y, 5, h, fill=1, stroke=0)
    text(c, title, x + 16, y + h - 25, w - 30, 11, accent, True)
    text(c, body, x + 16, y + h - 49, w - 30, body_size, C["ink"], False, body_size * 1.35)


def bar_chart(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    categories: Sequence[str],
    series: Sequence[tuple[str, Sequence[float], Color]],
    horizontal: bool = False,
    value_suffix: str = "",
) -> None:
    panel(c, x, y, w, h)
    left, bottom = x + 45, y + 45
    cw, ch = w - 70, h - 80
    maximum = max(max(values) for _, values, _ in series)
    maximum = max(maximum, 1)
    c.setStrokeColor(C["line"])
    c.setLineWidth(0.5)
    for tick in range(5):
        if horizontal:
            gx = left + cw * tick / 4
            c.line(gx, bottom, gx, bottom + ch)
            text(c, f"{maximum * tick / 4:.0f}", gx - 8, bottom - 18, 32, 6.5, C["muted"])
        else:
            gy = bottom + ch * tick / 4
            c.line(left, gy, left + cw, gy)
            text(c, f"{maximum * tick / 4:.0f}", left - 30, gy - 2, 26, 6.5, C["muted"])
    count = len(categories)
    group = (ch if horizontal else cw) / max(count, 1)
    bar_span = group * 0.68
    bar_size = bar_span / max(len(series), 1)
    for idx, category in enumerate(categories):
        if horizontal:
            base_y = bottom + ch - (idx + 1) * group + (group - bar_span) / 2
            text(c, category, x + 8, base_y + bar_span / 2 - 2, 110, 6.5, C["muted"])
        else:
            base_x = left + idx * group + (group - bar_span) / 2
            label = category if len(category) < 13 else category[:11] + "…"
            text(c, label, base_x, bottom - 18, group, 6.2, C["muted"])
        for s_idx, (_, values, color) in enumerate(series):
            value = values[idx]
            c.setFillColor(color)
            if horizontal:
                bw = cw * value / maximum
                by = base_y + s_idx * bar_size
                c.rect(left, by, bw, bar_size * 0.72, fill=1, stroke=0)
                text(c, f"{value:.1f}{value_suffix}", left + bw + 4, by + 1, 45, 6.2, C["ink"])
            else:
                bh = ch * value / maximum
                bx = base_x + s_idx * bar_size
                c.rect(bx, bottom, bar_size * 0.72, bh, fill=1, stroke=0)
                text(c, f"{value:.0f}{value_suffix}", bx, bottom + bh + 5, bar_size + 12, 6.2, C["ink"])
    legend_x = x + 45
    for name, _, color in series:
        c.setFillColor(color)
        c.rect(legend_x, y + 13, 8, 8, fill=1, stroke=0)
        text(c, name, legend_x + 13, y + 14, 150, 6.5, C["muted"])
        legend_x += 175


def line_chart(
    c: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    categories: Sequence[str],
    series: Sequence[tuple[str, Sequence[float], Color]],
) -> None:
    panel(c, x, y, w, h)
    left, bottom = x + 45, y + 45
    cw, ch = w - 70, h - 80
    maximum = max(max(values) for _, values, _ in series)
    minimum = min(min(values) for _, values, _ in series)
    if minimum > 0:
        minimum = 0
    span = max(maximum - minimum, 1)
    c.setStrokeColor(C["line"])
    c.setLineWidth(0.5)
    for tick in range(5):
        gy = bottom + ch * tick / 4
        c.line(left, gy, left + cw, gy)
        value = minimum + span * tick / 4
        text(c, f"{value:.0f}", left - 30, gy - 2, 28, 6.5, C["muted"])
    step = cw / max(len(categories) - 1, 1)
    for idx, category in enumerate(categories):
        tx = left + idx * step
        text(c, category, tx - 10, bottom - 18, 35, 6.1, C["muted"])
    for name, values, color in series:
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(2.2)
        points = []
        for idx, value in enumerate(values):
            px = left + idx * step
            py = bottom + (value - minimum) / span * ch
            points.append((px, py))
        for p1, p2 in zip(points, points[1:]):
            c.line(p1[0], p1[1], p2[0], p2[1])
        for px, py in points:
            c.circle(px, py, 2.4, fill=1, stroke=0)
    legend_x = x + 45
    for name, _, color in series:
        c.setStrokeColor(color)
        c.setLineWidth(2.2)
        c.line(legend_x, y + 17, legend_x + 15, y + 17)
        text(c, name, legend_x + 20, y + 14, 145, 6.5, C["muted"])
        legend_x += 180


def table(
    c: Canvas,
    x: float,
    y_top: float,
    widths: Sequence[float],
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_h: float = 28,
    font_size: float = 7.2,
) -> None:
    total = sum(widths)
    c.setFillColor(C["navy"])
    c.rect(x, y_top - row_h, total, row_h, fill=1, stroke=0)
    xx = x
    for idx, header_value in enumerate(headers):
        text(c, header_value, xx + 6, y_top - 18, widths[idx] - 12, font_size, C["white"], True)
        xx += widths[idx]
    for row_idx, row in enumerate(rows):
        y = y_top - (row_idx + 2) * row_h
        c.setFillColor(C["white"] if row_idx % 2 == 0 else C["canvas"])
        c.setStrokeColor(C["line"])
        c.rect(x, y, total, row_h, fill=1, stroke=1)
        xx = x
        for idx, value in enumerate(row):
            text(c, str(value), xx + 6, y + 9, widths[idx] - 12, font_size, C["ink"])
            xx += widths[idx]


def new_page(c: Canvas, title: str, subtitle: str, page: int) -> None:
    if page > 1:
        c.showPage()
    header(c, title, subtitle, page)


c = Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
c.setTitle("Integrated FP&A Budgeting, Forecasting & Scenario Planning System")
c.setAuthor("Murat Miraç Gedik")
c.setSubject("Professional FP&A portfolio project")

# 1 — Cover
c.setFillColor(C["navy"])
c.rect(0, 0, W, H, fill=1, stroke=0)
c.setFillColor(C["blue"])
c.rect(700, 0, 260, H, fill=1, stroke=0)
c.setFillColor(C["cyan"])
c.rect(735, 0, 225, H, fill=1, stroke=0)
c.setFillAlpha(0.16)
c.setFillColor(C["white"])
c.circle(835, 275, 150, fill=1, stroke=0)
c.setFillAlpha(1)
text(c, "INTEGRATED FP&A | PROFESSIONAL PORTFOLIO PROJECT", 42, 500, 570, 8.5, HexColor("#8FD8FF"), True)
text(c, "Integrated FP&A Budgeting,\nForecasting & Scenario Planning System", 42, 402, 635, 34, C["white"], True, 42)
text(c, "Actuals • Budget • Rolling Forecast • Cash • Working Capital • Scenario & Risk", 42, 245, 600, 13, HexColor("#D9E6F2"), False, 18)
text(c, "Murat Miraç Gedik", 42, 145, 420, 15, C["white"], True)
text(c, "Python • SQL • Power BI • DAX • Power Query • Microsoft Excel", 42, 115, 600, 10, HexColor("#8FD8FF"))
text(c, "Asteria Consumer Group | Synthetic portfolio dataset | TRY | July 2026", 42, 36, 620, 7, HexColor("#B8C6D8"))

# 2 — Executive overview
new_page(c, "Executive Overview", "FY2026 outlook and the management decision case", 2)
metric(c, 36, 329, 209, "FY2026 Revenue Forecast", b(fy26_f.RevenueTRY), f"{pct(fy26_f.RevenueTRY / fy26_b.RevenueTRY - 1)} vs budget", C["blue"])
metric(c, 261, 329, 209, "FY2026 EBITDA", m(fy26_f.EBITDATRY), f"{pct(fy26_f.EBITDAMarginPct)} margin", C["green"])
metric(c, 486, 329, 209, "Base-Case Ending Cash", m(base.EndingCashTRY), f"{m(base.MinimumCashTRY)} minimum", C["cyan"])
avg_wape = champions.WAPE.mean()
metric(c, 711, 329, 213, "Champion Accuracy", pct(1 - avg_wape), f"{len(champions)} business-unit models", C["violet"])
insight(
    c, 36, 116, 570, 180, "Management message",
    f"Revenue is forecast {pct(abs(fy26_f.RevenueTRY / fy26_b.RevenueTRY - 1))} below budget, yet operating-expense discipline lifts EBITDA {pct(fy26_f.EBITDATRY / fy26_b.EBITDATRY - 1)} above plan. The base case preserves liquidity. Management should close the commercial gap without sacrificing margin quality.",
    C["blue"], C["pale_blue"], 11,
)
insight(
    c, 626, 116, 298, 180, "Decision priorities",
    "1. Protect digital and subscription growth\n2. Correct the retail revenue gap\n3. Tighten working-capital discipline\n4. Run a monthly rolling-forecast cadence",
    C["teal"], C["pale_green"], 10,
)

# 3 — Architecture
new_page(c, "End-to-End Planning Architecture", "A reproducible flow from source data to management action", 3)
steps = [
    ("SOURCE", "Synthetic ERP, CRM, HR and capex"),
    ("TRANSFORM", "Python controls and forecasting"),
    ("STORE", "CSV analytics layer and SQLite"),
    ("MODEL", "SQL, Power Query, DAX and PBIP"),
    ("CONSUME", "Excel, Power BI, PDF and decks"),
]
colors = [C["blue"], C["cyan"], C["teal"], C["violet"], C["amber"]]
fills = [C["pale_blue"], C["pale_cyan"], C["pale_green"], C["pale_violet"], C["pale_amber"]]
for idx, (label, description) in enumerate(steps):
    x = 36 + idx * 178
    panel(c, x, 282, 154, 112, fills[idx], colors[idx])
    text(c, f"{idx + 1:02d}", x + 14, 368, 40, 8, colors[idx], True)
    text(c, label, x + 14, 340, 126, 11, C["navy"], True)
    text(c, description, x + 14, 310, 126, 7.4, C["muted"], False, 10, 3)
    if idx < 4:
        text(c, "→", x + 158, 331, 18, 15, C["muted"], True)
insight(c, 36, 116, 275, 130, "Reproducible", "One command regenerates data, runs forecasts, refreshes reporting tables, and repeats all controls.", C["blue"], C["pale_blue"], 9.5)
insight(c, 330, 116, 275, 130, "Auditable", "Version, period status, source system, assumptions, and validation evidence remain visible.", C["teal"], C["pale_green"], 9.5)
insight(c, 624, 116, 300, 130, "Portable", "PBIP embeds sample data; Excel, SQLite, SQL, Python, and documentation can be reviewed independently.", C["violet"], C["pale_violet"], 9.5)

# 4 — Historical performance
new_page(c, "Historical Performance", "Revenue scaled while profitability required active management", 4)
annual_trend = pd.concat([
    annual[(annual.Version == "Actual") & (annual.MonthsIncluded == 12)],
    annual[(annual.Year == 2026) & (annual.Version == "Forecast")],
]).sort_values("Year")
line_chart(
    c, 36, 120, 610, 296,
    annual_trend.Year.astype(str).tolist(),
    [
        ("Revenue (TRY M)", (annual_trend.RevenueTRY / 1e6).tolist(), C["blue"]),
        ("EBITDA (TRY M)", (annual_trend.EBITDATRY / 1e6).tolist(), C["green"]),
    ],
)
cagr = (fy25.RevenueTRY / annual_trend.iloc[0].RevenueTRY) ** 0.5 - 1
metric(c, 670, 320, 254, "2023–2025 Revenue CAGR", pct(cagr), "two-year growth rate", C["blue"])
metric(c, 670, 204, 254, "FY2025 EBITDA Margin", pct(fy25.EBITDAMarginPct), m(fy25.EBITDATRY), C["green"])
insight(c, 670, 120, 254, 66, "Interpretation", "Growth remained healthy, but margin quality stayed below FY2023.", C["amber"], C["pale_amber"], 8.3)

# 5 — H1 actual vs budget
new_page(c, "H1 2026 Actual vs Budget", "Revenue softness was offset by operating-cost discipline", 5)
metrics = ["Revenue", "Gross Profit", "Operating Expense", "EBITDA", "Net Income"]
rows = [h1[h1.Metric == item].iloc[0] for item in metrics]
bar_chart(
    c, 36, 120, 625, 296, metrics,
    [
        ("Actual (TRY M)", [row.CurrentValueTRY / 1e6 for row in rows], C["blue"]),
        ("Budget (TRY M)", [row.ComparatorValueTRY / 1e6 for row in rows], C["line"]),
    ],
)
rev_row = rows[0]
ebitda_row = rows[3]
metric(c, 685, 320, 239, "Revenue Variance", m(rev_row.VarianceTRY), pct(rev_row.VariancePct), C["red"])
metric(c, 685, 204, 239, "EBITDA Variance", f"+{m(ebitda_row.VarianceTRY)}", f"+{pct(ebitda_row.VariancePct)}", C["green"])
insight(c, 685, 120, 239, 66, "Read-through", "TRY 18.5M of opex savings kept EBITDA and net income above plan.", C["blue"], C["pale_blue"], 8.1)

# 6 — FY2026 forecast vs budget
new_page(c, "FY2026 Forecast vs Budget", "Lower revenue, stronger EBITDA, and disciplined spending", 6)
selected = [fy26_var[fy26_var.Metric == item].iloc[0] for item in metrics]
table(
    c, 36, 408, [145, 128, 128, 160, 100],
    ["Metric", "Forecast", "Budget", "Variance", "Status"],
    [
        [
            row.Metric,
            m(row.CurrentValueTRY),
            m(row.ComparatorValueTRY),
            f"{m(row.VarianceTRY)} ({pct(row.VariancePct)})",
            "Favorable" if row.FavorableFlag else "Unfavorable",
        ]
        for row in selected
    ],
    34,
    7.1,
)
insight(
    c, 720, 204, 204, 204, "Key outcome",
    f"Revenue is {m(abs(fy26_f.RevenueTRY - fy26_b.RevenueTRY))} below budget. EBITDA is {m(fy26_f.EBITDATRY - fy26_b.EBITDATRY)} above plan as operating expense remains controlled.",
    C["blue"], C["pale_blue"], 9.1,
)
insight(
    c, 36, 116, 888, 64, "Planning decision",
    "Deploy targeted commercial actions to close the revenue gap, while preserving productivity-based opex discipline and avoiding broad, value-destructive cuts.",
    C["teal"], C["pale_green"], 9,
)

# 7 — Revenue and cost drivers
new_page(c, "Revenue & Cost Drivers", "Business-unit mix and departmental spend shape the outlook", 7)
bar_chart(
    c, 36, 122, 430, 294,
    bu.BusinessUnit.tolist(),
    [("Revenue (TRY M)", (bu.RevenueTRY / 1e6).tolist(), C["blue"])],
    horizontal=True,
)
top_dept = dept.head(6)
bar_chart(
    c, 494, 122, 430, 294,
    top_dept.Department.tolist(),
    [("Operating Expense (TRY M)", (top_dept.OperatingExpenseTRY / 1e6).tolist(), C["violet"])],
    horizontal=True,
)
leader = bu.iloc[0]
insight(
    c, 36, 78, 888, 28, "Decision lens",
    f"{leader.BusinessUnit} contributes {pct(leader.RevenueTRY / fy26_f.RevenueTRY)} of FY2026 revenue. Protect scalable channels while linking departmental spend to explicit commercial and productivity outcomes.",
    C["blue"], C["pale_blue"], 8.2,
)

# 8 — Rolling forecast and governance
new_page(c, "Rolling Forecast & Model Governance", "Closed actuals, refreshed drivers, and evidence-based model selection", 8)
months = monthly_f.Month.dt.strftime("%b").tolist()
line_chart(
    c, 36, 172, 565, 244, months,
    [
        ("Rolling Forecast Revenue (TRY M)", (monthly_f.RevenueTRY / 1e6).tolist(), C["blue"]),
        ("Budget Revenue (TRY M)", (monthly_b.RevenueTRY / 1e6).tolist(), C["amber"]),
    ],
)
table(
    c, 625, 416, [115, 145, 72, 72],
    ["Business Unit", "Champion Model", "WAPE", "Accuracy"],
    [
        [row.BusinessUnit, row.Model, pct(row.WAPE), pct(1 - row.WAPE)]
        for row in champions.itertuples()
    ],
    28,
    6.3,
)
metric(c, 625, 160, 299, "Average Champion Accuracy", pct(1 - avg_wape), f"{len(champions)} governed models", C["green"])
insight(c, 625, 72, 299, 70, "Monthly cadence", "Close → variance review → driver refresh → model run → management approval", C["violet"], C["pale_violet"], 7.8)

# 9 — Cash and working capital
new_page(c, "Cash, Liquidity & Working Capital", "The plan stays liquid; cash conversion remains a controllable value lever", 9)
line_chart(
    c, 36, 155, 565, 261, months,
    [
        ("Forecast Ending Cash (TRY M)", (monthly_f.EndingCashTRY / 1e6).tolist(), C["blue"]),
        ("Budget Ending Cash (TRY M)", (monthly_b.EndingCashTRY / 1e6).tolist(), C["amber"]),
    ],
)
ending_f = monthly_f.iloc[-1].EndingCashTRY
ending_b = monthly_b.iloc[-1].EndingCashTRY
minimum_f = monthly_f.EndingCashTRY.min()
metric(c, 625, 320, 299, "FY2026 Ending Cash", m(ending_f), f"{m(ending_f - ending_b)} vs budget", C["blue"])
metric(c, 625, 204, 299, "FY2026 Minimum Cash", m(minimum_f), "positive liquidity buffer", C["green"])
insight(c, 625, 120, 299, 66, "Working-capital action", "Accelerate collections, reduce inventory days, and optimize supplier terms responsibly.", C["teal"], C["pale_green"], 8.3)

# 10 — Workforce and capital
new_page(c, "Workforce & Capital Allocation", "Headcount and capex are linked to strategic priorities", 10)
closing_month = hc_f.Month.max()
closing_fte = hc_f[hc_f.Month == closing_month].FTE.sum()
payroll = (hc_f.PayrollCostTRY + hc_f.BenefitsCostTRY).sum()
capex_spend = capex_f.CapexSpendTRY.sum()
metric(c, 36, 320, 274, "Closing FTE", f"{closing_fte:,.0f}", "December 2026 forecast", C["blue"])
metric(c, 330, 320, 274, "Payroll + Benefits", m(payroll), "FY2026 forecast", C["violet"])
metric(c, 624, 320, 300, "CAPEX", m(capex_spend), "FY2026 investment spend", C["teal"])
bar_chart(
    c, 36, 105, 565, 185,
    dept.head(6).Department.tolist(),
    [("Department Opex (TRY M)", (dept.head(6).OperatingExpenseTRY / 1e6).tolist(), C["violet"])],
    horizontal=True,
)
insight(
    c, 625, 105, 299, 185, "Governance rule",
    "Hiring and capex requests are assessed jointly through revenue capacity, productivity, cash impact, strategic fit, and resilience under downside scenarios.",
    C["blue"], C["pale_blue"], 9.4,
)

# 11 — Scenario and risk
new_page(c, "Scenario Planning & Risk", "Four coherent cases plus a 5,000-trial Monte Carlo distribution", 11)
bar_chart(
    c, 36, 164, 555, 252,
    scenarios.Scenario.tolist(),
    [
        ("EBITDA (TRY M)", (scenarios.EBITDATRY / 1e6).tolist(), C["green"]),
        ("Ending Cash (TRY M)", (scenarios.EndingCashTRY / 1e6).tolist(), C["blue"]),
    ],
)
metric(c, 615, 320, 309, "Revenue P10 / P50 / P90", f"{b(risk['Revenue P10'])}", f"{b(risk['Revenue P50'])} / {b(risk['Revenue P90'])}", C["blue"])
metric(c, 615, 204, 309, "Probability EBITDA Below Budget", pct(risk["Probability EBITDA Below Budget"]), "5,000 Monte Carlo trials", C["amber"])
insight(c, 615, 120, 309, 66, "Stress boundary", f"Stress ending cash remains positive at {m(stress.EndingCashTRY)}, but CCC extends to {stress.CashConversionCycleDays:.1f} days.", C["red"], C["pale_red"], 8.2)

# 12 — Recommendations and delivery
new_page(c, "Management Roadmap & Delivery", "A portfolio-ready system and a practical 90-day operating cadence", 12)
roadmap = [
    ("0–30 DAYS", "Formalize data ownership, close calendar, assumptions, and variance-accountability."),
    ("31–60 DAYS", "Operate driver refresh, forecast backtests, and monthly cross-functional review."),
    ("61–90 DAYS", "Automate scenario triggers, exception alerts, and management action tracking."),
]
for idx, (period, action) in enumerate(roadmap):
    x = 36 + idx * 296
    insight(c, x, 286, 272, 128, period, action, [C["blue"], C["teal"], C["violet"]][idx], [C["pale_blue"], C["pale_green"], C["pale_violet"]][idx], 9.2)
deliverables = [
    ("Python & SQL", "Reproducible planning engine, database, analytics views, tests"),
    ("Excel", "31-sheet formula-driven FP&A planning and scenario workbook"),
    ("Power BI", "11-page PBIP with embedded data, semantic model, and DAX measures"),
    ("Executive communication", "20-slide EN/TR decks, 12-page vector PDF, HD images"),
]
table(
    c, 36, 238, [190, 698], ["Delivery Layer", "What a reviewer can inspect"],
    [[a, b_] for a, b_ in deliverables], 31, 7.3,
)
text(c, "Prepared by Murat Miraç Gedik", 36, 60, 500, 13, C["navy"], True)
text(c, "FP&A • Forecasting • SQL • Python • Power BI • Excel • Executive Reporting", 36, 35, 700, 8.5, C["blue"])

c.save()
print(OUT)
