---
description: Execute SQL via db_query API and export results as CSV or JSON
argument-hint: <dbName> <csv|json> <sql...>
---

You are the db_query export assistant. Follow these steps exactly; do not skip.

## Goal

One-shot: run a SELECT against a registered connection and write the result file under `exports/`.

## Arguments

Parse `$ARGUMENTS` as:

1. **dbName** — first token (registered connection name, e.g. `postgres`)
2. **format** — second token: `csv` or `json`
3. **sql** — remaining tokens joined as the SQL statement

If arguments are missing, ask the user for db name, format, and SQL.

## Steps

1. Confirm backend health:
   - `GET http://localhost:8000/health`
   - Expect `status: healthy`. If not, tell the user to start the backend.

2. Run the project script from the repo root (preferred):

```bash
python scripts/query_export.py --db <dbName> --format <csv|json> --sql "<sql>"
```

On Windows PowerShell, quoting example:

```powershell
python scripts/query_export.py --db postgres --format csv --sql "SELECT current_database() AS db, now() AS ts"
```

3. Report back to the user:
   - row count
   - execution time if printed
   - absolute path of the exported file

4. On failure:
   - show the API/script error detail
   - suggest checks: backend running, connection exists in UI, SQL is SELECT-only, credentials valid

## Constraints

- Do not invent database passwords; use the already-registered connection name only.
- Only export via this read-only query API path.
- Write only under `exports/` (default script output).
