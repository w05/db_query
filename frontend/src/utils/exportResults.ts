/** Query result export helpers (CSV / JSON). */

export interface ExportableResult {
  columns: Array<{ name: string }>;
  rows: Array<Record<string, unknown>>;
  rowCount: number;
}

export type ExportFormat = "csv" | "json";

export const LARGE_EXPORT_THRESHOLD = 10_000;

export function shouldWarnLarge(rowCount: number): boolean {
  return rowCount > LARGE_EXPORT_THRESHOLD;
}

export function buildFilename(dbName: string, format: ExportFormat): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
  return `${dbName}_${timestamp}.${format}`;
}

function escapeCsvValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  const stringValue = String(value);
  if (
    stringValue.includes(",") ||
    stringValue.includes('"') ||
    stringValue.includes("\n")
  ) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

export function buildCsvContent(result: ExportableResult, withBom = true): string {
  const headers = result.columns.map((col) => col.name);
  const lines = [headers.join(",")];

  for (const row of result.rows) {
    lines.push(headers.map((header) => escapeCsvValue(row[header])).join(","));
  }

  const body = lines.join("\n");
  // UTF-8 BOM helps Excel open Chinese correctly
  return withBom ? `\uFEFF${body}` : body;
}

export function buildJsonContent(result: ExportableResult): string {
  return JSON.stringify(result.rows, null, 2);
}

function triggerDownload(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function downloadCsv(
  result: ExportableResult,
  dbName: string,
  withBom = true
): string {
  const filename = buildFilename(dbName, "csv");
  triggerDownload(
    buildCsvContent(result, withBom),
    filename,
    "text/csv;charset=utf-8;"
  );
  return filename;
}

export function downloadJson(result: ExportableResult, dbName: string): string {
  const filename = buildFilename(dbName, "json");
  triggerDownload(
    buildJsonContent(result),
    filename,
    "application/json;charset=utf-8;"
  );
  return filename;
}
