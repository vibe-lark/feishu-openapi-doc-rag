# OpenAPI Doc CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Build an offline-first CLI that syncs a cloud-hosted `larkopenapidoc.json`, indexes it locally, and supports fast `search/tree/show/open` over the Open Platform docs.

**Architecture:** Use a local SQLite database (with FTS5 where available) as the query engine. `update` is the only network-dependent command: it downloads the JSON to a temp file, builds a new index DB, then atomically swaps it in. All read commands work fully offline and remain consistent during updates.

**Tech Stack:** Python 3, SQLite (FTS5 optional), `argparse` or `typer` (choose later), streaming JSON parsing (choose `ijson` if dependency is acceptable; otherwise fallback to full `json.load` for current 33MB input).

---

## CLI Requirements (MVP)

### Commands

- `openapi-doc update`
  - Downloads remote JSON (supports `--url`, `--force`).
  - Uses HTTP caching headers if available (`ETag`, `Last-Modified`), otherwise uses content hash/version file.
  - Builds/updates local DB and swaps atomically.
  - Prints: doc count, update time range, index size, remote version signal.

- `openapi-doc search <query>`
  - Fast full-text search across metadata + content.
  - Options: `--limit`, `--offset`, `--fields`, `--json`.
  - Output includes: title-ish display (directory path), url, short snippet (optional).

- `openapi-doc tree [path...]`
  - Prints directory hierarchy, supports `--depth`, `--counts`, `--json`.
  - `path...` filters tree to a subdirectory (exact match on directory segments).

- `openapi-doc show <id|url|path>`
  - Shows metadata and optionally first N lines of content (`--head N`, `--no-content` default true).

- `openapi-doc open <id|url|path>`
  - Opens in browser when possible; always can print URL via `--print`.

### Non-goals (for MVP)

- SDK/code generation.
- Running API calls.
- Multi-source merging, auth, or per-tenant content.

---

## Data Model (Local Index)

### Files on disk

Under `~/.openapi-doc-cli/`:
- `index.sqlite` (active)
- `index.new.sqlite` (build target during update)
- `state.json` (remote url, etag/last_modified, last_successful_update_at, counts)
- `download.json.tmp` (optional temp download)

### SQLite schema (suggested)

Table `docs`:
- `id TEXT PRIMARY KEY`
- `origin_id TEXT`
- `url TEXT UNIQUE`
- `directory_json TEXT` (JSON array of strings)
- `directory_path TEXT` (joined with ` / ` for display)
- `pathnames_json TEXT`
- `pathnames_path TEXT` (joined with `/`)
- `original_path TEXT NULL`
- `update_time_ms INTEGER`
- `content TEXT` (the original `value`)

Indexes:
- `CREATE INDEX docs_update_time ON docs(update_time_ms);`
- `CREATE INDEX docs_directory_path ON docs(directory_path);`

FTS (optional, if SQLite has FTS5):
- `docs_fts(directory_path, pathnames_path, original_path, url, content, content='docs', content_rowid='rowid')`
- Triggers to keep in sync, or simpler: build FTS table as external content during indexing.

If FTS5 is not available:
- Fallback search: tokenize query, use `LIKE` on `directory_path`/`url` and a limited scan on `content` (warn about performance).

---

## Update Pipeline (Cloud JSON → Local DB)

1) Resolve remote URL (config, env, `--url`).
2) Issue conditional GET:
   - If `ETag` known: `If-None-Match`
   - Else if `Last-Modified` known: `If-Modified-Since`
   - If 304: skip rebuild, print “up-to-date”
3) Download to temp (`download.json.tmp`) with size limit guardrails (configurable).
4) Validate JSON structure:
   - root dict with `data` list
   - each item has required keys and types
5) Build `index.new.sqlite`:
   - `BEGIN` transaction
   - Insert docs rows
   - Build/refresh FTS if available
   - `COMMIT`
6) Write `state.json` with remote metadata + counts + max updateTime.
7) Atomic swap:
   - rename `index.sqlite` → `index.old.sqlite` (optional)
   - rename `index.new.sqlite` → `index.sqlite`
   - delete old (or keep N versions via config)

Streaming parse choice:
- Prefer `ijson` for true streaming if dependency policy allows.
- Otherwise use `json.load` initially; 33MB is fine; structure supports later swap to streaming with minimal changes.

---

## Tree Generation Strategy

