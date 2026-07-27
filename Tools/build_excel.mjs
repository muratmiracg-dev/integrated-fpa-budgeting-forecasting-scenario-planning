import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(process.argv[2] || ".");
const dataDir = path.join(projectRoot, "Data");
const outputDir = path.join(projectRoot, "Excel");
const previewDir = path.join(projectRoot, "Images", "excel-previews");

const C = {
  navy: "#081525",
  navy2: "#10233D",
  blue: "#2F6BFF",
  cyan: "#39C6F4",
  lightBlue: "#EAF5FF",
  light: "#F4F7FB",
  line: "#D8E0EA",
  text: "#172033",
  muted: "#667085",
  white: "#FFFFFF",
  green: "#0F9D7A",
  paleGreen: "#E8F7F1",
  amber: "#F6B73C",
  paleAmber: "#FFF4D6",
  red: "#D9534F",
  paleRed: "#FDECEC",
  input: "#FFF2CC",
  inputFont: "#0000FF",
  linkedFont: "#008000",
};

const FMT_TRY = "0.0";
const FMT_TRY_FULL = "0.0";
const FMT_PCT = "0.0%;[Red](0.0%);-";
const FMT_NUM = "#,##0;[Red](#,##0);-";
const FMT_DAYS = '0.0 "days";[Red](0.0 "days");-';

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field !== "" || row.length) {
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
  const rows = parseCsv(await fs.readFile(path.join(dataDir, filename), "utf8"));
  return {
    headers: rows[0],
    rows: rows.slice(1).map((row) => row.map(coerce)),
  };
}

function colName(index) {
  let n = index + 1;
  let result = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    result = String.fromCharCode(65 + r) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

function rangeFor(startRow, startCol, rows, cols) {
  return `${colName(startCol)}${startRow}:${colName(startCol + cols - 1)}${startRow + rows - 1}`;
}

function titleBand(sheet, title, subtitle, lastCol = "N") {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}2`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}2`).format = {
    fill: C.navy,
    font: { color: C.white, bold: true, size: 20 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A3:${lastCol}3`).merge();
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange(`A3:${lastCol}3`).format = {
    fill: C.navy2,
    font: { color: "#D7E3F7", italic: true, size: 10 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}3`).format.rowHeight = 25;
}

function section(sheet, range, label) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[label]];
  sheet.getRange(range).format = {
    fill: C.navy2,
    font: { color: C.white, bold: true, size: 10 },
    verticalAlignment: "center",
  };
}

function card(sheet, labelRange, valueRange, label, formula, numberFormat, accent = C.blue) {
  sheet.getRange(labelRange).merge();
  sheet.getRange(valueRange).merge();
  sheet.getRange(labelRange.split(":")[0]).values = [[label]];
  sheet.getRange(valueRange.split(":")[0]).formulas = [[formula]];
  sheet.getRange(labelRange).format = {
    fill: C.light,
    font: { color: C.muted, bold: true, size: 9 },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.line },
  };
  sheet.getRange(valueRange).format = {
    fill: C.white,
    font: { color: accent, bold: true, size: 19 },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.line },
    numberFormat,
  };
}

function styleDataTable(sheet, range, headerRange, options = {}) {
  sheet.getRange(range).format = {
    font: { color: C.text, size: options.fontSize || 9 },
    borders: { preset: "all", style: "thin", color: C.line },
    verticalAlignment: "center",
  };
  sheet.getRange(headerRange).format = {
    fill: C.navy2,
    font: { color: C.white, bold: true, size: options.headerSize || 9 },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: C.navy2 },
  };
}

function setWidths(sheet, widths) {
  for (const [address, width] of Object.entries(widths)) {
    sheet.getRange(address).format.columnWidth = width;
  }
}

function addRawSheet(workbook, name, title, subtitle, dataset, lastCol = null) {
  const sheet = workbook.worksheets.add(name);
  const finalCol = lastCol || colName(dataset.headers.length - 1);
  titleBand(sheet, title, subtitle, finalCol);
  const address = rangeFor(5, 0, dataset.rows.length + 1, dataset.headers.length);
  sheet.getRange(address).values = [dataset.headers, ...dataset.rows];
  styleDataTable(sheet, address, rangeFor(5, 0, 1, dataset.headers.length), {
    fontSize: 8,
    headerSize: 8,
  });
  sheet.freezePanes.freezeRows(5);
  sheet.getRange(address).format.rowHeight = 17;
  return sheet;
}

const [
  monthlyPnl,
  variance,
  scenarioSummary,
  workingCapital,
  cashFlow,
  headcount,
  capex,
  department,
  businessUnit,
  modelComparison,
  riskSummary,
  operationalDrivers,
  budgetSubmissions,
  managementInsights,
] = await Promise.all([
  loadCsv("monthly_pnl.csv"),
  loadCsv("variance_analysis.csv"),
  loadCsv("scenario_summary.csv"),
  loadCsv("fact_working_capital.csv"),
  loadCsv("fact_cash_flow.csv"),
  loadCsv("headcount_summary.csv"),
  loadCsv("capex_summary.csv"),
  loadCsv("department_performance.csv"),
  loadCsv("business_unit_performance.csv"),
  loadCsv("forecast_model_comparison.csv"),
  loadCsv("risk_summary.csv"),
  loadCsv("fact_operational_drivers.csv"),
  loadCsv("budget_submissions.csv"),
  loadCsv("management_insights.csv"),
]);

function scaleCurrencyColumns(dataset, extraHeaders = []) {
  const currencyIndexes = dataset.headers
    .map((header, index) => ({ header, index }))
    .filter(({ header }) => header.endsWith("TRY") || extraHeaders.includes(header))
    .map(({ index }) => index);
  for (const row of dataset.rows) {
    for (const index of currencyIndexes) {
      if (typeof row[index] === "number") row[index] /= 1_000_000;
    }
  }
}

for (const dataset of [
  monthlyPnl,
  variance,
  scenarioSummary,
  workingCapital,
  cashFlow,
  headcount,
  capex,
  department,
  businessUnit,
]) {
  scaleCurrencyColumns(dataset);
}
scaleCurrencyColumns(modelComparison, ["MAE", "RMSE"]);
const riskValueIndex = riskSummary.headers.indexOf("Value");
const riskUnitIndex = riskSummary.headers.indexOf("Unit");
for (const row of riskSummary.rows) {
  if (row[riskUnitIndex] === "TRY" && typeof row[riskValueIndex] === "number") {
    row[riskValueIndex] /= 1_000_000;
  }
}

const workbook = Workbook.create();
const cover = workbook.worksheets.add("Cover");
const dashboard = workbook.worksheets.add("Executive Dashboard");
const scenarioControl = workbook.worksheets.add("Scenario Control");
const incomeStatement = workbook.worksheets.add("Income Statement");
const budgetVsActual = workbook.worksheets.add("Budget vs Actual");
const rollingForecast = workbook.worksheets.add("Rolling Forecast");
const revenueDrivers = workbook.worksheets.add("Revenue Drivers");
const opexPlanning = workbook.worksheets.add("Opex Planning");
const cashFlowSheet = workbook.worksheets.add("Cash Flow");
const workingCapitalSheet = workbook.worksheets.add("Working Capital");
const headcountPlan = workbook.worksheets.add("Headcount Plan");
const capexPlan = workbook.worksheets.add("Capex Plan");
const departmentBudget = workbook.worksheets.add("Department Budget");
const businessUnitSheet = workbook.worksheets.add("Business Unit");
const forecastAccuracy = workbook.worksheets.add("Forecast Accuracy");
const riskAnalysis = workbook.worksheets.add("Risk Analysis");
const assumptions = workbook.worksheets.add("Assumptions");
const checks = workbook.worksheets.add("Checks");
const dictionary = workbook.worksheets.add("Data Dictionary");
const sources = workbook.worksheets.add("Sources");
const dashboardData = workbook.worksheets.add("Dashboard Data");

const pnlData = addRawSheet(
  workbook,
  "P&L Data",
  "P&L Data",
  "Formula source | actual, budget and Q2 rolling forecast",
  monthlyPnl,
);
const scenarioData = addRawSheet(
  workbook,
  "Scenario Data",
  "Scenario Data",
  "Base, Upside, Downside and Stress decision outputs",
  scenarioSummary,
);
const cashData = addRawSheet(
  workbook,
  "Cash Data",
  "Cash Data",
  "Cash roll-forward source by planning version",
  cashFlow,
);
const wcData = addRawSheet(
  workbook,
  "WC Data",
  "Working Capital Data",
  "AR, inventory, AP and cash conversion cycle",
  workingCapital,
);
const departmentData = addRawSheet(
  workbook,
  "Department Data",
  "Department Data",
  "Monthly P&L by department and version",
  department,
);
const businessUnitData = addRawSheet(
  workbook,
  "BU Data",
  "Business Unit Data",
  "Monthly P&L by business unit and version",
  businessUnit,
);
const headcountData = addRawSheet(
  workbook,
  "Headcount Data",
  "Headcount Data",
  "Monthly FTE, hires, exits and payroll",
  headcount,
);
const capexData = addRawSheet(
  workbook,
  "Capex Data",
  "Capex Data",
  "Monthly capex, depreciation and remaining NBV",
  capex,
);
const modelData = addRawSheet(
  workbook,
  "Model Data",
  "Forecast Model Data",
  "Backtest metrics and champion model flags",
  modelComparison,
);
const varianceData = addRawSheet(
  workbook,
  "Variance Data",
  "Variance Data",
  "H1 actual, FY forecast and prior-year comparison outputs",
  variance,
);

