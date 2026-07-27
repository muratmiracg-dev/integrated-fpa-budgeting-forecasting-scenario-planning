import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const projectRoot = path.resolve(process.argv[2] || ".");
const dataDir = path.join(projectRoot, "Data");
const outputDir = path.join(projectRoot, "Presentation");

const C = {
  ink: "#101828",
  navy: "#102A43",
  blue: "#2563EB",
  cyan: "#0EA5E9",
  teal: "#0F9D8B",
  green: "#16A34A",
  amber: "#D97706",
  red: "#DC2626",
  violet: "#7C3AED",
  white: "#FFFFFF",
  canvas: "#F7F9FC",
  panel: "#FFFFFF",
  line: "#D8E0EA",
  muted: "#667085",
  paleBlue: "#EAF2FF",
  paleCyan: "#E9F8FE",
  paleGreen: "#EAF8EF",
  paleAmber: "#FFF5E5",
  paleRed: "#FDECEC",
  paleViolet: "#F2EDFF",
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function coerce(value) {
  if (value === "") return null;
  if (value === "True" || value === "TRUE") return true;
  if (value === "False" || value === "FALSE") return false;
  if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(value)) return Number(value);
  return value;
}

async function loadCsv(filename) {
  const parsed = parseCsv(await fs.readFile(path.join(dataDir, filename), "utf8"));
  const headers = parsed[0];
  return parsed.slice(1).map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, coerce(row[index])])),
  );
}

const [
  annual,
  monthly,
  variance,
  scenarios,
  risks,
  cashSummary,
  modelComparison,
  businessUnits,
  departments,
  headcount,
  capex,
  monthlyKpi,
  managementInsights,
] = await Promise.all([
  loadCsv("annual_pnl.csv"),
  loadCsv("monthly_pnl.csv"),
  loadCsv("variance_analysis.csv"),
  loadCsv("scenario_summary.csv"),
  loadCsv("risk_summary.csv"),
  loadCsv("cash_flow_summary.csv"),
  loadCsv("forecast_model_comparison.csv"),
  loadCsv("business_unit_performance.csv"),
  loadCsv("department_performance.csv"),
  loadCsv("headcount_summary.csv"),
  loadCsv("capex_summary.csv"),
  loadCsv("monthly_kpi_dashboard.csv"),
  loadCsv("management_insights.csv"),
]);

const fy26Forecast = annual.find((row) => row.Year === 2026 && row.Version === "Forecast");
const fy26Budget = annual.find((row) => row.Year === 2026 && row.Version === "Budget");
const fy25Actual = annual.find((row) => row.Year === 2025 && row.Version === "Actual");
const baseScenario = scenarios.find((row) => row.Scenario === "Base");
const riskMap = Object.fromEntries(risks.map((row) => [row.RiskMetric, row.Value]));
const cashMap = Object.fromEntries(cashSummary.map((row) => [row.Version, row]));

const annualTrend = [
  ...annual.filter((row) => row.Version === "Actual" && row.MonthsIncluded === 12),
  fy26Forecast,
];

const fy26Variance = variance.filter((row) => row.Comparison === "FY2026 Forecast vs Budget");
const h1Variance = variance.filter((row) => row.Comparison === "H1 2026 Actual vs Budget");

const buForecast = businessUnits.filter((row) => row.Version === "Forecast" && row.Year === 2026);
const buSummary = [...new Set(buForecast.map((row) => row.BusinessUnit))]
  .map((name) => {
    const rows = buForecast.filter((row) => row.BusinessUnit === name);
    return {
      name,
      revenue: rows.reduce((sum, row) => sum + row.RevenueTRY, 0),
      ebitda: rows.reduce((sum, row) => sum + row.EBITDATRY, 0),
      grossProfit: rows.reduce((sum, row) => sum + row.GrossProfitTRY, 0),
    };
  })
  .sort((a, b) => b.revenue - a.revenue);

const deptForecast = departments.filter((row) => row.Version === "Forecast" && row.Year === 2026);
const deptSummary = [...new Set(deptForecast.map((row) => row.Department))]
  .map((name) => {
    const rows = deptForecast.filter((row) => row.Department === name);
    return {
      name,
      opex: rows.reduce((sum, row) => sum + row.OperatingExpenseTRY, 0),
      ebitda: rows.reduce((sum, row) => sum + row.EBITDATRY, 0),
    };
  })
  .sort((a, b) => b.opex - a.opex);

const champions = modelComparison.filter((row) => row.ChampionFlag === true);
const y2026ForecastMonths = monthlyKpi
  .filter((row) => row.Version === "Forecast" && row.Year === 2026)
  .sort((a, b) => String(a.Month).localeCompare(String(b.Month)));
const y2026BudgetMonths = monthlyKpi
  .filter((row) => row.Version === "Budget" && row.Year === 2026)
  .sort((a, b) => String(a.Month).localeCompare(String(b.Month)));
const y2026ActualMonths = monthlyKpi
  .filter((row) => row.Version === "Actual" && row.Year === 2026)
  .sort((a, b) => String(a.Month).localeCompare(String(b.Month)));
const hcForecast = headcount.filter((row) => row.Version === "Forecast" && String(row.Month).startsWith("2026"));
const capexForecast = capex.filter((row) => row.Version === "Forecast" && String(row.Month).startsWith("2026"));

const COPY = {
  en: {
    brand: "INTEGRATED FP&A | EXECUTIVE PLANNING SYSTEM",
    title: "Integrated FP&A Budgeting,\nForecasting & Scenario Planning System",
    subtitle: "A governed financial planning platform connecting actuals, budgets, rolling forecasts, liquidity, operating drivers, and risk",
    author: "Murat Miraç Gedik  |  Professional Portfolio Project  |  July 2026",
    notice: "Asteria Consumer Group | Synthetic portfolio dataset | TRY | 2023–2027 planning horizon",
    section: [
      ["Executive Summary", "The FY2026 decision case in four numbers"],
      ["Business Challenge", "Why disconnected planning creates slow and inconsistent decisions"],
      ["Objectives & Scope", "A unified operating model for performance management"],
      ["Data Landscape", "Granular finance, workforce, capital, and commercial signals"],
      ["Solution Architecture", "A reproducible path from source data to executive action"],
      ["Semantic Model & Controls", "Calendar-centered analytics with auditable financial logic"],
      ["Historical Performance", "Growth continued while profitability required active management"],
      ["Revenue Drivers", "Business-unit mix defines the growth outlook"],
      ["Cost Structure", "Where gross margin and operating leverage are created"],
      ["H1 Actual vs Budget", "Revenue softness was offset by operating cost discipline"],
      ["FY2026 Forecast vs Budget", "Lower revenue, stronger EBITDA, and a higher closing cash position"],
      ["Rolling Forecast", "Monthly outlook combines closed actuals with a refreshed forward view"],
      ["Forecast Governance", "Model selection is evidence-based and business-unit specific"],
      ["Cash & Liquidity", "The plan preserves liquidity across the operating horizon"],
      ["Working Capital", "Cash conversion is a controllable source of value"],
      ["Workforce & Capital", "Headcount and capex remain linked to strategic priorities"],
      ["Scenario Planning", "Four coherent cases quantify growth, margin, and cash trade-offs"],
      ["Risk & Uncertainty", "Monte Carlo simulation exposes the distribution around the plan"],
      ["Management Roadmap", "A 90-day path from portfolio model to an operating FP&A cadence"],
    ],
    close: "One connected view of performance,\nplan, cash, and risk",
    closeBody: "A portfolio-ready FP&A system demonstrating financial modeling, statistical forecasting, business intelligence, data engineering, and executive communication.",
    thankYou: "THANK YOU",
  },
  tr: {
    brand: "ENTEGRE FP&A | YÖNETİCİ PLANLAMA SİSTEMİ",
    title: "Entegre FP&A Bütçeleme,\nTahminleme ve Senaryo Planlama Sistemi",
    subtitle: "Gerçekleşenler, bütçe, rolling forecast, likidite, operasyonel sürücüler ve riski tek yönetişimli platformda birleştiren finansal planlama çözümü",
    author: "Murat Miraç Gedik  |  Profesyonel Portföy Projesi  |  Temmuz 2026",
    notice: "Asteria Consumer Group | Sentetik portföy verisi | TRY | 2023–2027 planlama dönemi",
    section: [
      ["Yönetici Özeti", "FY2026 karar görünümünü özetleyen dört temel gösterge"],
      ["İş Problemi", "Dağınık planlama neden yavaş ve tutarsız karar üretir"],
      ["Hedefler ve Kapsam", "Performans yönetimi için birleşik çalışma modeli"],
      ["Veri Kapsamı", "Finans, iş gücü, yatırım ve ticari performans sinyalleri"],
      ["Çözüm Mimarisi", "Kaynak veriden yönetici aksiyonuna tekrarlanabilir akış"],
      ["Semantik Model ve Kontroller", "Takvim merkezli, denetlenebilir finansal mantık"],
      ["Tarihsel Performans", "Büyüme sürerken kârlılık aktif yönetim gerektirdi"],
      ["Gelir Sürücüleri", "İş birimi karması büyüme görünümünü belirliyor"],
      ["Maliyet Yapısı", "Brüt marj ve operasyonel kaldıraç nerede oluşuyor"],
      ["H1 Gerçekleşen ve Bütçe", "Gelir zayıflığı gider disipliniyle dengelendi"],
      ["FY2026 Tahmin ve Bütçe", "Daha düşük gelir, daha güçlü EBITDA ve yüksek kapanış nakdi"],
      ["Rolling Forecast", "Kapanan gerçekleşenler ile güncellenen ileri görünümün birleşimi"],
      ["Tahmin Yönetişimi", "Model seçimi kanıta ve iş birimine göre yapılıyor"],
      ["Nakit ve Likidite", "Plan, operasyonel dönem boyunca likiditeyi koruyor"],
      ["İşletme Sermayesi", "Nakit dönüşüm döngüsü yönetilebilir bir değer kaynağıdır"],
      ["İş Gücü ve Yatırım", "Kadro ve capex stratejik önceliklere bağlanıyor"],
      ["Senaryo Planlama", "Dört tutarlı vaka büyüme, marj ve nakit dengesini ölçüyor"],
      ["Risk ve Belirsizlik", "Monte Carlo simülasyonu planın çevresindeki dağılımı gösteriyor"],
      ["Yönetim Yol Haritası", "Portföy modelinden çalışan FP&A ritmine 90 günlük geçiş"],
    ],
    close: "Performans, plan, nakit ve risk için\ntek bağlantılı görünüm",
    closeBody: "Finansal modelleme, istatistiksel tahminleme, iş zekâsı, veri mühendisliği ve yönetici iletişimini birleştiren portföy seviyesinde FP&A sistemi.",
    thankYou: "TEŞEKKÜRLER",
  },
};

