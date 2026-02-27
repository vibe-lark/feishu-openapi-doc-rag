---
name: feishu-openapi-doc-rag
description: "Use when you need offline-first retrieval and extraction of Feishu Open Platform OpenAPI documentation from a periodically updated JSON index (CDN) and a local SQLite index, including: API lookup from natural-language queries, core request block extraction, dependency doc chaining, and daily diffing for updates."
---

# Feishu Openapi Doc Rag

## Overview

Use the local `openapi_doc_cli` index and Unix-like commands to reliably retrieve Feishu Open Platform docs, extract the minimal “core API blocks” needed to write code, and output a reproducible evidence trail (ids/urls/commands).

## Quick Start

Assume an index already exists at `~/.openapi-doc-cli/` or another `--base-dir`.

This skill bundle includes a vendored copy of `openapi_doc_cli` under `vendor/openapi_doc_cli/` so it can run standalone (no extra repo needed).

Build/update index (offline, local JSON):

```bash
PYTHONPATH=vendor python3 -m openapi_doc_cli build --input /path/to/larkopenapidoc.json
```

Build/update index from CDN (online):

```bash
python3 scripts/bootstrap_index_from_cdn.py
```

Search:

```bash
PYTHONPATH=vendor python3 -m openapi_doc_cli grep "多维表格 高级权限"
```

Read a specific doc:

```bash
PYTHONPATH=vendor python3 -m openapi_doc_cli show <id> --head 120
```

## Workflow (Always Reproducible)

### Step 1: Normalize the user query

Use `grep` first; it auto-tokenizes Chinese queries (e.g. “多维表格写入” -> “多维表格” + “写入”).

Prefer these patterns:
- `"产品名 动作"` (e.g. `"多维表格 权限"`, `"日历 创建日程"`, `"消息 语音"`)
- `"资源名 动作"` (e.g. `"record create"`, `"msg_type audio"`)

### Step 2: Get 10–30 candidates via CLI (evidence trail)

```bash
PYTHONPATH=vendor python3 -m openapi_doc_cli grep "<query>" --limit 20
```

### Step 3: Verify each candidate by reading the “Request” section

For each candidate `id`, read the head and confirm it contains:
- `HTTP URL`
- `HTTP Method`
- required path/query params

```bash
PYTHONPATH=vendor python3 -m openapi_doc_cli show <id> --head 120
```

### Step 4: Extract “core API blocks” for model/tool use

When integrating into OpenClaw-like systems, output only:
- doc `id`, `url`, `directory_path`
- HTTP URL + method
- required headers
- required query params and path params
- minimal example body schema

If needed, use additional `show --head` passes (increasing head) until the request block is fully captured.

### Step 5: Identify dependencies (multi-doc flows)

Use the doc’s own text as source of truth:
- look for “前提条件/注意事项/你可以调用…接口/需先…”
- then retrieve the referenced docs by URL keyword (e.g. `.../app/update`, `.../file/create`)

### Step 6: Produce output in two parts

1) **Search log**: the exact CLI commands run + top hits (ids/urls)
2) **Final**: a numbered API list (ordered) + each doc’s core blocks

## Resources

This skill ships with `openapi_doc_cli` vendored; it still needs a built SQLite index (`index.sqlite`) to query.

## Resources (optional)

Create only the resource directories this skill actually needs. Delete this section if no resources are required.

### scripts/
Executable code (Python/Bash/etc.) that can be run directly to perform specific operations.

**Examples from other skills:**
- PDF skill: `fill_fillable_fields.py`, `extract_form_field_info.py` - utilities for PDF manipulation
- DOCX skill: `document.py`, `utilities.py` - Python modules for document processing

**Appropriate for:** Python scripts, shell scripts, or any executable code that performs automation, data processing, or specific operations.

**Note:** Scripts may be executed without loading into context, but can still be read by Codex for patching or environment adjustments.

### references/
Documentation and reference material intended to be loaded into context to inform Codex's process and thinking.

**Examples from other skills:**
- Product management: `communication.md`, `context_building.md` - detailed workflow guides
- BigQuery: API reference documentation and query examples
- Finance: Schema documentation, company policies

**Appropriate for:** In-depth documentation, API references, database schemas, comprehensive guides, or any detailed information that Codex should reference while working.

### assets/
Files not intended to be loaded into context, but rather used within the output Codex produces.

**Examples from other skills:**
- Brand styling: PowerPoint template files (.pptx), logo files
- Frontend builder: HTML/React boilerplate project directories
- Typography: Font files (.ttf, .woff2)

**Appropriate for:** Templates, boilerplate code, document templates, images, icons, fonts, or any files meant to be copied or used in the final output.

---

**Not every skill requires all three types of resources.**