// Cover
cover.showGridLines = false;
cover.getRange("A1:N4").merge();
cover.getRange("A1").values = [[
  "Integrated FP&A Budgeting, Forecasting\n& Scenario Planning System",
]];
cover.getRange("A1:N4").format = {
  fill: C.navy,
  font: { color: C.white, bold: true, size: 26 },
  verticalAlignment: "center",
  wrapText: true,
};
cover.getRange("A5:N5").merge();
cover.getRange("A5").values = [["Professional Excel FP&A Model & Management Reporting Pack"]];
cover.getRange("A5:N5").format = {
  fill: C.blue,
  font: { color: C.white, bold: true, size: 12 },
  verticalAlignment: "center",
};
cover.getRange("A7:H13").merge();
cover.getRange("A7").values = [[
  "Purpose\nUnify historical actuals, the FY2026 budget, a Q2 rolling forecast, operational drivers and scenario analytics into one auditable management-planning model.",
]];
cover.getRange("A7:H13").format = {
  fill: C.light,
  font: { color: C.text, size: 14 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.line },
};
cover.getRange("J7:N13").merge();
cover.getRange("J7").values = [[
  "Portfolio Scope\n• 42 months of actuals\n• FY2026 budget\n• 18-month rolling forecast\n• P&L, cash and working capital\n• Headcount and capex schedules\n• 4 scenarios + 5,000 Monte Carlo runs\n• TRY reporting currency",
]];
cover.getRange("J7:N13").format = {
  fill: C.lightBlue,
  font: { color: C.navy, size: 12, bold: true },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.cyan },
};
cover.getRange("A15:N18").merge();
cover.getRange("A15").values = [[
  "Prepared by Murat Miraç Gedik  |  Synthetic portfolio data  |  As of 30 June 2026\nUse blue-font cells for editable inputs. Green-font cells link to other worksheets. Black-font cells are formulas.",
]];
cover.getRange("A15:N18").format = {
  fill: C.white,
  font: { color: C.muted, italic: true, size: 10 },
  verticalAlignment: "center",
  wrapText: true,
};
setWidths(cover, { "A:N": 12 });

// Assumptions
titleBand(
  assumptions,
  "Assumptions & Planning Guardrails",
  "Editable scenario drivers | blue font and yellow fill",
  "J",
);
assumptions.getRange("A5:G9").values = [
  ["Scenario", "Revenue Multiplier", "COGS Ratio Multiplier", "Opex Multiplier", "DSO Delta", "DIO Delta", "DPO Delta"],
  ["Base", 1.0, 1.0, 1.0, 0, 0, 0],
  ["Upside", 1.09, 0.985, 1.025, -3, -4, 2],
  ["Downside", 0.9, 1.025, 0.965, 5, 7, -2],
  ["Stress", 0.8, 1.065, 0.925, 12, 15, -5],
];
styleDataTable(assumptions, "A5:G9", "A5:G5");
assumptions.getRange("B6:G9").format = {
  fill: C.input,
  font: { color: C.inputFont },
};
assumptions.getRange("B6:D9").format.numberFormat = FMT_PCT;
assumptions.getRange("E6:G9").format.numberFormat = '0.0 "days"';
assumptions.getRange("A12:D20").values = [
  ["Planning Convention", "Value", "Owner", "Notes"],
  ["Company", "Asteria Consumer Group", "FP&A", "Synthetic portfolio entity"],
  ["As-of date", "2026-06-30", "Controllership", "June close complete"],
  ["Reporting currency", "TRY", "Finance", "Nominal values"],
  ["Actual period", "Jan 2023 - Jun 2026", "Accounting", "42 monthly closes"],
  ["Budget version", "FY2026 Budget v1", "FP&A", "Approved baseline"],
  ["Forecast version", "Q2 2026 Rolling Forecast", "FP&A", "Actuals through June"],
  ["Forecast horizon", "Jul 2026 - Jun 2027", "FP&A", "12 open months"],
  ["Tax rate", 0.25, "Tax", "Applied to positive EBT"],
];
styleDataTable(assumptions, "A12:D20", "A12:D12");
assumptions.getRange("B20").format = {
  fill: C.input,
  font: { color: C.inputFont },
  numberFormat: FMT_PCT,
};
assumptions.getRange("I5:J9").values = [
  ["Color", "Meaning"],
  ["Blue font", "Editable input"],
  ["Green font", "Internal worksheet link"],
  ["Black font", "Formula / calculation"],
  ["Red font", "External workbook link"],
];
styleDataTable(assumptions, "I5:J9", "I5:J5");
setWidths(assumptions, {
  "A:A": 28,
  "B:D": 23,
  "E:G": 15,
  "I:I": 18,
  "J:J": 28,
});