const TR = {
  Revenue: "Gelir",
  COGS: "Satışların Maliyeti",
  "Gross Profit": "Brüt Kâr",
  "Operating Expense": "Faaliyet Gideri",
  EBITDA: "EBITDA",
  "Net Income": "Net Kâr",
  "Digital Commerce": "Dijital Ticaret",
  "Retail Stores": "Perakende Mağazalar",
  "Subscription Services": "Abonelik Hizmetleri",
  Wholesale: "Toptan Satış",
  Upside: "Yukarı Yönlü",
  Base: "Baz",
  Downside: "Aşağı Yönlü",
  Stress: "Stres",
};

function local(value, lang) {
  return lang === "tr" ? (TR[value] || value) : value;
}

function fmtM(value, lang) {
  return `${lang === "tr" ? "₺" : "TRY "}${(value / 1_000_000).toFixed(1)}M`;
}

function fmtB(value, lang) {
  return `${lang === "tr" ? "₺" : "TRY "}${(value / 1_000_000_000).toFixed(2)}B`;
}

function fmtPct(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
    name: options.name,
  });
  shape.text = text;
  shape.text.style = {
    fontFamily: "Arial",
    fontSize: options.fontSize ?? 18,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
  };
  shape.text.alignment = options.align ?? "left";
  shape.text.verticalAlignment = options.vertical ?? "top";
  return shape;
}

function addPanel(slide, position, options = {}) {
  return slide.shapes.add({
    geometry: options.geometry ?? "roundRect",
    position,
    fill: options.fill ?? C.panel,
    line: {
      style: "solid",
      fill: options.line ?? C.line,
      width: options.lineWidth ?? 1,
    },
    borderRadius: "rounded-xl",
  });
}

function addHeader(slide, copy, page) {
  const [title, subtitle] = copy.section[page - 2];
  slide.background.fill = C.canvas;
  addText(slide, copy.brand, { left: 48, top: 25, width: 650, height: 20 }, {
    fontSize: 11,
    bold: true,
    color: C.blue,
  });
  addText(slide, title, { left: 48, top: 53, width: 790, height: 50 }, {
    fontSize: 34,
    bold: true,
    color: C.navy,
  });
  addText(slide, subtitle, { left: 850, top: 60, width: 382, height: 42 }, {
    fontSize: 13,
    color: C.muted,
    align: "right",
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 48, top: 116, width: 1184, height: 3 },
    fill: C.blue,
    line: { style: "solid", fill: C.blue, width: 0 },
  });
  addText(slide, String(page).padStart(2, "0"), { left: 1180, top: 680, width: 52, height: 18 }, {
    fontSize: 10,
    bold: true,
    color: C.muted,
    align: "right",
  });
}

function addFooter(slide, copy) {
  addText(slide, copy.notice, { left: 48, top: 680, width: 720, height: 16 }, {
    fontSize: 9,
    color: C.muted,
  });
}

function addNotes(slide, sources, note = "") {
  const text = [
    note,
    "[Sources]",
    ...sources.map((source) => `- ${source}`),
    "[/Sources]",
  ].filter(Boolean).join("\n");
  slide.speakerNotes.textFrame.setText(text);
  slide.speakerNotes.setVisible(true);
}

function sources(...files) {
  return files.map((file) => `Internal synthetic project source: ${file}`);
}

function metricCard(slide, x, y, w, label, value, note, accent = C.blue) {
  addPanel(slide, { left: x, top: y, width: w, height: 144 }, { fill: C.white });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height: 7 },
    fill: accent,
    line: { style: "solid", fill: accent, width: 0 },
  });
  addText(slide, label.toUpperCase(), { left: x + 18, top: y + 24, width: w - 36, height: 20 }, {
    fontSize: 11,
    bold: true,
    color: C.muted,
  });
  addText(slide, value, { left: x + 18, top: y + 54, width: w - 36, height: 42 }, {
    fontSize: 27,
    bold: true,
    color: accent,
  });
  addText(slide, note, { left: x + 18, top: y + 108, width: w - 36, height: 23 }, {
    fontSize: 11,
    color: C.muted,
  });
}

function insightBox(slide, x, y, w, h, title, body, accent = C.blue, fill = C.paleBlue) {
  addPanel(slide, { left: x, top: y, width: w, height: h }, { fill, line: accent });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: 6, height: h },
    fill: accent,
    line: { style: "solid", fill: accent, width: 0 },
  });
  addText(slide, title, { left: x + 20, top: y + 17, width: w - 40, height: 27 }, {
    fontSize: 16,
    bold: true,
    color: accent,
  });
  addText(slide, body, { left: x + 20, top: y + 50, width: w - 40, height: h - 62 }, {
    fontSize: 14,
    color: C.ink,
  });
}

function bulletList(slide, items, x, y, w, options = {}) {
  const rowHeight = options.rowHeight ?? 55;
  items.forEach((item, index) => {
    const top = y + index * rowHeight;
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: x, top: top + 6, width: 11, height: 11 },
      fill: options.accent ?? C.blue,
      line: { style: "solid", fill: options.accent ?? C.blue, width: 0 },
    });
    addText(slide, item, { left: x + 24, top, width: w - 24, height: rowHeight - 4 }, {
      fontSize: options.fontSize ?? 17,
      color: options.color ?? C.ink,
    });
  });
}

