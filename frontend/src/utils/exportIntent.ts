/** Detect export-related intent from natural language prompts. */

import type { ExportFormat } from "./exportResults";

export type NlIntent = "query" | "export" | "query_and_export";

export interface ParsedNlIntent {
  intent: NlIntent;
  format: ExportFormat | null;
  cleanedPrompt: string;
}

const EXPORT_RE = /导出|下載|下载|export|download/i;
const QUERY_HINT_RE =
  /查询|查一下|列出|显示|統計|统计|show|select|list|find|count|查询一下/i;
const CSV_RE = /\bcsv\b|逗号分隔|表格文件/i;
const JSON_RE = /\bjson\b|对象数组/i;

function detectFormat(prompt: string): ExportFormat | null {
  const hasCsv = CSV_RE.test(prompt);
  const hasJson = JSON_RE.test(prompt);
  if (hasCsv && !hasJson) return "csv";
  if (hasJson && !hasCsv) return "json";
  return null;
}

/**
 * Classify user NL input for query / export / query+export.
 */
export function parseExportIntent(prompt: string): ParsedNlIntent {
  const text = prompt.trim();
  const wantsExport = EXPORT_RE.test(text);
  const format = detectFormat(text);
  const hasQueryHint = QUERY_HINT_RE.test(text);

  if (wantsExport && hasQueryHint) {
    return {
      intent: "query_and_export",
      format,
      cleanedPrompt: text
        .replace(EXPORT_RE, " ")
        .replace(CSV_RE, " ")
        .replace(JSON_RE, " ")
        .replace(/为|成|成爲|成为|as|to|成文件|文件/gi, " ")
        .replace(/\s+/g, " ")
        .trim(),
    };
  }

  if (wantsExport) {
    return { intent: "export", format, cleanedPrompt: text };
  }

  return { intent: "query", format: null, cleanedPrompt: text };
}

export type ExportPromptPreference = "ask" | "never";

const PREF_KEY = "db_query.exportPrompt";

export function getExportPromptPreference(): ExportPromptPreference {
  const value = localStorage.getItem(PREF_KEY);
  return value === "never" ? "never" : "ask";
}

export function setExportPromptPreference(value: ExportPromptPreference): void {
  localStorage.setItem(PREF_KEY, value);
}