// Scenario Control
titleBand(
  scenarioControl,
  "Scenario Control Center",
  "Select a case and review its P&L, liquidity and working-capital implications",
  "N",
);
section(scenarioControl, "A5:D5", "Scenario Selector");
scenarioControl.getRange("A6:B13").values = [
  ["Selected Scenario", "Base"],
  ["Revenue Multiplier", null],
  ["COGS Ratio Multiplier", null],
  ["Opex Multiplier", null],
  ["DSO Delta", null],
  ["DIO Delta", null],
  ["DPO Delta", null],
  ["Planning Status", null],
];
scenarioControl.getRange("B6").dataValidation = {
  rule: { type: "list", values: ["Base", "Upside", "Downside", "Stress"] },
};
for (let row = 7; row <= 12; row += 1) {
  const assumptionCol = colName(row - 6);
  scenarioControl.getRange(`B${row}`).formulas = [[
    `=SUMIF(Assumptions!$A$6:$A$9,$B$6,Assumptions!$${assumptionCol}$6:$${assumptionCol}$9)`,
  ]];
}
scenarioControl.getRange("B13").formulas = [[
  '=IF(B6="Stress","CONTINGENCY MODE",IF(B6="Downside","ACTION PLAN","OPERATING PLAN"))',
]];
styleDataTable(scenarioControl, "A6:B13", "A6:B6");
scenarioControl.getRange("B6").format = {
  fill: C.input,
  font: { color: C.inputFont, bold: true },
};
scenarioControl.getRange("B7:D13").format.font = { color: C.linkedFont };
scenarioControl.getRange("B7:B9").format.numberFormat = FMT_PCT;
scenarioControl.getRange("B10:B12").format.numberFormat = FMT_DAYS;
scenarioControl.getRange("B13").conditionalFormats.add("containsText", {
  text: "CONTINGENCY",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
section(scenarioControl, "F5:N5", "Selected Scenario Outputs");
const selectedOutputs = [
  ["Metric", "Selected Scenario", "Base Case", "Variance to Base"],
  ["Revenue", null, null, null],
  ["Gross Profit", null, null, null],
  ["EBITDA", null, null, null],
  ["EBITDA Margin", null, null, null],
  ["Net Income", null, null, null],
  ["Ending Cash", null, null, null],
  ["Minimum Cash", null, null, null],
  ["Cash Conversion Cycle", null, null, null],
];
scenarioControl.getRange("F6:I14").values = selectedOutputs;
styleDataTable(scenarioControl, "F6:I14", "F6:I6");
const scenarioOutputCols = {
  7: "B",
  8: "C",
  9: "D",
  10: "G",
  11: "E",
  12: "H",
  13: "I",
  14: "J",
};
for (const [rowText, dataCol] of Object.entries(scenarioOutputCols)) {
  const row = Number(rowText);
  scenarioControl.getRange(`G${row}`).formulas = [[
    `=SUMIF('Scenario Data'!$A$6:$A$9,$B$6,'Scenario Data'!$${dataCol}$6:$${dataCol}$9)`,
  ]];
  scenarioControl.getRange(`H${row}`).formulas = [[
    `=SUMIF('Scenario Data'!$A$6:$A$9,"Base",'Scenario Data'!$${dataCol}$6:$${dataCol}$9)`,
  ]];
  scenarioControl.getRange(`I${row}`).formulas = [[`=G${row}-H${row}`]];
}
scenarioControl.getRange("G7:I9").format.numberFormat = FMT_TRY;
scenarioControl.getRange("G11:I13").format.numberFormat = FMT_TRY;
scenarioControl.getRange("G10:I10").format.numberFormat = FMT_PCT;
scenarioControl.getRange("G14:I14").format.numberFormat = FMT_DAYS;
scenarioControl.getRange("G7:H14").format.font = { color: C.linkedFont };
scenarioControl.getRange("K7:N11").values = [
  ["Scenario", "Revenue", "EBITDA", "Ending Cash"],
  ...scenarioSummary.rows.map((row) => [row[0], row[1], row[3], row[7]]),
];
styleDataTable(scenarioControl, "K7:N11", "K7:N7");
scenarioControl.getRange("L8:N11").format.numberFormat = FMT_TRY;
const scenarioChart = scenarioControl.charts.add(
  "bar",
  scenarioControl.getRange("K7:M11"),
);
scenarioChart.title = "FY2026 Revenue and EBITDA by Scenario";
scenarioChart.hasLegend = true;
scenarioChart.setPosition("F17", "N34");
setWidths(scenarioControl, {
  "A:A": 28,
  "B:B": 20,
  "C:D": 4,
  "F:F": 25,
  "G:I": 20,
  "J:J": 4,
  "K:K": 16,
  "L:N": 18,
});

// P&L Data formatting
pnlData.getRange("B6:L77").format.numberFormat = FMT_TRY;
pnlData.getRange("M6:O77").format.numberFormat = FMT_PCT;
pnlData.getRange("V6:W77").format.numberFormat = FMT_PCT;
setWidths(pnlData, { "A:A": 13, "B:O": 18, "P:W": 16 });

// Income Statement
titleBand(
  incomeStatement,
  "Management Income Statement",
  "Actual, budget and rolling forecast | TRY millions",
  "H",
);
incomeStatement.getRange("A5:H5").values = [[
  "Line Item",
  "FY2024 Actual",
  "FY2025 Actual",
  "H1 2026 Actual",
  "FY2026 Budget",
  "FY2026 Forecast",
  "F vs B Var",
  "F vs B Var %",
]];
const pnlLines = [
  ["Revenue", "F"],
  ["COGS", "B"],
  ["Gross Profit", "H"],
  ["Gross Margin", null],
  ["Operating Expense", "E"],
  ["EBITDA", "I"],
  ["EBITDA Margin", null],
  ["Depreciation", "C"],
  ["EBIT", "J"],
  ["Interest", "D"],
  ["Tax", "G"],
  ["Net Income", "L"],
];
incomeStatement.getRange("A6:A17").values = pnlLines.map((line) => [line[0]]);
styleDataTable(incomeStatement, "A5:H17", "A5:H5", { fontSize: 10 });
const columnSpecs = [
  ["B", "Actual", 2024],
  ["C", "Actual", 2025],
  ["D", "Actual", 2026],
  ["E", "Budget", 2026],
  ["F", "Forecast", 2026],
];
for (const [targetCol, version, year] of columnSpecs) {
  for (let i = 0; i < pnlLines.length; i += 1) {
    const row = 6 + i;
    const sourceCol = pnlLines[i][1];
    if (pnlLines[i][0] === "Gross Margin") {
      incomeStatement.getRange(`${targetCol}${row}`).formulas = [[
        `=${targetCol}8/${targetCol}6`,
      ]];
    } else if (pnlLines[i][0] === "EBITDA Margin") {
      incomeStatement.getRange(`${targetCol}${row}`).formulas = [[
        `=${targetCol}11/${targetCol}6`,
      ]];
    } else {
      incomeStatement.getRange(`${targetCol}${row}`).formulas = [[
        `=SUMIFS('P&L Data'!$${sourceCol}$6:$${sourceCol}$77,'P&L Data'!$P$6:$P$77,"${version}",'P&L Data'!$T$6:$T$77,${year})`,
      ]];
    }
  }
}
for (let row = 6; row <= 17; row += 1) {
  incomeStatement.getRange(`G${row}`).formulas = [[`=F${row}-E${row}`]];
  incomeStatement.getRange(`H${row}`).formulas = [[
    `=IFERROR(G${row}/ABS(E${row}),0)`,
  ]];
}
incomeStatement.getRange("B6:H17").format.font = { color: C.linkedFont };
incomeStatement.getRange("B6:H8").format.numberFormat = FMT_TRY;
incomeStatement.getRange("B9:H9").format.numberFormat = FMT_PCT;
incomeStatement.getRange("B10:H11").format.numberFormat = FMT_TRY;
incomeStatement.getRange("B12:H12").format.numberFormat = FMT_PCT;
incomeStatement.getRange("B13:H17").format.numberFormat = FMT_TRY;
for (const row of [6, 8, 11, 17]) {
  incomeStatement.getRange(`A${row}:H${row}`).format = {
    fill: row === 11 ? C.lightBlue : C.light,
    font: { color: C.text, bold: true },
    borders: {
      top: { style: "thin", color: C.navy2 },
      bottom: { style: "thin", color: C.line },
    },
  };
  incomeStatement.getRange(`B${row}:H${row}`).format.font = {
    color: C.linkedFont,
    bold: true,
  };
}
incomeStatement.getRange("B6:H8").format.numberFormat = FMT_TRY;
incomeStatement.getRange("B9:H9").format.numberFormat = FMT_PCT;
incomeStatement.getRange("B10:H11").format.numberFormat = FMT_TRY;
incomeStatement.getRange("B12:H12").format.numberFormat = FMT_PCT;
incomeStatement.getRange("B13:H17").format.numberFormat = FMT_TRY;
incomeStatement.getRange("H6:H17").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleRed },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleGreen },
  ],
});
setWidths(incomeStatement, { "A:A": 28, "B:H": 20 });