function addBarChart(slide, position, categories, series, options = {}) {
  return slide.charts.add("bar", {
    position,
    categories,
    series: series.map((item) => ({
      name: item.name,
      categories,
      values: item.values,
      fill: item.color,
    })),
    hasLegend: options.hasLegend ?? series.length > 1,
    legend: { position: "bottom", overlay: false },
    dataLabels: {
      showValue: options.showValue ?? true,
      position: "outEnd",
      numberFormatCode: options.valueFormat ?? "0.0",
    },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: {
      visible: true,
      line: { style: "solid", width: 1, fill: C.line },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    yAxis: {
      visible: true,
      min: options.min ?? 0,
      max: options.max,
      numberFormatCode: options.axisFormat ?? "0.0",
      majorGridlines: { style: "solid", width: 1, fill: C.line },
      line: { style: "solid", width: 0, fill: C.white },
      textStyle: { typeface: "Arial", fontSize: "11px", color: C.muted },
    },
    barOptions: {
      direction: options.horizontal ? "bar" : "column",
      grouping: options.grouping ?? "clustered",
      gapWidth: 80,
    },
  });
}

function addLineChart(slide, position, categories, series, options = {}) {
  return slide.charts.add("line", {
    position,
    categories,
    series: series.map((item) => ({
      name: item.name,
      categories,
      values: item.values,
      line: { style: "solid", width: 3, fill: item.color },
      marker: { symbol: "circle", size: 4 },
    })),
    hasLegend: true,
    legend: { position: "bottom", overlay: false },
    chartFill: C.white,
    chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: {
      visible: true,
      line: { style: "solid", width: 1, fill: C.line },
      textStyle: { typeface: "Arial", fontSize: "10px", color: C.muted },
    },
    yAxis: {
      visible: true,
      min: options.min ?? 0,
      max: options.max,
      numberFormatCode: options.axisFormat ?? "0.0",
      majorGridlines: { style: "solid", width: 1, fill: C.line },
      line: { style: "solid", width: 0, fill: C.white },
      textStyle: { typeface: "Arial", fontSize: "10px", color: C.muted },
    },
    lineOptions: { grouping: "standard" },
  });
}

function simpleTable(slide, x, y, widths, headers, rows, options = {}) {
  const rowHeight = options.rowHeight ?? 38;
  const totalWidth = widths.reduce((sum, width) => sum + width, 0);
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: totalWidth, height: rowHeight },
    fill: C.navy,
    line: { style: "solid", fill: C.navy, width: 0 },
  });
  let left = x;
  headers.forEach((header, index) => {
    addText(slide, header, { left: left + 8, top: y + 9, width: widths[index] - 16, height: rowHeight - 14 }, {
      fontSize: options.headerSize ?? 11,
      bold: true,
      color: C.white,
    });
    left += widths[index];
  });
  rows.forEach((row, rowIndex) => {
    const top = y + (rowIndex + 1) * rowHeight;
    slide.shapes.add({
      geometry: "rect",
      position: { left: x, top, width: totalWidth, height: rowHeight },
      fill: rowIndex % 2 ? C.canvas : C.white,
      line: { style: "solid", fill: C.line, width: 0.5 },
    });
    let cellLeft = x;
    row.forEach((value, index) => {
      addText(slide, String(value), { left: cellLeft + 8, top: top + 8, width: widths[index] - 16, height: rowHeight - 13 }, {
        fontSize: options.fontSize ?? 11,
        color: C.ink,
      });
      cellLeft += widths[index];
    });
  });
}

function addProcess(slide, items, y, lang) {
  const width = 205;
  const gap = 29;
  items.forEach((item, index) => {
    const x = 48 + index * (width + gap);
    addPanel(slide, { left: x, top: y, width, height: 150 }, {
      fill: [C.paleBlue, C.paleCyan, C.paleGreen, C.paleViolet, C.paleAmber][index],
      line: [C.blue, C.cyan, C.green, C.violet, C.amber][index],
    });
    addText(slide, String(index + 1).padStart(2, "0"), { left: x + 18, top: y + 16, width: 42, height: 25 }, {
      fontSize: 14,
      bold: true,
      color: [C.blue, C.cyan, C.green, C.violet, C.amber][index],
    });
    addText(slide, item[0], { left: x + 18, top: y + 51, width: width - 36, height: 38 }, {
      fontSize: 17,
      bold: true,
      color: C.navy,
    });
    addText(slide, item[1], { left: x + 18, top: y + 98, width: width - 36, height: 39 }, {
      fontSize: 11,
      color: C.muted,
    });
    if (index < items.length - 1) {
      addText(slide, "→", { left: x + width + 5, top: y + 58, width: 20, height: 28 }, {
        fontSize: 21,
        bold: true,
        color: C.muted,
        align: "center",
      });
    }
  });
}

