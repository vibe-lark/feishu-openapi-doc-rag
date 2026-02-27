# feishu-openapi-doc-rag

Offline-first Feishu Open Platform (OpenAPI) documentation retrieval + extraction, designed for RAG-style toolchains.

## What’s inside

- `src/openapi_doc_cli/`: a small Python CLI that builds a local SQLite index from `larkopenapidoc.json` and provides `ls/find/cat/grep/show/open`, plus `diff` for daily-style updates.
- `skills/feishu-openapi-doc-rag/`: a self-contained Skill bundle (vendored `openapi_doc_cli`, CDN bootstrap script, core request-block extractor).

## Quick start (local)

```bash
cd /path/to/repo
PYTHONPATH=src python3 -m openapi_doc_cli build --input /path/to/larkopenapidoc.json
PYTHONPATH=src python3 -m openapi_doc_cli grep "多维表格 高级权限" --limit 10
```

## Skill usage (standalone)

After installing the skill, run it from the skill directory:

```bash
cd ~/.codex/skills/feishu-openapi-doc-rag
python3 scripts/bootstrap_index_from_cdn.py
PYTHONPATH=vendor python3 -m openapi_doc_cli grep "发送语音" --limit 10
```

