import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


const projectRoot = process.cwd();
const dataDir = path.join(projectRoot, "data_clean", "value_type");
const outputPath = path.join(projectRoot, "output", "mainlayer_onset_differentiation.xlsx");
const previewDir = path.join(projectRoot, "tmp", "mainlayer_onset_workbook_preview");

const files = {
  summary: "mainlayer_onset_summary.csv",
  slotSummary: "mainlayer_onset_slot_summary.csv",
  structure: "mainlayer_onset_structure_patterns.csv",
  chains: "mainlayer_onset_chain_patterns.csv",
  slotValues: "mainlayer_onset_slot_value_positions.csv",
  points: "point_mainlayer_onset_chains.csv",
};

const fontFamily = "Arial";
const colors = {
  header: "#1F4E78",
  subheader: "#D9EAF7",
  rule: "#9EADBA",
  text: "#222222",
  note: "#5A6570",
  white: "#FFFFFF",
};

const headerLabels = {
  onset_class: "声母组",
  point_id: "方言点编号",
  point_name: "方言点",
  point_count: "方言点数",
  merged_point_count: "合流点数",
  merged_point_share: "合流占比",
  fully_distinct_point_count: "全对立点数",
  fully_distinct_point_share: "全对立占比",
  leapfrog_point_count: "越级点数",
  leapfrog_point_share: "越级占比",
  S0_equals_S1_count: "S0=S1 点数",
  S0_equals_S1_share: "S0=S1 占比",
  S1_equals_S2_count: "S1=S2 点数",
  S1_equals_S2_share: "S1=S2 占比",
  S2_equals_S3_count: "S2=S3 点数",
  S2_equals_S3_share: "S2=S3 占比",
  structure_pattern_count: "结构模式数",
  top_structure_pattern: "最高频结构模式",
  top_structure_count: "最高频结构点数",
  top_structure_share: "最高频结构占比",
  exact_chain_count: "精确音值链数",
  top_exact_chain: "最高频音值链",
  top_exact_chain_count: "最高频音值链点数",
  top_exact_chain_share: "最高频音值链占比",
  slot_modal_values: "各槽最高频音值",
  slot: "槽位",
  rhyme_group: "韵类",
  slot_initial: "槽位初始音",
  unique_value_count: "音值类型数",
  top_value: "最高频音值",
  top_value_count: "最高频音值点数",
  top_value_share: "最高频音值占比",
  second_value: "次高频音值",
  second_value_count: "次高频音值点数",
  second_value_share: "次高频音值占比",
  diphthong_count: "复元音点数",
  diphthong_share: "复元音占比",
  unplaced_count: "未定位点数",
  unplaced_share: "未定位占比",
  rank_within_onset: "声母组内排名",
  rank_within_onset_slot: "声母槽位内排名",
  level_1: "一级分类",
  level_2: "二级分类",
  structure_pattern: "结构模式",
  is_leapfrog: "是否越级",
  exact_chain: "S0→S1→S2→S3 音值链",
  S0: "S0 佳皆",
  S1: "S1 麻",
  S2: "S2 歌戈",
  S3: "S3 模",
  share_within_onset: "声母组内占比",
  share_within_onset_slot: "声母槽位内占比",
  point_list: "方言点列表",
  mainlayer_value: "主体层音值",
  vowel_components: "元音组成",
  is_diphthong: "是否复元音",
  plot_x_front_to_back: "舌位横轴：前→后",
  plot_y_close_to_open: "舌位纵轴：高→低",
  coordinate_status: "坐标状态",
  slot_distinct_count: "槽位音值数",
  unplaced_values: "未定位音值",
  一级分类: "一级分类",
  二级分类: "二级分类",
  "三级分类(详细模式)": "三级分类（详细模式）",
};