function createDeck(lang) {
  const copy = COPY[lang];
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1 — Cover
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.navy;
    slide.shapes.add({
      geometry: "rect",
      position: { left: 930, top: 0, width: 350, height: 720 },
      fill: C.blue,
      line: { style: "solid", fill: C.blue, width: 0 },
    });
    slide.shapes.add({
      geometry: "rect",
      position: { left: 975, top: 0, width: 305, height: 720 },
      fill: C.cyan,
      line: { style: "solid", fill: C.cyan, width: 0 },
      opacity: 0.18,
    });
    addText(slide, copy.brand, { left: 56, top: 44, width: 650, height: 24 }, {
      fontSize: 12,
      bold: true,
      color: "#8FD8FF",
    });
    addText(slide, copy.title, { left: 56, top: 160, width: 850, height: 210 }, {
      fontSize: 51,
      bold: true,
      color: C.white,
    });
    addText(slide, copy.subtitle, { left: 56, top: 400, width: 790, height: 90 }, {
      fontSize: 19,
      color: "#D9E6F2",
    });
    addText(slide, copy.author, { left: 56, top: 555, width: 750, height: 28 }, {
      fontSize: 14,
      color: C.white,
    });
    addText(slide, copy.notice, { left: 56, top: 660, width: 780, height: 18 }, {
      fontSize: 10,
      color: "#B8C6D8",
    });
    addNotes(slide, sources("README.md", "Data/project_metadata.csv"));
  }

  // 2 — Executive summary
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 2);
    const revVariance = (fy26Forecast.RevenueTRY / fy26Budget.RevenueTRY) - 1;
    metricCard(slide, 48, 155, 276, lang === "tr" ? "FY2026 Gelir Tahmini" : "FY2026 Revenue Forecast", fmtB(fy26Forecast.RevenueTRY, lang), `${fmtPct(revVariance)} ${lang === "tr" ? "bütçeye göre" : "vs budget"}`, C.blue);
    metricCard(slide, 344, 155, 276, "EBITDA", fmtM(fy26Forecast.EBITDATRY, lang), `${fmtPct(fy26Forecast.EBITDAMarginPct)} ${lang === "tr" ? "marj" : "margin"}`, C.green);
    metricCard(slide, 640, 155, 276, lang === "tr" ? "Baz Senaryo Kapanış Nakdi" : "Base-Case Ending Cash", fmtM(baseScenario.EndingCashTRY, lang), `${fmtM(baseScenario.MinimumCashTRY, lang)} ${lang === "tr" ? "minimum nakit" : "minimum cash"}`, C.cyan);
    metricCard(slide, 936, 155, 296, lang === "tr" ? "Tahmin Doğruluğu" : "Forecast Accuracy", fmtPct(1 - champions.reduce((s, r) => s + r.WAPE, 0) / champions.length), `${champions.length} ${lang === "tr" ? "iş birimi modeli" : "business-unit champions"}`, C.violet);
    insightBox(
      slide, 48, 338, 770, 252,
      lang === "tr" ? "Yönetim mesajı" : "Management message",
      lang === "tr"
        ? `Gelir tahmini bütçenin ${fmtPct(Math.abs(revVariance))} altında olsa da, faaliyet gideri disiplini EBITDA'yı bütçenin ${fmtPct((fy26Forecast.EBITDATRY / fy26Budget.EBITDATRY) - 1)} üzerine taşıyor. Baz senaryo likiditeyi koruyor; asıl odak gelir açığını kapatırken marj kalitesini sürdürmek olmalı.`
        : `Revenue is forecast ${fmtPct(Math.abs(revVariance))} below budget, yet operating-cost discipline lifts EBITDA ${fmtPct((fy26Forecast.EBITDATRY / fy26Budget.EBITDATRY) - 1)} above plan. The base case preserves liquidity; management should close the revenue gap without sacrificing margin quality.`,
      C.blue,
      C.paleBlue,
    );
    insightBox(
      slide, 842, 338, 390, 252,
      lang === "tr" ? "Karar öncelikleri" : "Decision priorities",
      lang === "tr"
        ? "1. Dijital ve abonelik büyümesini koru\n2. Perakende gelir açığını düzelt\n3. İşletme sermayesi disiplinini güçlendir\n4. Aylık rolling forecast ritmini işlet"
        : "1. Protect digital and subscription growth\n2. Correct the retail revenue gap\n3. Tighten working-capital discipline\n4. Operate a monthly rolling-forecast cadence",
      C.teal,
      C.paleGreen,
    );
    addFooter(slide, copy);
    addNotes(slide, sources("Data/annual_pnl.csv", "Data/cash_flow_summary.csv", "Data/forecast_model_comparison.csv"));
  }

  // 3 — Business challenge
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 3);
    const cards = lang === "tr"
      ? [
          ["Parçalı veri", "Finans, satış, insan kaynağı ve capex farklı tablolarda tutulduğunda tek gerçek görünüm kaybolur."],
          ["Statik bütçe", "Yıllık bütçe, değişen talep ve maliyet koşullarına tek başına yeterince hızlı yanıt vermez."],
          ["Nakit kör noktası", "Gelir ve kâr görünürken işletme sermayesi ile likidite riski geç fark edilebilir."],
          ["Model riski", "Tahmin yöntemi ve varsayımlar yönetişimsizse plan güvenilirliğini kaybeder."],
        ]
      : [
          ["Fragmented data", "A single version of truth disappears when finance, sales, workforce, and capex live in separate files."],
          ["Static budget", "An annual plan alone cannot respond quickly enough to changing demand and cost conditions."],
          ["Cash blind spot", "Working-capital and liquidity risks can remain hidden even when revenue and profit are visible."],
          ["Model risk", "Forecast credibility deteriorates when methods and assumptions lack governance."],
        ];
    cards.forEach((item, index) => {
      const x = 48 + (index % 2) * 594;
      const y = 156 + Math.floor(index / 2) * 205;
      insightBox(slide, x, y, 570, 176, item[0], item[1], [C.blue, C.cyan, C.amber, C.red][index], [C.paleBlue, C.paleCyan, C.paleAmber, C.paleRed][index]);
    });
    insightBox(slide, 48, 584, 1164, 64, lang === "tr" ? "Temel soru" : "Core question", lang === "tr" ? "Gerçekleşen performansı, ileri görünümü, nakdi ve riski aynı karar çerçevesinde nasıl yönetiriz?" : "How can actual performance, forward outlook, cash, and risk be managed within one decision framework?", C.navy, C.white);
    addFooter(slide, copy);
    addNotes(slide, sources("Docs/executive_summary.md", "Docs/methodology.md"));
  }

  // 4 — Objectives & scope
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 4);
    addProcess(slide, lang === "tr"
      ? [
          ["Gerçekleşen", "42 aylık finansal ve operasyonel geçmiş"],
          ["Bütçe", "FY2026 hedef ve departman planı"],
          ["Rolling Forecast", "18 aylık güncellenen ileri görünüm"],
          ["Senaryo", "Yukarı, Baz, Aşağı, Stres"],
          ["Karar", "KPI, aksiyon, sahiplik ve kontrol"],
        ]
      : [
          ["Actuals", "42 months of financial and operating history"],
          ["Budget", "FY2026 targets and departmental plan"],
          ["Rolling Forecast", "18-month refreshed forward view"],
          ["Scenarios", "Upside, Base, Downside, Stress"],
          ["Decision", "KPIs, actions, ownership, and controls"],
        ], 164, lang);
    const objectives = lang === "tr"
      ? ["P&L, nakit akışı ve işletme sermayesini bağlamak", "Bütçe sapmalarını sürücü bazında açıklamak", "Tahmin performansını geri testlerle ölçmek", "Yönetici ve planlama ekipleri için tekrar kullanılabilir teslimatlar üretmek"]
      : ["Connect P&L, cash flow, and working capital", "Explain budget variance through operating drivers", "Measure forecast performance through backtesting", "Deliver reusable outputs for executives and planning teams"];
    bulletList(slide, objectives, 70, 390, 550, { fontSize: 17, rowHeight: 54 });
    insightBox(slide, 680, 382, 532, 210, lang === "tr" ? "Teslimat kapsamı" : "Delivery scope", lang === "tr" ? "Python planlama motoru • SQL veri katmanı • 31 sayfalık Excel modeli • 11 sayfalık Power BI PBIP • Türkçe ve İngilizce sunum • Vektörel yönetici raporu • Teknik dokümantasyon" : "Python planning engine • SQL data layer • 31-sheet Excel model • 11-page Power BI PBIP • English and Turkish decks • Vector executive report • Technical documentation", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/project_metadata.csv", "README.md"));
  }

  // 5 — Data landscape
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 5);
    const dataCards = lang === "tr"
      ? [
          ["5.325", "Gerçekleşen muhasebe satırı", "2023–Haz 2026"],
          ["1.558", "Bütçe satırı", "FY2026"],
          ["2.338", "Rolling forecast satırı", "18 ay"],
          ["9.352", "Senaryo satırı", "4 vaka"],
          ["5.000", "Monte Carlo koşusu", "Risk dağılımı"],
          ["12", "Maliyet merkezi", "Departman × İş Birimi"],
        ]
      : [
          ["5,325", "Actual accounting rows", "2023–Jun 2026"],
          ["1,558", "Budget rows", "FY2026"],
          ["2,338", "Rolling-forecast rows", "18 months"],
          ["9,352", "Scenario rows", "4 cases"],
          ["5,000", "Monte Carlo trials", "Risk distribution"],
          ["12", "Cost centers", "Department × Business Unit"],
        ];
    dataCards.forEach((item, index) => {
      const x = 48 + (index % 3) * 397;
      const y = 150 + Math.floor(index / 3) * 185;
      addPanel(slide, { left: x, top: y, width: 365, height: 155 }, { fill: C.white });
      addText(slide, item[0], { left: x + 22, top: y + 20, width: 150, height: 42 }, { fontSize: 28, bold: true, color: [C.blue, C.cyan, C.teal, C.violet, C.amber, C.green][index] });
      addText(slide, item[1], { left: x + 22, top: y + 70, width: 315, height: 32 }, { fontSize: 16, bold: true, color: C.navy });
      addText(slide, item[2], { left: x + 22, top: y + 112, width: 315, height: 20 }, { fontSize: 11, color: C.muted });
    });
    insightBox(slide, 48, 535, 1164, 92, lang === "tr" ? "Tasarım ilkesi" : "Design principle", lang === "tr" ? "Her tablo ay, sürüm, iş birimi, departman ve hesap boyutlarıyla izlenebilir; bu yapı hem finansal uzlaşmayı hem de zaman zekâsını destekler." : "Every table is traceable through month, version, business unit, department, and account dimensions—supporting both financial reconciliation and time intelligence.", C.blue, C.paleBlue);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/fact_actuals.csv", "Data/fact_budget.csv", "Data/fact_forecast.csv", "Data/fact_scenario.csv", "Data/monte_carlo_simulations.csv"));
  }

  // 6 — Architecture
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 6);
    addProcess(slide, lang === "tr"
      ? [
          ["Kaynak", "Sentetik ERP, CRM, İK ve capex verisi"],
          ["Dönüşüm", "Python üretim, kontrol ve tahmin motoru"],
          ["Depolama", "CSV analitik katmanı ve SQLite veri tabanı"],
          ["Modelleme", "Power Query, SQL, DAX ve semantik model"],
          ["Tüketim", "Excel, Power BI, PDF ve PowerPoint"],
        ]
      : [
          ["Source", "Synthetic ERP, CRM, HR, and capex data"],
          ["Transform", "Python generation, control, and forecasting engine"],
          ["Storage", "CSV analytics layer and SQLite database"],
          ["Model", "Power Query, SQL, DAX, and semantic model"],
          ["Consume", "Excel, Power BI, PDF, and PowerPoint"],
        ], 175, lang);
    insightBox(slide, 48, 380, 360, 205, lang === "tr" ? "Tekrarlanabilirlik" : "Reproducibility", lang === "tr" ? "Tek komut veri üretir, modelleri çalıştırır, raporlama tablolarını yeniler ve kontrolleri tekrarlar." : "One command regenerates data, runs the models, refreshes reporting tables, and repeats control checks.", C.blue, C.paleBlue);
    insightBox(slide, 432, 380, 360, 205, lang === "tr" ? "Denetlenebilirlik" : "Auditability", lang === "tr" ? "Sürüm, dönem durumu, kaynak sistem ve kontrol sonuçları veri hattında korunur." : "Version, period status, source system, and control results remain visible throughout the pipeline.", C.teal, C.paleGreen);
    insightBox(slide, 816, 380, 396, 205, lang === "tr" ? "Taşınabilirlik" : "Portability", lang === "tr" ? "PBIP veri modeli gömülü örnek veri kullanır; Excel ve SQLite bağımsız olarak incelenebilir." : "The PBIP semantic model embeds its sample data; Excel and SQLite remain independently reviewable.", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Python/src/fpa_system/run_pipeline.py", "SQL/schema.sql", "PowerBI/Integrated_FPA_PBIP", "Excel/Integrated_FP&A_Budgeting_Forecasting_Scenario_Planning_Model.xlsx"));
  }

  // 7 — Semantic model & controls
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 7);
    addPanel(slide, { left: 48, top: 156, width: 760, height: 430 }, { fill: C.white });
    addText(slide, lang === "tr" ? "Takvim Merkezli Yıldız Şema" : "Calendar-Centered Star Schema", { left: 74, top: 178, width: 380, height: 30 }, { fontSize: 21, bold: true, color: C.navy });
    addPanel(slide, { left: 286, top: 270, width: 270, height: 100 }, { fill: C.paleBlue, line: C.blue });
    addText(slide, "dim_calendar", { left: 315, top: 300, width: 210, height: 30 }, { fontSize: 22, bold: true, color: C.blue, align: "center" });
    const facts = [
      ["monthly_performance", 90, 225],
      ["department_performance", 90, 405],
      ["business_unit_performance", 580, 225],
      ["scenario_summary", 580, 405],
    ];
    facts.forEach((item, index) => {
      addPanel(slide, { left: item[1], top: item[2], width: 190, height: 84 }, { fill: index < 2 ? C.paleGreen : C.paleViolet, line: index < 2 ? C.teal : C.violet });
      addText(slide, item[0], { left: item[1] + 12, top: item[2] + 25, width: 166, height: 34 }, { fontSize: 13, bold: true, color: C.navy, align: "center" });
      addText(slide, "→", { left: item[1] < 300 ? 265 : 555, top: item[2] + 27, width: 25, height: 26 }, { fontSize: 20, bold: true, color: C.muted, align: "center" });
    });
    const controls = lang === "tr"
      ? ["P&L denklemi uzlaşması", "Nakit akışı sürekliliği", "Bilanço işletme sermayesi kontrolü", "Senaryo sıralaması", "Tahmin geri testleri", "Kaynak–rapor satır uzlaşması"]
      : ["P&L equation reconciliation", "Cash-flow continuity", "Working-capital balance control", "Scenario ordering", "Forecast backtests", "Source-to-report row reconciliation"];
    addText(slide, lang === "tr" ? "Kontrol Kütüphanesi" : "Control Library", { left: 850, top: 170, width: 320, height: 30 }, { fontSize: 21, bold: true, color: C.navy });
    bulletList(slide, controls, 850, 230, 350, { fontSize: 15, rowHeight: 55, accent: C.green });
    insightBox(slide, 850, 538, 362, 68, "17 / 17 PASS", lang === "tr" ? "Finansal ve veri kalite kontrolleri" : "Financial and data-quality controls", C.green, C.paleGreen);
    addFooter(slide, copy);
    addNotes(slide, sources("PowerBI/Integrated_FPA_Measures.dax", "Data/validation_report.json", "Python/tests/test_financial_controls.py"));
  }

  // 8 — Historical performance
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 8);
    addPanel(slide, { left: 48, top: 150, width: 800, height: 442 }, { fill: C.white });
    addLineChart(slide, { left: 72, top: 185, width: 750, height: 350 }, annualTrend.map((r) => String(r.Year)), [
      { name: lang === "tr" ? "Gelir (₺M)" : "Revenue (TRY M)", values: annualTrend.map((r) => r.RevenueTRY / 1e6), color: C.blue },
      { name: "EBITDA (₺M)", values: annualTrend.map((r) => r.EBITDATRY / 1e6), color: C.green },
    ], { axisFormat: "0" });
    metricCard(slide, 880, 150, 332, lang === "tr" ? "2023–2025 Gelir CAGR" : "2023–2025 Revenue CAGR", fmtPct(Math.pow(fy25Actual.RevenueTRY / annualTrend[0].RevenueTRY, 1 / 2) - 1), lang === "tr" ? "iki yıllık büyüme" : "two-year growth", C.blue);
    metricCard(slide, 880, 314, 332, lang === "tr" ? "FY2025 EBITDA Marjı" : "FY2025 EBITDA Margin", fmtPct(fy25Actual.EBITDAMarginPct), `${fmtM(fy25Actual.EBITDATRY, lang)} EBITDA`, C.green);
    insightBox(slide, 880, 478, 332, 114, lang === "tr" ? "Yorum" : "Interpretation", lang === "tr" ? "Gelir ölçeği büyüdü; ancak marj 2023 seviyesinin altında kaldı. FY2026 planı büyümeyi maliyet disipliniyle dengelemeyi hedefliyor." : "Scale increased, but margin remained below 2023. The FY2026 plan seeks to balance growth with tighter operating-cost discipline.", C.amber, C.paleAmber);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/annual_pnl.csv"));
  }

  // 9 — Revenue drivers
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 9);
    addPanel(slide, { left: 48, top: 150, width: 760, height: 442 }, { fill: C.white });
    addBarChart(slide, { left: 75, top: 185, width: 700, height: 350 }, buSummary.map((r) => local(r.name, lang)), [
      { name: lang === "tr" ? "FY2026 Gelir (₺M)" : "FY2026 Revenue (TRY M)", values: buSummary.map((r) => r.revenue / 1e6), color: C.blue },
    ], { horizontal: true, axisFormat: "0", valueFormat: "0.0", hasLegend: false });
    const leader = buSummary[0];
    insightBox(slide, 842, 150, 370, 136, lang === "tr" ? "En büyük katkı" : "Largest contributor", `${local(leader.name, lang)}\n${fmtM(leader.revenue, lang)} | ${fmtPct(leader.revenue / fy26Forecast.RevenueTRY)} ${lang === "tr" ? "pay" : "share"}`, C.blue, C.paleBlue);
    insightBox(slide, 842, 306, 370, 136, lang === "tr" ? "Büyüme mantığı" : "Growth logic", lang === "tr" ? "Trafik/lead, dönüşüm, işlem adedi, ortalama satış fiyatı ve churn/refund sürücüleri iş birimi düzeyinde modellenir." : "Traffic/leads, conversion, transactions, average selling price, and churn/refund are modeled at business-unit level.", C.teal, C.paleGreen);
    insightBox(slide, 842, 462, 370, 130, lang === "tr" ? "Yönetim aksiyonu" : "Management action", lang === "tr" ? "Dijital ve abonelik kanallarındaki momentumu korurken perakende plan açığını kanal bazında kapat." : "Protect momentum in digital and subscription channels while correcting the retail plan gap by channel.", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/business_unit_performance.csv", "Data/fact_operational_drivers.csv"));
  }

  // 10 — Cost structure
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 10);
    const costCategories = [local("COGS", lang), local("Operating Expense", lang), lang === "tr" ? "Amortisman" : "Depreciation", lang === "tr" ? "Faiz" : "Interest", lang === "tr" ? "Vergi" : "Tax"];
    const values = [fy26Forecast.COGSTRY, fy26Forecast.OperatingExpenseTRY, fy26Forecast.DepreciationTRY, fy26Forecast.InterestTRY, fy26Forecast.TaxTRY];
    addPanel(slide, { left: 48, top: 150, width: 760, height: 442 }, { fill: C.white });
    addBarChart(slide, { left: 72, top: 180, width: 710, height: 360 }, costCategories, [
      { name: lang === "tr" ? "FY2026 Tahmin (₺M)" : "FY2026 Forecast (TRY M)", values: values.map((v) => v / 1e6), color: C.amber },
    ], { horizontal: true, axisFormat: "0", valueFormat: "0.0", hasLegend: false });
    insightBox(slide, 842, 150, 370, 132, lang === "tr" ? "Brüt marj" : "Gross margin", fmtPct(fy26Forecast.GrossMarginPct), C.blue, C.paleBlue);
    insightBox(slide, 842, 302, 370, 132, lang === "tr" ? "Faaliyet gideri / gelir" : "Operating expense / revenue", fmtPct(fy26Forecast.OperatingExpenseTRY / fy26Forecast.RevenueTRY), C.amber, C.paleAmber);
    insightBox(slide, 842, 454, 370, 138, lang === "tr" ? "Kaldıraç fırsatı" : "Leverage opportunity", lang === "tr" ? "Bütçeye göre gider tasarrufu, gelir açığına rağmen EBITDA’nın plan üzerinde kalmasını sağlıyor." : "Operating savings keep EBITDA above plan despite the revenue shortfall.", C.green, C.paleGreen);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/annual_pnl.csv", "Data/department_performance.csv"));
  }

  // 11 — H1 actual vs budget
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 11);
    const selected = ["Revenue", "Gross Profit", "Operating Expense", "EBITDA", "Net Income"].map((metric) => h1Variance.find((r) => r.Metric === metric));
    addPanel(slide, { left: 48, top: 150, width: 810, height: 442 }, { fill: C.white });
    addBarChart(slide, { left: 76, top: 180, width: 750, height: 360 }, selected.map((r) => local(r.Metric, lang)), [
      { name: lang === "tr" ? "Gerçekleşen" : "Actual", values: selected.map((r) => r.CurrentValueTRY / 1e6), color: C.blue },
      { name: lang === "tr" ? "Bütçe" : "Budget", values: selected.map((r) => r.ComparatorValueTRY / 1e6), color: C.line },
    ], { axisFormat: "0", valueFormat: "0.0" });
    const revenueRow = selected[0];
    const ebitdaRow = selected[3];
    insightBox(slide, 890, 150, 322, 126, lang === "tr" ? "Gelir sapması" : "Revenue variance", `${fmtM(revenueRow.VarianceTRY, lang)} | ${fmtPct(revenueRow.VariancePct)}`, C.red, C.paleRed);
    insightBox(slide, 890, 296, 322, 126, lang === "tr" ? "EBITDA sapması" : "EBITDA variance", `+${fmtM(ebitdaRow.VarianceTRY, lang)} | +${fmtPct(ebitdaRow.VariancePct)}`, C.green, C.paleGreen);
    insightBox(slide, 890, 442, 322, 150, lang === "tr" ? "Okuma" : "Read-through", lang === "tr" ? "H1 gelir açığına karşı ₺18,5M faaliyet gideri tasarrufu, EBITDA ve net kârı plan üzerinde tuttu." : "TRY 18.5M of operating-expense savings offset the H1 revenue gap and kept EBITDA and net income above plan.", C.blue, C.paleBlue);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/variance_analysis.csv"));
  }

  // 12 — FY2026 forecast vs budget
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 12);
    const rows = ["Revenue", "Gross Profit", "Operating Expense", "EBITDA", "Net Income"].map((metric) => fy26Variance.find((r) => r.Metric === metric));
    simpleTable(slide, 48, 160, [235, 175, 175, 175, 165], [
      lang === "tr" ? "Gösterge" : "Metric",
      lang === "tr" ? "Tahmin" : "Forecast",
      lang === "tr" ? "Bütçe" : "Budget",
      lang === "tr" ? "Sapma" : "Variance",
      lang === "tr" ? "Durum" : "Status",
    ], rows.map((r) => [
      local(r.Metric, lang),
      fmtM(r.CurrentValueTRY, lang),
      fmtM(r.ComparatorValueTRY, lang),
      `${r.VarianceTRY >= 0 ? "+" : ""}${fmtM(r.VarianceTRY, lang)} (${fmtPct(r.VariancePct)})`,
      r.FavorableFlag ? (lang === "tr" ? "Olumlu" : "Favorable") : (lang === "tr" ? "Olumsuz" : "Unfavorable"),
    ]), { rowHeight: 48, fontSize: 12 });
    insightBox(slide, 1010, 160, 202, 288, lang === "tr" ? "Ana sonuç" : "Key outcome", lang === "tr" ? `Gelir bütçenin ${fmtM(Math.abs(fy26Forecast.RevenueTRY - fy26Budget.RevenueTRY), lang)} altında; EBITDA ise ${fmtM(fy26Forecast.EBITDATRY - fy26Budget.EBITDATRY, lang)} üzerinde.` : `Revenue is ${fmtM(Math.abs(fy26Forecast.RevenueTRY - fy26Budget.RevenueTRY), lang)} below budget, while EBITDA is ${fmtM(fy26Forecast.EBITDATRY - fy26Budget.EBITDATRY, lang)} above plan.`, C.blue, C.paleBlue);
    insightBox(slide, 48, 500, 1164, 102, lang === "tr" ? "Planlama kararı" : "Planning decision", lang === "tr" ? "Gelir açığı için ticari aksiyon planı oluştur; bütçe altındaki kontrollü opex seviyesini kör kesinti yerine verimlilik göstergeleriyle koru." : "Build a commercial action plan for the revenue gap and preserve the below-budget opex position through productivity metrics—not indiscriminate cuts.", C.teal, C.paleGreen);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/variance_analysis.csv", "Data/forecast_bridge.csv"));
  }

  // 13 — Rolling forecast
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 13);
    const months = y2026ForecastMonths.map((r) => String(r.MonthLabel).split(" ")[0]);
    addPanel(slide, { left: 48, top: 150, width: 830, height: 442 }, { fill: C.white });
    addLineChart(slide, { left: 76, top: 180, width: 770, height: 360 }, months, [
      { name: lang === "tr" ? "Rolling Forecast (₺M)" : "Rolling Forecast (TRY M)", values: y2026ForecastMonths.map((r) => r.RevenueTRY / 1e6), color: C.blue },
      { name: lang === "tr" ? "Bütçe (₺M)" : "Budget (TRY M)", values: y2026BudgetMonths.map((r) => r.RevenueTRY / 1e6), color: C.amber },
    ], { axisFormat: "0" });
    insightBox(slide, 910, 150, 302, 124, lang === "tr" ? "Kapanan dönem" : "Closed period", lang === "tr" ? "Ocak–Haziran gerçekleşenleri forecast görünümüne sabitlenir." : "January–June actuals are locked into the forecast view.", C.teal, C.paleGreen);
    insightBox(slide, 910, 294, 302, 124, lang === "tr" ? "İleri dönem" : "Forward period", lang === "tr" ? "Temmuz 2026–Haziran 2027 iş sürücülerine göre yenilenir." : "July 2026–June 2027 refreshes from operating drivers.", C.blue, C.paleBlue);
    insightBox(slide, 910, 438, 302, 154, lang === "tr" ? "Yönetişim" : "Governance", lang === "tr" ? "Aylık kapanış → sapma incelemesi → sürücü güncellemesi → model çalıştırma → yönetim onayı." : "Monthly close → variance review → driver refresh → model run → management approval.", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/monthly_kpi_dashboard.csv", "Data/fact_forecast.csv"));
  }

  // 14 — Forecast governance
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 14);
    simpleTable(slide, 48, 160, [280, 320, 170, 170], [
      lang === "tr" ? "İş Birimi" : "Business Unit",
      lang === "tr" ? "Şampiyon Model" : "Champion Model",
      "WAPE",
      lang === "tr" ? "Doğruluk" : "Accuracy",
    ], champions.map((r) => [
      local(r.BusinessUnit, lang),
      r.Model,
      fmtPct(r.WAPE),
      fmtPct(1 - r.WAPE),
    ]), { rowHeight: 54, fontSize: 12 });
    insightBox(slide, 1010, 160, 202, 270, lang === "tr" ? "Seçim kuralı" : "Selection rule", lang === "tr" ? "MAE, RMSE, WAPE ve bias birlikte değerlendirilir; en düşük birleşik puan iş birimi şampiyonu olur." : "MAE, RMSE, WAPE, and bias are evaluated together; the lowest composite score becomes the business-unit champion.", C.blue, C.paleBlue);
    const averageWape = champions.reduce((sum, r) => sum + r.WAPE, 0) / champions.length;
    metricCard(slide, 48, 470, 350, lang === "tr" ? "Ortalama Şampiyon WAPE" : "Average Champion WAPE", fmtPct(averageWape), `${champions.length} ${lang === "tr" ? "iş birimi" : "business units"}`, C.green);
    insightBox(slide, 430, 470, 782, 144, lang === "tr" ? "Model riski kontrolü" : "Model-risk control", lang === "tr" ? "Geri test sonuçları, model kartları, varsayım kayıtları ve aylık hata izleme sayesinde tek bir algoritmaya kör bağımlılık önlenir." : "Backtests, model cards, assumption logs, and monthly error monitoring prevent blind dependence on a single algorithm.", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/forecast_model_comparison.csv", "Data/forecast_backtest.csv", "Docs/forecast-model-governance.md"));
  }

  // 15 — Cash & liquidity
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 15);
    const months = y2026ForecastMonths.map((r) => String(r.MonthLabel).split(" ")[0]);
    const fy26EndingForecast = y2026ForecastMonths.at(-1).EndingCashTRY;
    const fy26EndingBudget = y2026BudgetMonths.at(-1).EndingCashTRY;
    const fy26MinimumForecast = Math.min(...y2026ForecastMonths.map((r) => r.EndingCashTRY));
    addPanel(slide, { left: 48, top: 150, width: 760, height: 442 }, { fill: C.white });
    addLineChart(slide, { left: 74, top: 180, width: 710, height: 360 }, months, [
      { name: lang === "tr" ? "Tahmin Kapanış Nakdi (₺M)" : "Forecast Ending Cash (TRY M)", values: y2026ForecastMonths.map((r) => r.EndingCashTRY / 1e6), color: C.blue },
      { name: lang === "tr" ? "Bütçe Kapanış Nakdi (₺M)" : "Budget Ending Cash (TRY M)", values: y2026BudgetMonths.map((r) => r.EndingCashTRY / 1e6), color: C.amber },
    ], { axisFormat: "0" });
    metricCard(slide, 842, 150, 370, lang === "tr" ? "FY2026 Tahmini Kapanış Nakdi" : "FY2026 Forecast Ending Cash", fmtM(fy26EndingForecast, lang), `${fmtM(fy26EndingForecast - fy26EndingBudget, lang)} ${lang === "tr" ? "bütçe sapması" : "vs budget"}`, C.blue);
    metricCard(slide, 842, 314, 370, lang === "tr" ? "FY2026 Minimum Nakit" : "FY2026 Minimum Cash", fmtM(fy26MinimumForecast, lang), lang === "tr" ? "pozitif likidite tamponu" : "positive liquidity buffer", C.green);
    insightBox(slide, 842, 478, 370, 114, lang === "tr" ? "Karar" : "Decision", lang === "tr" ? "Büyüme yatırımlarını nakit tabanı ve senaryo eşikleriyle birlikte onayla." : "Approve growth investments against the cash floor and scenario thresholds.", C.violet, C.paleViolet);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/cash_flow_summary.csv", "Data/fact_cash_flow.csv"));
  }

  // 16 — Working capital
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 16);
    addPanel(slide, { left: 48, top: 150, width: 760, height: 442 }, { fill: C.white });
    addBarChart(slide, { left: 72, top: 180, width: 710, height: 360 }, scenarios.map((r) => local(r.Scenario, lang)), [
      { name: lang === "tr" ? "Nakit Dönüşüm Döngüsü (gün)" : "Cash Conversion Cycle (days)", values: scenarios.map((r) => r.CashConversionCycleDays), color: C.amber },
    ], { axisFormat: "0", valueFormat: "0.0", hasLegend: false });
    metricCard(slide, 842, 150, 370, lang === "tr" ? "Baz Senaryo CCC" : "Base-Case CCC", `${baseScenario.CashConversionCycleDays.toFixed(1)} ${lang === "tr" ? "gün" : "days"}`, lang === "tr" ? "DSO + DIO − DPO" : "DSO + DIO − DPO", C.amber);
    insightBox(slide, 842, 314, 370, 132, lang === "tr" ? "Değer kaldıraçları" : "Value levers", lang === "tr" ? "Tahsilat hızını artır • stok gününü azalt • tedarikçi vadelerini kontrollü optimize et" : "Accelerate collections • reduce inventory days • optimize supplier terms responsibly", C.teal, C.paleGreen);
    insightBox(slide, 842, 466, 370, 126, lang === "tr" ? "Stres etkisi" : "Stress impact", lang === "tr" ? `CCC ${scenarios.find((r) => r.Scenario === "Stress").CashConversionCycleDays.toFixed(1)} güne çıkarken kapanış nakdi ${fmtM(scenarios.find((r) => r.Scenario === "Stress").EndingCashTRY, lang)} seviyesine iner.` : `CCC extends to ${scenarios.find((r) => r.Scenario === "Stress").CashConversionCycleDays.toFixed(1)} days while ending cash falls to ${fmtM(scenarios.find((r) => r.Scenario === "Stress").EndingCashTRY, lang)}.`, C.red, C.paleRed);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/fact_working_capital.csv", "Data/scenario_summary.csv"));
  }

  // 17 — Workforce & capital
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 17);
    const lastMonth = [...new Set(hcForecast.map((r) => r.Month))].sort().slice(-1)[0];
    const closingFte = hcForecast.filter((r) => r.Month === lastMonth).reduce((s, r) => s + r.FTE, 0);
    const payroll = hcForecast.reduce((s, r) => s + r.PayrollCostTRY + r.BenefitsCostTRY, 0);
    const capexSpend = capexForecast.reduce((s, r) => s + r.CapexSpendTRY, 0);
    metricCard(slide, 48, 155, 360, lang === "tr" ? "Kapanış FTE" : "Closing FTE", String(closingFte), lang === "tr" ? "Aralık 2026 tahmini" : "December 2026 forecast", C.blue);
    metricCard(slide, 432, 155, 360, lang === "tr" ? "Bordro + Yan Haklar" : "Payroll + Benefits", fmtM(payroll, lang), lang === "tr" ? "FY2026 tahmini" : "FY2026 forecast", C.violet);
    metricCard(slide, 816, 155, 396, "CAPEX", fmtM(capexSpend, lang), lang === "tr" ? "FY2026 yatırım harcaması" : "FY2026 investment spend", C.teal);
    const topDept = deptSummary.slice(0, 5);
    addPanel(slide, { left: 48, top: 340, width: 720, height: 274 }, { fill: C.white });
    addBarChart(slide, { left: 72, top: 365, width: 670, height: 220 }, topDept.map((r) => r.name), [
      { name: lang === "tr" ? "Faaliyet Gideri (₺M)" : "Operating Expense (TRY M)", values: topDept.map((r) => r.opex / 1e6), color: C.violet },
    ], { horizontal: true, axisFormat: "0", valueFormat: "0.0", hasLegend: false });
    insightBox(slide, 800, 340, 412, 274, lang === "tr" ? "Yönetişim kuralı" : "Governance rule", lang === "tr" ? "Yeni işe alım ve capex talepleri; gelir kapasitesi, verimlilik, nakit etkisi, stratejik uyum ve senaryo dayanıklılığı birlikte değerlendirilerek onaylanır." : "Hiring and capex requests are approved through a joint assessment of revenue capacity, productivity, cash impact, strategic alignment, and scenario resilience.", C.blue, C.paleBlue);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/headcount_summary.csv", "Data/capex_summary.csv", "Data/department_performance.csv"));
  }

  // 18 — Scenario planning
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 18);
    addPanel(slide, { left: 48, top: 150, width: 800, height: 442 }, { fill: C.white });
    addBarChart(slide, { left: 72, top: 180, width: 750, height: 360 }, scenarios.map((r) => local(r.Scenario, lang)), [
      { name: lang === "tr" ? "EBITDA (₺M)" : "EBITDA (TRY M)", values: scenarios.map((r) => r.EBITDATRY / 1e6), color: C.green },
      { name: lang === "tr" ? "Kapanış Nakdi (₺M)" : "Ending Cash (TRY M)", values: scenarios.map((r) => r.EndingCashTRY / 1e6), color: C.blue },
    ], { axisFormat: "0", valueFormat: "0.0" });
    const stress = scenarios.find((r) => r.Scenario === "Stress");
    metricCard(slide, 880, 150, 332, lang === "tr" ? "Baz EBITDA" : "Base EBITDA", fmtM(baseScenario.EBITDATRY, lang), `${fmtPct(baseScenario.EBITDAMarginPct)} ${lang === "tr" ? "marj" : "margin"}`, C.green);
    metricCard(slide, 880, 314, 332, lang === "tr" ? "Stres Kapanış Nakdi" : "Stress Ending Cash", fmtM(stress.EndingCashTRY, lang), `${stress.CashConversionCycleDays.toFixed(1)} ${lang === "tr" ? "gün CCC" : "days CCC"}`, C.red);
    insightBox(slide, 880, 478, 332, 114, lang === "tr" ? "Tetikleyici" : "Trigger", lang === "tr" ? "Gelir, brüt marj veya CCC eşikleri bozulduğunda maliyet, capex ve tahsilat aksiyonları devreye girer." : "Cost, capex, and collection actions activate when revenue, gross-margin, or CCC thresholds deteriorate.", C.amber, C.paleAmber);
    addFooter(slide, copy);
    addNotes(slide, sources("Data/scenario_summary.csv", "Data/scenario_monthly_pnl.csv", "Data/scenario_cash_flow.csv"));
  }

  // 19 — Risk & roadmap
  {
    const slide = presentation.slides.add();
    addHeader(slide, copy, 19);
    metricCard(slide, 48, 150, 260, lang === "tr" ? "Gelir P10" : "Revenue P10", fmtB(riskMap["Revenue P10"], lang), lang === "tr" ? "aşağı kuyruk" : "lower tail", C.red);
    metricCard(slide, 328, 150, 260, lang === "tr" ? "Gelir P50" : "Revenue P50", fmtB(riskMap["Revenue P50"], lang), lang === "tr" ? "medyan" : "median", C.blue);
    metricCard(slide, 608, 150, 260, lang === "tr" ? "Gelir P90" : "Revenue P90", fmtB(riskMap["Revenue P90"], lang), lang === "tr" ? "yukarı kuyruk" : "upper tail", C.green);
    metricCard(slide, 888, 150, 324, lang === "tr" ? "EBITDA Bütçe Altı Olasılığı" : "Probability EBITDA Below Budget", fmtPct(riskMap["Probability EBITDA Below Budget"]), "5,000 Monte Carlo", C.amber);
    const roadmap = lang === "tr"
      ? [
          ["0–30 Gün", "Veri sahipliğini ve aylık kapanış takvimini resmileştir."],
          ["31–60 Gün", "Sürücü güncelleme, forecast geri test ve sapma oturumlarını işlet."],
          ["61–90 Gün", "Senaryo tetikleyicileri ile otomatik yönetim aksiyonları oluştur."],
        ]
      : [
          ["0–30 Days", "Formalize data ownership and the monthly close calendar."],
          ["31–60 Days", "Operate driver refresh, forecast backtest, and variance-review sessions."],
          ["61–90 Days", "Create automated management actions linked to scenario triggers."],
        ];
    roadmap.forEach((item, index) => {
      const x = 48 + index * 394;
      addPanel(slide, { left: x, top: 350, width: 366, height: 230 }, { fill: C.white, line: [C.blue, C.teal, C.violet][index] });
      addText(slide, item[0], { left: x + 22, top: 374, width: 320, height: 26 }, { fontSize: 14, bold: true, color: [C.blue, C.teal, C.violet][index] });
      addText(slide, item[1], { left: x + 22, top: 430, width: 320, height: 110 }, { fontSize: 17, bold: true, color: C.navy });
    });
    addFooter(slide, copy);
    addNotes(slide, sources("Data/risk_summary.csv", "Data/monte_carlo_simulations.csv", "Data/management_insights.csv"));
  }

  // 20 — Close
  {
    const slide = presentation.slides.add();
    slide.background.fill = C.navy;
    addText(slide, copy.thankYou, { left: 56, top: 44, width: 300, height: 25 }, { fontSize: 12, bold: true, color: "#8FD8FF" });
    addText(slide, copy.close, { left: 56, top: 170, width: 920, height: 150 }, { fontSize: 50, bold: true, color: C.white });
    addText(slide, copy.closeBody, { left: 56, top: 365, width: 860, height: 100 }, { fontSize: 19, color: "#D9E6F2" });
    addText(slide, "Murat Miraç Gedik", { left: 56, top: 545, width: 360, height: 34 }, { fontSize: 18, bold: true, color: C.white });
    addText(slide, "FP&A • Forecasting • SQL • Python • Power BI • Excel", { left: 56, top: 590, width: 650, height: 26 }, { fontSize: 14, color: "#8FD8FF" });
    addText(slide, copy.notice, { left: 56, top: 660, width: 780, height: 18 }, { fontSize: 10, color: "#B8C6D8" });
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: 975, top: 195, width: 220, height: 220 },
      fill: C.blue,
      line: { style: "solid", fill: C.blue, width: 0 },
    });
    addText(slide, "PLAN\n→\nDECIDE", { left: 1015, top: 245, width: 140, height: 120 }, { fontSize: 25, bold: true, color: C.white, align: "center", vertical: "middle" });
    addNotes(slide, sources("README.md"));
  }

  return presentation;
}