Do not compute tree by scanning full content. Use DB aggregation:
- Fetch `directory_json` for all docs (or precomputed `directory_path`) and build an in-memory prefix tree (fast for ~4k items).
- Alternatively, store a `directories` table updated during indexing with `path TEXT PRIMARY KEY`, `count INTEGER`, `parent TEXT`.
  - For MVP, in-memory from query is sufficient; add `directories` table only if doc count becomes very large.

---

## Error Handling & UX

- `update`: clearly distinguish “network failure” vs “bad JSON” vs “index build failure”.
- Always keep last known-good index for reads.
- Provide `--verbose` for debug; `--json` output for scripting.
- Avoid printing full content by default; allow `show --head` and `show --content`.

---

## Testing Strategy

- Unit tests for:
  - JSON validation (missing keys, wrong types)
  - Directory tree builder (counts, depth trimming, subtree filtering)
  - Search query formatting + escaping
  - State handling (etag/last_modified)
- Integration tests:
  - Build index from a small fixture JSON (a trimmed subset)
  - Run `search/tree/show` against built DB and compare deterministic outputs

---

## Task Breakdown (TDD-friendly)

### Task 1: Create CLI skeleton

**Files:**
- Create: `src/openapi_doc_cli/__init__.py`
- Create: `src/openapi_doc_cli/cli.py`
- Create: `pyproject.toml` (if project not using one already)

**Step 1: Write failing smoke test**

```python
def test_cli_help_exits_zero():
    # run `python -m openapi_doc_cli --help`
    assert True
```

**Step 2: Implement minimal entrypoint**

```python
def main():
    ...
```

**Step 3: Run tests**

Run: `pytest -q`
Expected: PASS

---

### Task 2: Implement local state + paths

**Files:**
- Create: `src/openapi_doc_cli/paths.py`
- Create: `src/openapi_doc_cli/state.py`
- Test: `tests/test_state.py`

**Step 1: Write failing tests for state read/write**

```python
def test_state_roundtrip(tmp_path):
    ...
```

**Step 2: Implement state.json read/write and atomic write**

**Step 3: Run tests**

Run: `pytest -q`
Expected: PASS

---

### Task 3: Implement index schema + builder (from local file)

**Files:**
- Create: `src/openapi_doc_cli/index/db.py`
- Create: `src/openapi_doc_cli/index/build.py`
- Test: `tests/test_index_build.py`
- Add fixture: `tests/fixtures/sample.json`

**Step 1: Write failing test that builds DB and queries doc count**

```python
def test_build_creates_docs_table(tmp_path):
    ...
```

**Step 2: Implement schema + inserts**

**Step 3: Run tests**

Run: `pytest -q`
Expected: PASS

---

### Task 4: Implement `tree` command (offline)

**Files:**
- Create: `src/openapi_doc_cli/commands/tree.py`
- Modify: `src/openapi_doc_cli/cli.py`
- Test: `tests/test_tree.py`

**Step 1: Write failing test for subtree + depth**

**Step 2: Implement in-memory tree from `docs.directory_json`**

**Step 3: Run tests**

Run: `pytest -q`
Expected: PASS

---

### Task 5: Implement `search` command (FTS if available)

**Files:**
- Create: `src/openapi_doc_cli/commands/search.py`
- Modify: `src/openapi_doc_cli/index/build.py`
- Test: `tests/test_search.py`

**Step 1: Write failing test: query returns known doc**

**Step 2: Implement FTS detection and query**

**Step 3: Run tests**

Run: `pytest -q`
Expected: PASS

---

### Task 6: Implement `show` + `open`

**Files:**
- Create: `src/openapi_doc_cli/commands/show.py`
- Create: `src/openapi_doc_cli/commands/open.py`
- Modify: `src/openapi_doc_cli/cli.py`
- Test: `tests/test_show_open.py`

---

### Task 7: Implement `update` (remote download)

**Files:**
- Create: `src/openapi_doc_cli/commands/update.py`
- Create: `src/openapi_doc_cli/http.py`
- Modify: `src/openapi_doc_cli/cli.py`
- Test: `tests/test_update.py`

**Notes:**
- In tests, mock HTTP (e.g., `responses` or local test server) to validate ETag/304 behavior.

---

## Acceptance Criteria

- `tree` produces the same hierarchy as the source JSON `directory` fields (with counts).
- `search` returns stable results quickly and works offline.
- `update` is safe: never corrupts the active index, and prints clear status.