// Budget vs Actual
titleBand(
  budgetVsActual,
  "Budget vs Actual & Forecast Variance",
  "H1 actual performance and FY2026 rolling forecast gap",
  "H",
);
budgetVsActual.getRange("A5:F15").values = [
  ["Metric", "H1 Actual", "H1 Budget", "Variance", "Variance %", "Status"],
  ...pnlLines
    .filter((line) => !line[0].includes("Margin"))
    .map((line) => [line[0], null, null, null, null, null]),
];
styleDataTable(budgetVsActual, "A5:F15", "A5:F5");
const statementRows = Object.fromEntries(
  pnlLines.map((line, index) => [line[0], 6 + index]),
);
const varianceMetrics = pnlLines.filter((line) => !line[0].includes("Margin"));
for (let index = 0; index < varianceMetrics.length; index += 1) {
  const row = 6 + index;
  const metric = varianceMetrics[index][0];
  const sourceRow = statementRows[metric];
  budgetVsActual.getRange(`B${row}`).formulas = [[`='Income Statement'!D${sourceRow}`]];
  const sourceCol = varianceMetrics[index][1];
  budgetVsActual.getRange(`C${row}`).formulas = [[
    `=SUMIFS('P&L Data'!$${sourceCol}$6:$${sourceCol}$77,'P&L Data'!$P$6:$P$77,"Budget",'P&L Data'!$A$6:$A$77,">=2026-01-01",'P&L Data'!$A$6:$A$77,"<=2026-06-01")`,
  ]];
  budgetVsActual.getRange(`D${row}`).formulas = [[`=B${row}-C${row}`]];
  budgetVsActual.getRange(`E${row}`).formulas = [[
    `=IFERROR(D${row}/ABS(C${row}),0)`,
  ]];
  const lowerIsBetter = ["COGS", "Operating Expense", "Depreciation", "Interest", "Tax"].includes(metric);
  budgetVsActual.getRange(`F${row}`).formulas = [[
    `=IF(D${row}${lowerIsBetter ? "<=" : ">="}0,"FAVORABLE","UNFAVORABLE")`,
  ]];
}
budgetVsActual.getRange("B6:D15").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
budgetVsActual.getRange("E6:E15").format.numberFormat = FMT_PCT;
budgetVsActual.getRange("F6:F15").conditionalFormats.add("containsText", {
  text: "FAVORABLE",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
budgetVsActual.getRange("F6:F15").conditionalFormats.add("containsText", {
  text: "UNFAVORABLE",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
section(budgetVsActual, "A18:H18", "FY2026 Forecast-to-Budget EBITDA Bridge");
budgetVsActual.getRange("A19:B26").values = [
  ["Bridge Item", "Impact (TRY)"],
  ["FY2026 Budget EBITDA", 158.666],
  ["Volume Impact", -27.859],
  ["Price & Mix Impact", -20.175],
  ["Gross Margin / COGS Impact", 10.774],
  ["Payroll Impact", 5.545],
  ["Marketing Impact", 4.154],
  ["FY2026 Rolling Forecast EBITDA", 164.381],
];
styleDataTable(budgetVsActual, "A19:B26", "A19:B19");
budgetVsActual.getRange("B20:B26").format.numberFormat = FMT_TRY;
setWidths(budgetVsActual, { "A:A": 35, "B:E": 20, "F:F": 18, "G:H": 4 });

// Dashboard Data formula-backed helper ranges
titleBand(
  dashboardData,
  "Dashboard Data",
  "Formula-backed helper ranges for executive charts",
  "J",
);
dashboardData.getRange("A5:E17").values = [
  ["Month", "Budget Revenue", "Forecast Revenue", "Budget EBITDA", "Forecast EBITDA"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
    null,
    null,
  ]),
];
styleDataTable(dashboardData, "A5:E17", "A5:E5");
for (let row = 6; row <= 17; row += 1) {
  dashboardData.getRange(`B${row}`).formulas = [[
    `=SUMIFS('P&L Data'!$F$6:$F$77,'P&L Data'!$A$6:$A$77,$A${row},'P&L Data'!$P$6:$P$77,"Budget")`,
  ]];
  dashboardData.getRange(`C${row}`).formulas = [[
    `=SUMIFS('P&L Data'!$F$6:$F$77,'P&L Data'!$A$6:$A$77,$A${row},'P&L Data'!$P$6:$P$77,"Forecast")`,
  ]];
  dashboardData.getRange(`D${row}`).formulas = [[
    `=SUMIFS('P&L Data'!$I$6:$I$77,'P&L Data'!$A$6:$A$77,$A${row},'P&L Data'!$P$6:$P$77,"Budget")`,
  ]];
  dashboardData.getRange(`E${row}`).formulas = [[
    `=SUMIFS('P&L Data'!$I$6:$I$77,'P&L Data'!$A$6:$A$77,$A${row},'P&L Data'!$P$6:$P$77,"Forecast")`,
  ]];
}
dashboardData.getRange("B6:E17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
dashboardData.getRange("G5:J9").values = [
  ["Scenario", "Revenue", "EBITDA", "Ending Cash"],
  ...scenarioSummary.rows.map((row) => [row[0], row[1], row[3], row[7]]),
];
styleDataTable(dashboardData, "G5:J9", "G5:J5");
dashboardData.getRange("H6:J9").format.numberFormat = FMT_TRY;
setWidths(dashboardData, { "A:A": 15, "B:E": 20, "G:G": 16, "H:J": 20 });

// Executive Dashboard
titleBand(
  dashboard,
  "Executive FP&A Dashboard",
  "FY2026 budget, Q2 rolling forecast and scenario decision support",
  "N",
);
card(
  dashboard,
  "A5:C5",
  "A6:C8",
  "FY2026 Forecast Revenue",
  "='Income Statement'!F6",
  FMT_TRY,
);
card(
  dashboard,
  "D5:F5",
  "D6:F8",
  "FY2026 Forecast EBITDA",
  "='Income Statement'!F11",
  FMT_TRY,
  C.cyan,
);
card(
  dashboard,
  "G5:I5",
  "G6:I8",
  "EBITDA Margin",
  "='Income Statement'!F12",
  FMT_PCT,
  C.green,
);
card(
  dashboard,
  "J5:L5",
  "J6:L8",
  "Forecast vs Budget Revenue",
  "='Income Statement'!G6",
  FMT_TRY,
  C.amber,
);
const revenueChart = dashboard.charts.add(
  "line",
  dashboardData.getRange("A5:C17"),
);
revenueChart.title = "FY2026 Monthly Revenue | Budget vs Forecast";
revenueChart.hasLegend = true;
revenueChart.setPosition("A11", "G27");
revenueChart.yAxis = { numberFormatCode: '₺0,,"m"' };
const ebitdaChart = dashboard.charts.add(
  "bar",
  dashboardData.getRange("L5:N17"),
);
ebitdaChart.title = "FY2026 Monthly EBITDA | Budget vs Forecast";
ebitdaChart.hasLegend = true;
ebitdaChart.setPosition("H11", "N27");
ebitdaChart.yAxis = { numberFormatCode: '₺0,,"m"' };
section(dashboard, "A30:N30", "Management Takeaways");
dashboard.getRange("A31:N37").merge();
dashboard.getRange("A31").values = [[
  "The Q2 rolling forecast expects FY2026 revenue to finish 2.6% below budget, while EBITDA remains above plan due to tighter operating-expense control. Gross-margin delivery and the working-capital gap are the principal management risks. The Base scenario preserves strong liquidity; Downside and Stress cases should trigger staged spend controls, collection actions and capex gating.",
]];
dashboard.getRange("A31:N37").format = {
  fill: C.lightBlue,
  font: { color: C.navy, size: 12 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: C.cyan },
};
setWidths(dashboard, { "A:N": 12 });

// Rolling Forecast
titleBand(
  rollingForecast,
  "Rolling Forecast | FY2026",
  "Monthly budget, forecast, EBITDA and liquidity outlook",
  "I",
);
rollingForecast.getRange("A5:I17").values = [
  ["Month", "Budget Revenue", "Forecast Revenue", "Revenue Var", "Budget EBITDA", "Forecast EBITDA", "EBITDA Var", "Ending Cash", "CCC Days"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
  ]),
];
styleDataTable(rollingForecast, "A5:I17", "A5:I5");
for (let row = 6; row <= 17; row += 1) {
  rollingForecast.getRange(`B${row}`).formulas = [[`='Dashboard Data'!B${row}`]];
  rollingForecast.getRange(`C${row}`).formulas = [[`='Dashboard Data'!C${row}`]];
  rollingForecast.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  rollingForecast.getRange(`E${row}`).formulas = [[`='Dashboard Data'!D${row}`]];
  rollingForecast.getRange(`F${row}`).formulas = [[`='Dashboard Data'!E${row}`]];
  rollingForecast.getRange(`G${row}`).formulas = [[`=F${row}-E${row}`]];
  rollingForecast.getRange(`H${row}`).formulas = [[
    `=SUMIFS('Cash Data'!$H$6:$H$77,'Cash Data'!$A$6:$A$77,$A${row},'Cash Data'!$B$6:$B$77,"Forecast")`,
  ]];
  rollingForecast.getRange(`I${row}`).formulas = [[
    `=SUMIFS('WC Data'!$F$6:$F$77,'WC Data'!$A$6:$A$77,$A${row},'WC Data'!$B$6:$B$77,"Forecast")`,
  ]];
}
rollingForecast.getRange("B6:H17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
rollingForecast.getRange("I6:I17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_DAYS,
};
rollingForecast.getRange("D6:D17").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleRed },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleGreen },
  ],
});
const rollingChart = rollingForecast.charts.add(
  "line",
  rollingForecast.getRange("A5:C17"),
);
rollingChart.title = "Revenue Outlook";
rollingChart.hasLegend = true;
rollingChart.setPosition("A20", "E35");
const cashChart = rollingForecast.charts.add(
  "line",
  rollingForecast.getRange("A5:A17").getCurrentRegion(),
);
cashChart.title = "Ending Cash & CCC";
cashChart.hasLegend = true;
cashChart.setPosition("F20", "I35");
setWidths(rollingForecast, { "A:A": 15, "B:H": 18, "I:I": 15 });