async function writeBlob(filename, blob) {
  await fs.writeFile(filename, new Uint8Array(await blob.arrayBuffer()));
}

async function exportDeck(lang) {
  const presentation = createDeck(lang);
  const previewDir = path.join(outputDir, `previews-${lang}`);
  await fs.mkdir(previewDir, { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1.5 });
    await writeBlob(path.join(previewDir, `${stem}.png`), png);
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(previewDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }
  const montage = await presentation.export({ format: "webp", montage: true, scale: 0.7 });
  await writeBlob(path.join(previewDir, "deck-montage.webp"), montage);
  const inspection = await presentation.inspect({
    kind: "slide,textbox,shape,chart,notes,layout",
    maxChars: 20000,
    options: { maxResults: 600 },
  });
  await fs.writeFile(path.join(previewDir, "deck-inspection.ndjson"), inspection.ndjson, "utf8");
  const pptx = await PresentationFile.exportPptx(presentation);
  const filename = lang === "tr"
    ? "Entegre_FPA_Butceleme_Tahminleme_Senaryo_Planlama_Profesyonel_Sunum_TR.pptx"
    : "Integrated_FPA_Budgeting_Forecasting_Scenario_Planning_Professional_Deck_EN.pptx";
  const outputPath = path.join(outputDir, filename);
  await pptx.save(outputPath);
  return outputPath;
}

await fs.mkdir(outputDir, { recursive: true });
const english = await exportDeck("en");
const turkish = await exportDeck("tr");
console.log(JSON.stringify({ english, turkish }, null, 2));