function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  const source = text.replace(/^\uFEFF/, "");
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (quoted) {
      if (char === '"' && source[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows.filter((item) => item.length > 1 || item[0] !== "");
}


function coerceValue(header, value) {
  if (value === "") return null;
  if (header.startsWith("is_") || header === "是否越级") {
    return String(value).toLowerCase() === "true" ? "是" : "否";
  }
  if (header === "coordinate_status") {
    return value === "placed" ? "已定位" : "待确认";
  }
  const numeric =
    header.includes("count") ||
    header.includes("share") ||
    header.includes("rank") ||
    header === "slot_distinct_count" ||
    header.startsWith("plot_x_") ||
    header.startsWith("plot_y_");
  if (numeric && Number.isFinite(Number(value))) return Number(value);
  return value;
}


function displayHeaders(headers) {
  return headers.map((header) => headerLabels[header] ?? header);
}


function selectColumns(data, keys) {
  const indexes = keys.map((key) => data.headers.indexOf(key));
  if (indexes.some((index) => index < 0)) {
    throw new Error(`Missing summary column: ${keys[indexes.findIndex((index) => index < 0)]}`);
  }
  return {
    headers: keys,
    rows: data.rows.map((row) => indexes.map((index) => row[index])),
  };
}


async function readCsv(name) {
  const text = await fs.readFile(path.join(dataDir, files[name]), "utf8");
  const matrix = parseCsv(text);
  const headers = matrix[0];
  const rows = matrix.slice(1).map((row) =>
    headers.map((header, index) => coerceValue(header, row[index] ?? "")),
  );
  return { headers, rows };
}


function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}


function columnWidth(header) {
  if (["point_list"].includes(header)) return 56;
  if (["slot_modal_values"].includes(header)) return 48;
  if (["top_exact_chain", "exact_chain"].includes(header)) return 25;
  if (["coordinate_note", "unplaced_values"].includes(header)) return 28;
  if (["point_name"].includes(header)) return 18;
  if (["point_id", "onset_class", "slot", "S0", "S1", "S2", "S3"].includes(header)) return 12;
  if (header.includes("pattern")) return 24;
  if (header.includes("share")) return 14;
  if (header.includes("count") || header.includes("rank")) return 13;
  if (header.startsWith("plot_")) return 17;
  return Math.min(22, Math.max(12, header.length + 2));
}


function styleHeader(range) {
  range.format = {
    fill: colors.header,
    font: { name: fontFamily, size: 10, bold: true, color: colors.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: {
      insideVertical: { style: "thin", color: colors.white },
      bottom: { style: "thin", color: colors.header },
    },
  };
  range.format.rowHeight = 30;
}


function applyFormats(sheet, headers, startRow, rowCount) {
  const lastRow = startRow + rowCount;
  const lastCol = columnName(headers.length - 1);
  const allRange = sheet.getRange(`A${startRow}:${lastCol}${lastRow}`);
  allRange.format.font = { name: fontFamily, size: 10, color: colors.text };
  allRange.format.verticalAlignment = "center";
  allRange.format.wrapText = false;
  allRange.format.rowHeight = 20;

  headers.forEach((header, index) => {
    const col = columnName(index);
    sheet.getRange(`${col}:${col}`).format.columnWidth = columnWidth(header);
    if (header === "point_list") {
      sheet.getRange(`${col}${startRow + 1}:${col}${lastRow}`).format.wrapText = true;
    }
    if (header.includes("share")) {
      sheet.getRange(`${col}${startRow + 1}:${col}${lastRow}`).format.numberFormat = "0.0%";
    } else if (header.startsWith("plot_x_") || header.startsWith("plot_y_")) {
      sheet.getRange(`${col}${startRow + 1}:${col}${lastRow}`).format.numberFormat = "0.00";
    } else if (header.includes("count") || header.includes("rank") || header === "slot_distinct_count") {
      sheet.getRange(`${col}${startRow + 1}:${col}${lastRow}`).format.numberFormat = "0";
    }
  });
}


function addFlatSheet(workbook, name, data, tableName) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const matrix = [displayHeaders(data.headers), ...data.rows];
  sheet.getRange("A1").write(matrix);
  const lastCol = columnName(data.headers.length - 1);
  const lastRow = matrix.length;
  styleHeader(sheet.getRange(`A1:${lastCol}1`));
  applyFormats(sheet, data.headers, 1, data.rows.length);
  const table = sheet.tables.add(`A1:${lastCol}${lastRow}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showBandedColumns = false;
  table.showFilterButton = true;
  sheet.freezePanes.freezeRows(1);
  if (data.headers.includes("point_id")) sheet.freezePanes.freezeColumns(2);
  return sheet;
}


const data = {};
for (const name of Object.keys(files)) data[name] = await readCsv(name);

const workbook = Workbook.create();

const summarySheet = workbook.worksheets.add("声母总览");
summarySheet.showGridLines = false;
summarySheet.getRange("A1").values = [["按声母条件的主体层分化"]];
summarySheet.getRange("A1").format.font = { name: fontFamily, size: 16, bold: true, color: colors.text };
summarySheet.getRange("A2").values = [["82 个方言点；K、M、P、TS、Ø 分别统计，不跨声母取众数。S0=佳皆，S1=麻，S2=歌戈，S3=模。"]];
summarySheet.getRange("A2").format.font = { name: fontFamily, size: 10, italic: true, color: colors.note };
summarySheet.getRange("A3:J3").format.borders = { bottom: { style: "thin", color: colors.rule } };

const structureSummary = selectColumns(data.summary, [
  "onset_class",
  "point_count",
  "merged_point_share",
  "fully_distinct_point_share",
  "S0_equals_S1_share",
  "S1_equals_S2_share",
  "S2_equals_S3_share",
  "top_structure_pattern",
  "top_structure_share",
  "leapfrog_point_count",
]);
summarySheet.getRange("A4").values = [["结构关系"]];
summarySheet.getRange("A4:J4").format = {
  fill: colors.subheader,
  font: { name: fontFamily, size: 10, bold: true, color: colors.text },
  borders: { preset: "outside", style: "thin", color: colors.rule },
};
const structureMatrix = [displayHeaders(structureSummary.headers), ...structureSummary.rows];
summarySheet.getRange("A5").write(structureMatrix);
styleHeader(summarySheet.getRange("A5:J5"));
applyFormats(summarySheet, structureSummary.headers, 5, structureSummary.rows.length);
const structureSummaryTable = summarySheet.tables.add("A5:J10", true, "OnsetStructureSummaryTable");
structureSummaryTable.style = "TableStyleMedium2";
structureSummaryTable.showFilterButton = true;

const chainSummary = selectColumns(data.summary, [
  "onset_class",
  "exact_chain_count",
  "top_exact_chain",
  "top_exact_chain_count",
  "top_exact_chain_share",
  "slot_modal_values",
]);
summarySheet.getRange("A12").values = [["精确音值链"]];
summarySheet.getRange("A12:F12").format = {
  fill: colors.subheader,
  font: { name: fontFamily, size: 10, bold: true, color: colors.text },
  borders: { preset: "outside", style: "thin", color: colors.rule },
};
const chainMatrix = [displayHeaders(chainSummary.headers), ...chainSummary.rows];
summarySheet.getRange("A13").write(chainMatrix);
styleHeader(summarySheet.getRange("A13:F13"));
applyFormats(summarySheet, chainSummary.headers, 13, chainSummary.rows.length);
const chainSummaryTable = summarySheet.tables.add("A13:F18", true, "OnsetChainSummaryTable");
chainSummaryTable.style = "TableStyleMedium2";
chainSummaryTable.showFilterButton = true;
summarySheet.freezePanes.freezeRows(5);
summarySheet.freezePanes.freezeColumns(1);

addFlatSheet(workbook, "分槽概览", data.slotSummary, "OnsetSlotSummaryTable");
addFlatSheet(
  workbook,
  "结构模式",
  selectColumns(data.structure, [
    "onset_class",
    "rank_within_onset",
    "level_1",
    "level_2",
    "structure_pattern",
    "is_leapfrog",
    "point_count",
    "share_within_onset",
  ]),
  "OnsetStructureTable",
);
addFlatSheet(
  workbook,
  "音值链",
  selectColumns(data.chains, [
    "onset_class",
    "rank_within_onset",
    "exact_chain",
    "S0",
    "S1",
    "S2",
    "S3",
    "structure_pattern",
    "point_count",
    "share_within_onset",
  ]),
  "OnsetChainTable",
);
addFlatSheet(
  workbook,
  "分槽音值",
  selectColumns(data.slotValues, [
    "onset_class",
    "slot",
    "rhyme_group",
    "slot_initial",
    "rank_within_onset_slot",
    "mainlayer_value",
    "vowel_components",
    "is_diphthong",
    "plot_x_front_to_back",
    "plot_y_close_to_open",
    "coordinate_status",
    "point_count",
    "share_within_onset_slot",
  ]),
  "OnsetSlotValueTable",
);
addFlatSheet(workbook, "点位明细", data.points, "PointOnsetChainTable");

const methodSheet = workbook.worksheets.add("方法说明");
methodSheet.showGridLines = false;
const methodRows = [
  ["项目", "说明"],
  ["分析单位", "方言点 × 声母类别。每个声母条件独立保留一条 S0→S1→S2→S3 主体层音值链。"],
  ["声母类别", "K、M、P、TS、Ø；沿用 data_raw/mainlayer_merge.csv 的 onset_class。"],
  ["结构模式", "直接采用 mainlayer_merge.csv 的‘三级分类(详细模式)’；全对立、S0=S1、S1=S2、S2=S3、S0=S1且S2=S3、S1=S2=S3、越级合流分别计数。"],
  ["音值链模式", "同一声母内，按 S0、S1、S2、S3 的实际主体层 IPA 串精确分组；不把 a、ᴀ、ɑ 合并，也不跨声母取众数。"],
  ["IPA 坐标", "复元音采用组成元音舌位坐标的算术中点；ɷ 暂置于 o–u 之间，ᴀ 暂置于 a–ɑ 之间，ᴇ 暂置于 e–ɛ 之间。"],
  ["未定位符号", "v、ɥ、ʮ 保留在明细中，不强行放入常规元音舌位图。"],
  ["数据来源", "data_raw/mainlayer_merge.csv；410 行，82 个方言点 × 5 类声母。"],
  ["生成日期", "2026-09-05"],
];
methodSheet.getRange("A1").write(methodRows);
styleHeader(methodSheet.getRange("A1:B1"));
methodSheet.getRange("A1:B9").format.font = { name: fontFamily, size: 10, color: colors.text };
methodSheet.getRange("A1:B9").format.wrapText = true;
methodSheet.getRange("A1:B9").format.verticalAlignment = "top";
methodSheet.getRange("A:A").format.columnWidth = 18;
methodSheet.getRange("B:B").format.columnWidth = 86;
methodSheet.getRange("A2:A9").format.fill = colors.subheader;
methodSheet.getRange("A2:A9").format.font = { name: fontFamily, size: 10, bold: true, color: colors.text };
methodSheet.freezePanes.freezeRows(1);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["声母总览", "分槽概览", "结构模式", "音值链", "分槽音值", "点位明细", "方法说明"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  const previewBytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), previewBytes);
}

const inspection = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 8,
  tableMaxCols: 10,
  tableMaxCellChars: 100,
});
console.log(inspection.ndjson);

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);
console.log(`saved ${outputPath}`);