// Revenue Drivers
titleBand(
  revenueDrivers,
  "Revenue Driver Planning",
  "FY2026 business-unit revenue, gross margin and EBITDA delivery",
  "H",
);
revenueDrivers.getRange("A5:H10").values = [
  ["Business Unit", "Budget Revenue", "Forecast Revenue", "Variance", "Forecast Gross Profit", "Gross Margin", "Forecast EBITDA", "EBITDA Margin"],
  ["Digital Commerce", null, null, null, null, null, null, null],
  ["Retail Stores", null, null, null, null, null, null, null],
  ["Wholesale", null, null, null, null, null, null, null],
  ["Subscription Services", null, null, null, null, null, null, null],
  ["Shared Services", null, null, null, null, null, null, null],
];
styleDataTable(revenueDrivers, "A5:H10", "A5:H5");
for (let row = 6; row <= 10; row += 1) {
  revenueDrivers.getRange(`B${row}`).formulas = [[
    `=SUMIFS('BU Data'!$D$6:$D$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Budget",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`C${row}`).formulas = [[
    `=SUMIFS('BU Data'!$D$6:$D$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  revenueDrivers.getRange(`E${row}`).formulas = [[
    `=SUMIFS('BU Data'!$E$6:$E$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`F${row}`).formulas = [[`=IFERROR(E${row}/C${row},0)`]];
  revenueDrivers.getRange(`G${row}`).formulas = [[
    `=SUMIFS('BU Data'!$G$6:$G$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`H${row}`).formulas = [[`=IFERROR(G${row}/C${row},0)`]];
}
revenueDrivers.getRange("B6:E10").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
revenueDrivers.getRange("F6:F10").format.numberFormat = FMT_PCT;
revenueDrivers.getRange("G6:G10").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
revenueDrivers.getRange("H6:H10").format.numberFormat = FMT_PCT;
const buChart = revenueDrivers.charts.add(
  "bar",
  revenueDrivers.getRange("A5:C10"),
);
buChart.title = "FY2026 Revenue by Business Unit";
buChart.hasLegend = true;
buChart.setPosition("A13", "H30");
setWidths(revenueDrivers, { "A:A": 26, "B:E": 19, "F:F": 15, "G:G": 19, "H:H": 15 });

// Opex Planning
titleBand(
  opexPlanning,
  "Operating Expense Planning",
  "FY2026 department-level forecast versus budget",
  "G",
);
const departments = [
  "Sales",
  "Customer Success",
  "Marketing",
  "Operations",
  "Technology",
  "Finance & Corporate",
];
opexPlanning.getRange("A5:G11").values = [
  ["Department", "Budget Opex", "Forecast Opex", "Variance", "Variance %", "Forecast Payroll", "Status"],
  ...departments.map((name) => [name, null, null, null, null, null, null]),
];
styleDataTable(opexPlanning, "A5:G11", "A5:G5");
for (let row = 6; row <= 11; row += 1) {
  opexPlanning.getRange(`B${row}`).formulas = [[
    `=SUMIFS('Department Data'!$F$6:$F$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Budget",'Department Data'!$R$6:$R$437,2026)`,
  ]];
  opexPlanning.getRange(`C${row}`).formulas = [[
    `=SUMIFS('Department Data'!$F$6:$F$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Forecast",'Department Data'!$R$6:$R$437,2026)`,
  ]];
  opexPlanning.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  opexPlanning.getRange(`E${row}`).formulas = [[`=IFERROR(D${row}/ABS(B${row}),0)`]];
  opexPlanning.getRange(`F${row}`).formulas = [[
    `=SUMIFS('Headcount Data'!$F$6:$F$437,'Headcount Data'!$C$6:$C$437,$A${row},'Headcount Data'!$B$6:$B$437,"Forecast",'Headcount Data'!$A$6:$A$437,">=2026-01-01",'Headcount Data'!$A$6:$A$437,"<=2026-12-01")`,
  ]];
  opexPlanning.getRange(`G${row}`).formulas = [[
    `=IF(D${row}<=0,"WITHIN PLAN","OVER PLAN")`,
  ]];
}
opexPlanning.getRange("B6:D11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
opexPlanning.getRange("E6:E11").format.numberFormat = FMT_PCT;
opexPlanning.getRange("F6:F11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
opexPlanning.getRange("G6:G11").conditionalFormats.add("containsText", {
  text: "WITHIN",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
opexPlanning.getRange("G6:G11").conditionalFormats.add("containsText", {
  text: "OVER",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
const opexChart = opexPlanning.charts.add(
  "bar",
  opexPlanning.getRange("A5:C11"),
);
opexChart.title = "Department Opex | Budget vs Forecast";
opexChart.hasLegend = true;
opexChart.setPosition("A14", "G30");
setWidths(opexPlanning, { "A:A": 28, "B:F": 19, "G:G": 17 });

// Cash Flow
titleBand(
  cashFlowSheet,
  "Cash Flow & Liquidity",
  "FY2026 rolling cash outlook | operating cash, capex and ending liquidity",
  "H",
);
cashFlowSheet.getRange("A5:H17").values = [
  ["Month", "Beginning Cash", "Cash From Operations", "Capex", "Financing", "Net Cash Flow", "Ending Cash", "Liquidity Status"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
  ]),
];
styleDataTable(cashFlowSheet, "A5:H17", "A5:H5");
const cashSourceCols = { B: "C", C: "D", D: "E", E: "F", F: "G", G: "H" };
for (let row = 6; row <= 17; row += 1) {
  for (const [targetCol, sourceCol] of Object.entries(cashSourceCols)) {
    cashFlowSheet.getRange(`${targetCol}${row}`).formulas = [[
      `=SUMIFS('Cash Data'!$${sourceCol}$6:$${sourceCol}$77,'Cash Data'!$A$6:$A$77,$A${row},'Cash Data'!$B$6:$B$77,"Forecast")`,
    ]];
  }
  cashFlowSheet.getRange(`H${row}`).formulas = [[
    `=IF(G${row}<100,"WATCH",IF(G${row}<180,"ADEQUATE","STRONG"))`,
  ]];
}
cashFlowSheet.getRange("B6:G17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
cashFlowSheet.getRange("H6:H17").conditionalFormats.add("containsText", {
  text: "STRONG",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
cashFlowSheet.getRange("H6:H17").conditionalFormats.add("containsText", {
  text: "WATCH",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
const liquidityChart = cashFlowSheet.charts.add(
  "line",
  cashFlowSheet.getRange("J5:K17"),
);
liquidityChart.title = "FY2026 Ending Cash";
liquidityChart.hasLegend = true;
liquidityChart.setPosition("A20", "H35");
setWidths(cashFlowSheet, { "A:A": 15, "B:G": 19, "H:H": 18 });

// Working Capital
titleBand(
  workingCapitalSheet,
  "Working Capital & Cash Conversion Cycle",
  "FY2026 forecast | DSO, DIO, DPO and net working capital",
  "I",
);
workingCapitalSheet.getRange("A5:I17").values = [
  ["Month", "DSO", "DIO", "DPO", "CCC", "Accounts Receivable", "Inventory", "Accounts Payable", "Net Working Capital"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
  ]),
];
styleDataTable(workingCapitalSheet, "A5:I17", "A5:I5");
const wcSourceCols = { B: "C", C: "D", D: "E", E: "F", F: "G", G: "H", H: "I", I: "J" };
for (let row = 6; row <= 17; row += 1) {
  for (const [targetCol, sourceCol] of Object.entries(wcSourceCols)) {
    workingCapitalSheet.getRange(`${targetCol}${row}`).formulas = [[
      `=SUMIFS('WC Data'!$${sourceCol}$6:$${sourceCol}$77,'WC Data'!$A$6:$A$77,$A${row},'WC Data'!$B$6:$B$77,"Forecast")`,
    ]];
  }
}
workingCapitalSheet.getRange("B6:E17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_DAYS,
};
workingCapitalSheet.getRange("F6:I17").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
workingCapitalSheet.getRange("E6:E17").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleGreen },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleRed },
  ],
});
workingCapitalSheet.getRange("K5:N17").values = [
  ["Month", "DSO", "DIO", "DPO"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
    null,
  ]),
];
styleDataTable(workingCapitalSheet, "K5:N17", "K5:N5");
for (let row = 6; row <= 17; row += 1) {
  workingCapitalSheet.getRange(`L${row}`).formulas = [[`=B${row}`]];
  workingCapitalSheet.getRange(`M${row}`).formulas = [[`=C${row}`]];
  workingCapitalSheet.getRange(`N${row}`).formulas = [[`=D${row}`]];
}
workingCapitalSheet.getRange("L6:N17").format.numberFormat = FMT_DAYS;
const wcChart = workingCapitalSheet.charts.add(
  "line",
  workingCapitalSheet.getRange("K5:N17"),
);
wcChart.title = "Working-Capital Days";
wcChart.hasLegend = true;
wcChart.setPosition("A20", "I35");
setWidths(workingCapitalSheet, {
  "A:A": 15,
  "B:E": 13,
  "F:I": 19,
  "J:J": 3,
  "K:K": 15,
  "L:N": 13,
});

// Headcount Plan
titleBand(
  headcountPlan,
  "Headcount & Workforce Plan",
  "December 2026 FTE and full-year payroll | budget versus rolling forecast",
  "G",
);
headcountPlan.getRange("A5:G11").values = [
  ["Department", "Budget FTE", "Forecast FTE", "FTE Var", "Budget Payroll", "Forecast Payroll", "Payroll Var"],
  ...departments.map((name) => [name, null, null, null, null, null, null]),
];
styleDataTable(headcountPlan, "A5:G11", "A5:G5");
for (let row = 6; row <= 11; row += 1) {
  headcountPlan.getRange(`B${row}`).formulas = [[
    `=SUMIFS('Headcount Data'!$D$6:$D$437,'Headcount Data'!$C$6:$C$437,$A${row},'Headcount Data'!$B$6:$B$437,"Budget",'Headcount Data'!$A$6:$A$437,"2026-12-01")`,
  ]];
  headcountPlan.getRange(`C${row}`).formulas = [[
    `=SUMIFS('Headcount Data'!$D$6:$D$437,'Headcount Data'!$C$6:$C$437,$A${row},'Headcount Data'!$B$6:$B$437,"Forecast",'Headcount Data'!$A$6:$A$437,"2026-12-01")`,
  ]];
  headcountPlan.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  headcountPlan.getRange(`E${row}`).formulas = [[
    `=SUMIFS('Headcount Data'!$G$6:$G$437,'Headcount Data'!$C$6:$C$437,$A${row},'Headcount Data'!$B$6:$B$437,"Budget",'Headcount Data'!$A$6:$A$437,">=2026-01-01",'Headcount Data'!$A$6:$A$437,"<=2026-12-01")`,
  ]];
  headcountPlan.getRange(`F${row}`).formulas = [[
    `=SUMIFS('Headcount Data'!$G$6:$G$437,'Headcount Data'!$C$6:$C$437,$A${row},'Headcount Data'!$B$6:$B$437,"Forecast",'Headcount Data'!$A$6:$A$437,">=2026-01-01",'Headcount Data'!$A$6:$A$437,"<=2026-12-01")`,
  ]];
  headcountPlan.getRange(`G${row}`).formulas = [[`=F${row}-E${row}`]];
}
headcountPlan.getRange("B6:D11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_NUM,
};
headcountPlan.getRange("E6:G11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
const hcChart = headcountPlan.charts.add(
  "bar",
  headcountPlan.getRange("A5:C11"),
);
hcChart.title = "December 2026 FTE | Budget vs Forecast";
hcChart.hasLegend = true;
hcChart.setPosition("A14", "G30");
setWidths(headcountPlan, { "A:A": 28, "B:D": 15, "E:G": 20 });

// Capex Plan
titleBand(
  capexPlan,
  "Capital Expenditure Plan",
  "FY2026 spend, depreciation and year-end net book value",
  "H",
);
capexPlan.getRange("A5:H11").values = [
  ["Department", "Budget Capex", "Forecast Capex", "Variance", "Variance %", "Forecast Depreciation", "Dec-26 NBV", "Status"],
  ...departments.map((name) => [name, null, null, null, null, null, null, null]),
];
styleDataTable(capexPlan, "A5:H11", "A5:H5");
for (let row = 6; row <= 11; row += 1) {
  capexPlan.getRange(`B${row}`).formulas = [[
    `=SUMIFS('Capex Data'!$D$6:$D$755,'Capex Data'!$C$6:$C$755,$A${row},'Capex Data'!$B$6:$B$755,"Budget",'Capex Data'!$A$6:$A$755,">=2026-01-01",'Capex Data'!$A$6:$A$755,"<=2026-12-01")`,
  ]];
  capexPlan.getRange(`C${row}`).formulas = [[
    `=SUMIFS('Capex Data'!$D$6:$D$755,'Capex Data'!$C$6:$C$755,$A${row},'Capex Data'!$B$6:$B$755,"Forecast",'Capex Data'!$A$6:$A$755,">=2026-01-01",'Capex Data'!$A$6:$A$755,"<=2026-12-01")`,
  ]];
  capexPlan.getRange(`D${row}`).formulas = [[`=C${row}-B${row}`]];
  capexPlan.getRange(`E${row}`).formulas = [[`=IFERROR(D${row}/ABS(B${row}),0)`]];
  capexPlan.getRange(`F${row}`).formulas = [[
    `=SUMIFS('Capex Data'!$E$6:$E$755,'Capex Data'!$C$6:$C$755,$A${row},'Capex Data'!$B$6:$B$755,"Forecast",'Capex Data'!$A$6:$A$755,">=2026-01-01",'Capex Data'!$A$6:$A$755,"<=2026-12-01")`,
  ]];
  capexPlan.getRange(`G${row}`).formulas = [[
    `=SUMIFS('Capex Data'!$F$6:$F$755,'Capex Data'!$C$6:$C$755,$A${row},'Capex Data'!$B$6:$B$755,"Forecast",'Capex Data'!$A$6:$A$755,"2026-12-01")`,
  ]];
  capexPlan.getRange(`H${row}`).formulas = [[
    `=IF(D${row}<=0,"WITHIN PLAN","OVER PLAN")`,
  ]];
}
capexPlan.getRange("B6:D11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
capexPlan.getRange("E6:E11").format.numberFormat = FMT_PCT;
capexPlan.getRange("F6:G11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
capexPlan.getRange("H6:H11").conditionalFormats.add("containsText", {
  text: "WITHIN",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
capexPlan.getRange("H6:H11").conditionalFormats.add("containsText", {
  text: "OVER",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
const capexChart = capexPlan.charts.add(
  "bar",
  capexPlan.getRange("A5:C11"),
);
capexChart.title = "FY2026 Capex | Budget vs Forecast";
capexChart.hasLegend = true;
capexChart.setPosition("A14", "H30");
setWidths(capexPlan, { "A:A": 28, "B:G": 19, "H:H": 17 });

// Department Budget
titleBand(
  departmentBudget,
  "Department Budget Ownership",
  "FY2026 revenue, opex and EBITDA accountability",
  "H",
);
departmentBudget.getRange("A5:H11").values = [
  ["Department", "Budget Revenue", "Forecast Revenue", "Revenue Var", "Budget Opex", "Forecast Opex", "Forecast EBITDA", "Forecast EBITDA Margin"],
  ...departments.map((name) => [name, null, null, null, null, null, null, null]),
];
styleDataTable(departmentBudget, "A5:H11", "A5:H5");
for (let row = 6; row <= 11; row += 1) {
  const formulas = {
    B: `=SUMIFS('Department Data'!$G$6:$G$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Budget",'Department Data'!$R$6:$R$437,2026)`,
    C: `=SUMIFS('Department Data'!$G$6:$G$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Forecast",'Department Data'!$R$6:$R$437,2026)`,
    D: `=C${row}-B${row}`,
    E: `=SUMIFS('Department Data'!$F$6:$F$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Budget",'Department Data'!$R$6:$R$437,2026)`,
    F: `=SUMIFS('Department Data'!$F$6:$F$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Forecast",'Department Data'!$R$6:$R$437,2026)`,
    G: `=SUMIFS('Department Data'!$J$6:$J$437,'Department Data'!$B$6:$B$437,$A${row},'Department Data'!$Q$6:$Q$437,"Forecast",'Department Data'!$R$6:$R$437,2026)`,
    H: `=IFERROR(G${row}/C${row},0)`,
  };
  for (const [column, formula] of Object.entries(formulas)) {
    departmentBudget.getRange(`${column}${row}`).formulas = [[formula]];
  }
}
departmentBudget.getRange("B6:G11").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
departmentBudget.getRange("H6:H11").format.numberFormat = FMT_PCT;
setWidths(departmentBudget, { "A:A": 28, "B:G": 19, "H:H": 20 });

// Business Unit
titleBand(
  businessUnitSheet,
  "Business Unit Performance",
  "FY2026 budget and forecast profitability by operating model",
  "H",
);
businessUnitSheet.getRange("A5:H10").values = [
  ["Business Unit", "Budget Revenue", "Forecast Revenue", "Revenue Var", "Forecast Gross Profit", "Gross Margin", "Forecast EBITDA", "EBITDA Margin"],
  ["Digital Commerce", null, null, null, null, null, null, null],
  ["Retail Stores", null, null, null, null, null, null, null],
  ["Wholesale", null, null, null, null, null, null, null],
  ["Subscription Services", null, null, null, null, null, null, null],
  ["Shared Services", null, null, null, null, null, null, null],
];
styleDataTable(businessUnitSheet, "A5:H10", "A5:H5");
for (let row = 6; row <= 10; row += 1) {
  const formulas = {
    B: `=SUMIFS('BU Data'!$G$6:$G$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Budget",'BU Data'!$R$6:$R$365,2026)`,
    C: `=SUMIFS('BU Data'!$G$6:$G$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
    D: `=C${row}-B${row}`,
    E: `=SUMIFS('BU Data'!$I$6:$I$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
    F: `=IFERROR(E${row}/C${row},0)`,
    G: `=SUMIFS('BU Data'!$J$6:$J$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
    H: `=IFERROR(G${row}/C${row},0)`,
  };
  for (const [column, formula] of Object.entries(formulas)) {
    businessUnitSheet.getRange(`${column}${row}`).formulas = [[formula]];
  }
}
businessUnitSheet.getRange("B6:E10").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
businessUnitSheet.getRange("F6:F10").format.numberFormat = FMT_PCT;
businessUnitSheet.getRange("G6:G10").format = {
  font: { color: C.linkedFont },
  numberFormat: FMT_TRY,
};
businessUnitSheet.getRange("H6:H10").format.numberFormat = FMT_PCT;
const businessChart = businessUnitSheet.charts.add(
  "bar",
  businessUnitSheet.getRange("A5:C10"),
);
businessChart.title = "FY2026 Revenue by Business Unit";
businessChart.hasLegend = true;
businessChart.setPosition("A13", "H30");
setWidths(businessUnitSheet, { "A:A": 26, "B:E": 19, "F:F": 15, "G:G": 19, "H:H": 15 });

// Correct Revenue Drivers formulas to the exact BU data columns.
for (let row = 6; row <= 10; row += 1) {
  revenueDrivers.getRange(`B${row}`).formulas = [[
    `=SUMIFS('BU Data'!$G$6:$G$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Budget",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`C${row}`).formulas = [[
    `=SUMIFS('BU Data'!$G$6:$G$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`E${row}`).formulas = [[
    `=SUMIFS('BU Data'!$I$6:$I$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
  revenueDrivers.getRange(`G${row}`).formulas = [[
    `=SUMIFS('BU Data'!$J$6:$J$365,'BU Data'!$B$6:$B$365,$A${row},'BU Data'!$Q$6:$Q$365,"Forecast",'BU Data'!$R$6:$R$365,2026)`,
  ]];
}

// Forecast Accuracy
titleBand(
  forecastAccuracy,
  "Forecast Accuracy & Model Governance",
  "Business-unit backtest metrics and selected champion models",
  "H",
);
const championRows = modelComparison.rows.filter((row) => row[7] === true);
forecastAccuracy.getRange("A5:H9").values = [
  modelComparison.headers,
  ...championRows,
];
styleDataTable(forecastAccuracy, "A5:H9", "A5:H5");
forecastAccuracy.getRange("C6:D9").format.numberFormat = FMT_TRY_FULL;
forecastAccuracy.getRange("E6:G9").format.numberFormat = FMT_PCT;
forecastAccuracy.getRange("E6:E9").conditionalFormats.add("colorScale", {
  criteria: [
    { type: "lowestValue", color: C.paleGreen },
    { type: "percentile", value: 50, color: C.paleAmber },
    { type: "highestValue", color: C.paleRed },
  ],
});
forecastAccuracy.getRange("J5:K9").values = [
  ["Business Unit", "Champion WAPE"],
  ...championRows.map((row) => [row[0], row[4]]),
];
styleDataTable(forecastAccuracy, "J5:K9", "J5:K5");
forecastAccuracy.getRange("K6:K9").format.numberFormat = FMT_PCT;
const modelChart = forecastAccuracy.charts.add(
  "bar",
  forecastAccuracy.getRange("J5:K9"),
);
modelChart.title = "Champion Model WAPE";
modelChart.hasLegend = false;
modelChart.setPosition("A13", "H29");
setWidths(forecastAccuracy, {
  "A:A": 26,
  "B:B": 30,
  "C:G": 15,
  "H:H": 15,
  "I:I": 3,
  "J:J": 26,
  "K:K": 18,
});

// Risk Analysis
titleBand(
  riskAnalysis,
  "Scenario & Monte Carlo Risk Analysis",
  "5,000 simulations | revenue, EBITDA and liquidity confidence ranges",
  "J",
);
riskAnalysis.getRange("A5:C14").values = [
  riskSummary.headers,
  ...riskSummary.rows,
];
styleDataTable(riskAnalysis, "A5:C14", "A5:C5");
for (let row = 6; row <= 14; row += 1) {
  const unit = riskSummary.rows[row - 6][2];
  riskAnalysis.getRange(`B${row}`).format.numberFormat =
    unit === "Percent" ? FMT_PCT : FMT_TRY;
}
riskAnalysis.getRange("E5:J9").values = [
  ["Scenario", "Revenue", "EBITDA", "EBITDA Margin", "Ending Cash", "Minimum Cash"],
  ...scenarioSummary.rows.map((row) => [row[0], row[1], row[3], row[6], row[7], row[8]]),
];
styleDataTable(riskAnalysis, "E5:J9", "E5:J5");
riskAnalysis.getRange("F6:G9").format.numberFormat = FMT_TRY;
riskAnalysis.getRange("H6:H9").format.numberFormat = FMT_PCT;
riskAnalysis.getRange("I6:J9").format.numberFormat = FMT_TRY;
const riskChart = riskAnalysis.charts.add(
  "bar",
  riskAnalysis.getRange("E5:G9"),
);
riskChart.title = "Scenario Revenue & EBITDA";
riskChart.hasLegend = true;
riskChart.setPosition("A17", "J33");
setWidths(riskAnalysis, { "A:A": 36, "B:B": 21, "C:C": 14, "D:D": 3, "E:E": 16, "F:J": 19 });

// Checks
titleBand(
  checks,
  "Model Controls & Audit Checks",
  "Formula-driven financial integrity and completeness controls",
  "G",
);
checks.getRange("A5:G17").values = [
  ["Check", "Actual / Result", "Expected", "Difference", "Tolerance", "Status", "Where to Fix"],
  ["P&L gross profit identity", null, 0, null, 0.01, null, "Income Statement"],
  ["P&L EBITDA identity", null, 0, null, 0.01, null, "Income Statement"],
  ["Net income identity", null, 0, null, 0.01, null, "Income Statement"],
  ["Cash roll-forward", null, 0, null, 0.01, null, "Cash Data"],
  ["Scenario count", null, 4, null, 0, null, "Scenario Data"],
  ["Champion model count", null, 4, null, 0, null, "Model Data"],
  ["Budget submissions approved", null, 12, null, 0, null, "Budget submissions"],
  ["Forecast months", null, 18, null, 0, null, "P&L Data"],
  ["Stress EBITDA below Base", null, 1, null, 0, null, "Scenario Data"],
  ["Negative forecast revenue rows", null, 0, null, 0, null, "P&L Data"],
  ["Forecast EBITDA is positive", null, 1, null, 0, null, "Income Statement"],
  ["MODEL STATUS", null, 11, null, 0, null, "Review failed rows above"],
];
styleDataTable(checks, "A5:G17", "A5:G5");
checks.getRange("B6").formulas = [["='Income Statement'!F8-('Income Statement'!F6-'Income Statement'!F7)"]];
checks.getRange("B7").formulas = [["='Income Statement'!F11-('Income Statement'!F8-'Income Statement'!F10)"]];
checks.getRange("B8").formulas = [["='Income Statement'!F17-('Income Statement'!F11-'Income Statement'!F13-'Income Statement'!F15-'Income Statement'!F16)"]];
checks.getRange("B9").formulas = [["=SUM('Cash Data'!H6:H77)-SUM('Cash Data'!C6:C77)-SUM('Cash Data'!G6:G77)"]];
checks.getRange("B10").formulas = [["=COUNTA('Scenario Data'!A6:A9)"]];
checks.getRange("B11").formulas = [["=COUNTA('Forecast Accuracy'!A6:A9)"]];
checks.getRange("B12").values = [[budgetSubmissions.rows.filter((row) => String(row[5]).startsWith("Approved")).length]];
checks.getRange("B13").formulas = [['=COUNTIFS(\'P&L Data\'!P6:P77,"Forecast")']];
checks.getRange("B14").formulas = [['=IF(SUMIF(\'Scenario Data\'!A6:A9,"Stress",\'Scenario Data\'!D6:D9)<SUMIF(\'Scenario Data\'!A6:A9,"Base",\'Scenario Data\'!D6:D9),1,0)']];
checks.getRange("B15").formulas = [['=COUNTIFS(\'P&L Data\'!P6:P77,"Forecast",\'P&L Data\'!F6:F77,"<0")']];
checks.getRange("B16").formulas = [["=IF('Income Statement'!F11>0,1,0)"]];
for (let row = 6; row <= 16; row += 1) {
  checks.getRange(`D${row}`).formulas = [[`=B${row}-C${row}`]];
  checks.getRange(`F${row}`).formulas = [[
    `=IF(ABS(D${row})<=E${row},"PASS","FAIL")`,
  ]];
}
checks.getRange("B17").formulas = [['=COUNTIF(F6:F16,"PASS")']];
checks.getRange("D17").formulas = [["=B17-C17"]];
checks.getRange("F17").formulas = [['=IF(B17=C17,"PASS","FAIL")']];
checks.getRange("B6:B9").format.numberFormat = FMT_TRY_FULL;
checks.getRange("F6:F17").conditionalFormats.add("containsText", {
  text: "PASS",
  format: { fill: C.paleGreen, font: { color: C.green, bold: true } },
});
checks.getRange("F6:F17").conditionalFormats.add("containsText", {
  text: "FAIL",
  format: { fill: C.paleRed, font: { color: C.red, bold: true } },
});
setWidths(checks, { "A:A": 34, "B:E": 18, "F:F": 14, "G:G": 28 });

// Data Dictionary
titleBand(
  dictionary,
  "FP&A Data Dictionary",
  "Primary analytical entities, measures and business definitions",
  "H",
);
dictionary.getRange("A5:H25").values = [
  ["Table", "Field / Metric", "Type", "Definition", "Grain", "Source", "Owner", "Notes"],
  ["fact_actuals", "AmountTRY", "Currency", "Natural-sign actual ledger amount", "Month-account-cost center", "Synthetic ERP", "Controllership", "Non-negative storage"],
  ["fact_budget", "AmountTRY", "Currency", "Approved FY2026 budget amount", "Month-account-cost center", "Budget v1", "FP&A", "12 months"],
  ["fact_forecast", "AmountTRY", "Currency", "Q2 rolling forecast with closed actuals", "Month-account-cost center", "Forecast engine", "FP&A", "18 months"],
  ["monthly_pnl", "RevenueTRY", "Currency", "Revenue accounts aggregated by month and version", "Month-version", "Reporting layer", "FP&A", "TRY"],
  ["monthly_pnl", "GrossProfitTRY", "Currency", "Revenue less COGS", "Month-version", "Reporting layer", "FP&A", null],
  ["monthly_pnl", "EBITDATRY", "Currency", "Gross profit less operating expense", "Month-version", "Reporting layer", "FP&A", null],
  ["monthly_pnl", "NetIncomeTRY", "Currency", "EBT less income tax", "Month-version", "Reporting layer", "FP&A", null],
  ["fact_working_capital", "DSO", "Days", "Accounts receivable divided by revenue per day", "Month-version", "Planning model", "Treasury", null],
  ["fact_working_capital", "DIO", "Days", "Inventory divided by COGS per day", "Month-version", "Planning model", "Supply Chain", null],
  ["fact_working_capital", "DPO", "Days", "Accounts payable divided by COGS per day", "Month-version", "Planning model", "Procurement", null],
  ["fact_cash_flow", "EndingCashTRY", "Currency", "Beginning cash plus net cash flow", "Month-version", "Cash model", "Treasury", null],
  ["fact_headcount", "FTE", "Count", "Full-time equivalent positions", "Month-cost center-version", "Workforce plan", "People", null],
  ["fact_capex", "CapexSpendTRY", "Currency", "Project spend recognized in month", "Month-project-version", "Capex schedule", "Finance", null],
  ["fact_capex", "RemainingNBVTRY", "Currency", "Asset cost less accumulated depreciation", "Month-project-version", "Capex schedule", "Finance", null],
  ["forecast_model_comparison", "WAPE", "Percentage", "Absolute forecast error divided by actual revenue", "Business unit-model", "Backtest", "Analytics", "Lower is better"],
  ["forecast_model_comparison", "Bias", "Percentage", "Net forecast error divided by actual revenue", "Business unit-model", "Backtest", "Analytics", "Positive = over-forecast"],
  ["scenario_summary", "MinimumCashTRY", "Currency", "Minimum FY2026 cash balance by scenario", "Scenario", "Scenario engine", "Treasury", null],
  ["scenario_summary", "CashConversionCycleDays", "Days", "Average DSO plus DIO less DPO", "Scenario", "Scenario engine", "FP&A", null],
  ["risk_summary", "Probability EBITDA Below Budget", "Percentage", "Share of Monte Carlo runs below budget EBITDA", "Portfolio", "5,000 simulations", "FP&A", null],
  ["validation_report", "all_passed", "Boolean", "All automated data and business-rule checks passed", "Project", "Validation", "Analytics", "17 controls"],
];
styleDataTable(dictionary, "A5:H25", "A5:H5", { fontSize: 8 });
dictionary.getRange("A5:H25").format.wrapText = true;
setWidths(dictionary, {
  "A:A": 27,
  "B:B": 28,
  "C:C": 14,
  "D:D": 48,
  "E:E": 25,
  "F:G": 22,
  "H:H": 23,
});

// Sources
titleBand(
  sources,
  "Sources, Versioning & Data Notice",
  "Lineage, ownership and portfolio disclosure",
  "I",
);
sources.getRange("A5:I16").values = [
  ["Item", "Location", "Purpose", "Type", "Period / As-of", "Currency", "Owner", "Disclosure", "Refresh"],
  ["Actual ledger", "Data/fact_actuals.csv", "Historical P&L actuals", "Generated", "Jan 2023 - Jun 2026", "TRY", "Controllership", "Synthetic", "Pipeline"],
  ["FY2026 budget", "Data/fact_budget.csv", "Approved baseline", "Generated", "FY2026", "TRY", "FP&A", "Synthetic", "Pipeline"],
  ["Rolling forecast", "Data/fact_forecast.csv", "Q2 outlook", "Model output", "Jan 2026 - Jun 2027", "TRY", "FP&A", "Synthetic", "Pipeline"],
  ["Working capital", "Data/fact_working_capital.csv", "AR, inventory and AP", "Model output", "2023-2027", "TRY / days", "Treasury", "Synthetic", "Pipeline"],
  ["Cash flow", "Data/fact_cash_flow.csv", "Liquidity outlook", "Model output", "2023-2027", "TRY", "Treasury", "Synthetic", "Pipeline"],
  ["Headcount", "Data/fact_headcount.csv", "FTE and payroll plan", "Generated", "2023-2027", "TRY / FTE", "People", "Synthetic", "Pipeline"],
  ["Capex", "Data/fact_capex.csv", "Spend and depreciation", "Generated", "2023-2027", "TRY", "Finance", "Synthetic", "Pipeline"],
  ["Forecast models", "Data/forecast_model_comparison.csv", "Model governance", "Backtest", "H1 2026", "TRY / %", "Analytics", "Synthetic", "Pipeline"],
  ["Scenario engine", "Data/scenario_summary.csv", "Decision cases", "Model output", "FY2026", "TRY / days", "FP&A", "Synthetic", "Pipeline"],
  ["Monte Carlo", "Data/monte_carlo_simulations.csv", "Risk distribution", "5,000 runs", "FY2026", "TRY / %", "FP&A", "Synthetic", "Pipeline"],
  ["Author", "Murat Miraç Gedik", "Portfolio attribution", "Metadata", "July 2026", null, "Author", "No real company records", "Versioned"],
];
styleDataTable(sources, "A5:I16", "A5:I5", { fontSize: 8 });
sources.getRange("A5:I16").format.wrapText = true;
setWidths(sources, {
  "A:A": 24,
  "B:B": 38,
  "C:C": 34,
  "D:I": 20,
});

// Raw sheet widths and formats
scenarioData.getRange("B6:I9").format.numberFormat = FMT_TRY;
scenarioData.getRange("F6:G9").format.numberFormat = FMT_PCT;
scenarioData.getRange("J6:J9").format.numberFormat = FMT_DAYS;
setWidths(scenarioData, { "A:A": 16, "B:I": 19, "J:J": 20, "K:K": 14 });
cashData.getRange("C6:H77").format.numberFormat = FMT_TRY;
setWidths(cashData, { "A:B": 16, "C:H": 20 });
wcData.getRange("C6:F77").format.numberFormat = FMT_DAYS;
wcData.getRange("G6:K77").format.numberFormat = FMT_TRY;
setWidths(wcData, { "A:B": 16, "C:F": 15, "G:K": 20 });
departmentData.getRange("C6:M437").format.numberFormat = FMT_TRY;
departmentData.getRange("N6:P437").format.numberFormat = FMT_PCT;
setWidths(departmentData, { "A:A": 14, "B:B": 26, "C:P": 18, "Q:S": 15 });
businessUnitData.getRange("C6:M365").format.numberFormat = FMT_TRY;
businessUnitData.getRange("N6:P365").format.numberFormat = FMT_PCT;
setWidths(businessUnitData, { "A:A": 14, "B:B": 26, "C:P": 18, "Q:S": 15 });
headcountData.getRange("D6:F437").format.numberFormat = FMT_NUM;
headcountData.getRange("G6:H437").format.numberFormat = FMT_TRY_FULL;
setWidths(headcountData, { "A:B": 15, "C:C": 27, "D:F": 13, "G:H": 20 });
capexData.getRange("D6:F755").format.numberFormat = FMT_TRY_FULL;
setWidths(capexData, { "A:B": 15, "C:C": 27, "D:F": 21 });
modelData.getRange("C6:D21").format.numberFormat = FMT_TRY_FULL;
modelData.getRange("E6:G21").format.numberFormat = FMT_PCT;
setWidths(modelData, { "A:A": 28, "B:B": 30, "C:G": 17, "H:H": 15 });
varianceData.getRange("F6:H35").format.numberFormat = FMT_TRY;
varianceData.getRange("I6:I35").format.numberFormat = FMT_PCT;
setWidths(varianceData, { "A:A": 31, "B:B": 24, "C:C": 14, "D:E": 22, "F:H": 19, "I:I": 15, "J:K": 16 });

// Add formula-backed chart helpers that avoid unrelated series.
dashboardData.getRange("L5:N17").values = [
  ["Month", "Budget EBITDA", "Forecast EBITDA"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
    null,
  ]),
];
styleDataTable(dashboardData, "L5:N17", "L5:N5");
for (let row = 6; row <= 17; row += 1) {
  dashboardData.getRange(`M${row}`).formulas = [[`=D${row}`]];
  dashboardData.getRange(`N${row}`).formulas = [[`=E${row}`]];
}
dashboardData.getRange("M6:N17").format.numberFormat = FMT_TRY;
ebitdaChart.setData(dashboardData.getRange("L5:N17"));

cashFlowSheet.getRange("J5:K17").values = [
  ["Month", "Ending Cash"],
  ...Array.from({ length: 12 }, (_, index) => [
    `2026-${String(index + 1).padStart(2, "0")}-01`,
    null,
  ]),
];
styleDataTable(cashFlowSheet, "J5:K17", "J5:K5");
for (let row = 6; row <= 17; row += 1) {
  cashFlowSheet.getRange(`K${row}`).formulas = [[`=G${row}`]];
}
cashFlowSheet.getRange("K6:K17").format.numberFormat = FMT_TRY;
liquidityChart.setData(cashFlowSheet.getRange("J5:K17"));

for (const sheet of [
  cover,
  dashboard,
  scenarioControl,
  incomeStatement,
  budgetVsActual,
  rollingForecast,
  revenueDrivers,
  opexPlanning,
  cashFlowSheet,
  workingCapitalSheet,
  headcountPlan,
  capexPlan,
  departmentBudget,
  businessUnitSheet,
  forecastAccuracy,
  riskAnalysis,
  assumptions,
  checks,
  dictionary,
  sources,
  dashboardData,
]) {
  sheet.getUsedRange()?.format?.autofitRows?.();
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const outputPath = path.join(
  outputDir,
  "Integrated_FP&A_Budgeting_Forecasting_Scenario_Planning_Model.xlsx",
);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

const userFacingSheets = [
  "Cover",
  "Executive Dashboard",
  "Scenario Control",
  "Income Statement",
  "Budget vs Actual",
  "Rolling Forecast",
  "Revenue Drivers",
  "Opex Planning",
  "Cash Flow",
  "Working Capital",
  "Headcount Plan",
  "Capex Plan",
  "Department Budget",
  "Business Unit",
  "Forecast Accuracy",
  "Risk Analysis",
  "Assumptions",
  "Checks",
  "Data Dictionary",
  "Sources",
  "Dashboard Data",
  "P&L Data",
  "Scenario Data",
  "Cash Data",
  "WC Data",
  "Department Data",
  "BU Data",
  "Headcount Data",
  "Capex Data",
  "Model Data",
  "Variance Data",
];

for (const sheetName of userFacingSheets) {
  const important = [
    "Executive Dashboard",
    "Scenario Control",
    "Income Statement",
    "Budget vs Actual",
    "Rolling Forecast",
  ].includes(sheetName);
  const raw = sheetName.endsWith("Data") && sheetName !== "Dashboard Data";
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: important ? 1.25 : raw ? 0.55 : 0.8,
    format: "png",
  });
  const safeName = sheetName.toLowerCase().replaceAll("&", "and").replaceAll(" ", "-");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const inspect = await workbook.inspect({
  kind: "workbook,sheet,formula,drawing",
  maxChars: 20000,
  tableMaxRows: 8,
  tableMaxCols: 8,
  options: { maxResults: 240 },
});
await fs.writeFile(
  path.join(outputDir, "workbook_inspection.json"),
  JSON.stringify(inspect, null, 2),
  "utf8",
);

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  maxChars: 10000,
});
await fs.writeFile(
  path.join(outputDir, "formula_error_scan.json"),
  JSON.stringify(errorScan, null, 2),
  "utf8",
);

console.log(outputPath);
