# feishu-openapi-doc-rag

Offline-first Feishu Open Platform (OpenAPI) documentation retrieval + extraction, designed for RAG-style toolchains.

## What’s inside

- `src/openapi_doc_cli/`: a small Python CLI that builds a local SQLite index from `larkopenapidoc.json` and provides `ls/find/cat/grep/show/open`, plus `diff` for daily-style updates.
- `skills/feishu-openapi-doc-rag/`: a self-contained Skill bundle (vendored `openapi_doc_cli`, CDN bootstrap script, core request-block extractor).

## Search behavior

- Chinese queries now use a CJK-aware fallback matcher when exact FTS tokenization is too brittle, which improves ranking for compound terms such as `审批结果` and out-of-order keywords such as `审批 写入`.
- Compound Chinese input is split into more useful search tokens, so phrases like `审批结果写入` can still surface the most relevant API page.
- `search` and `grep` print an explicit `0 results found ...` message when nothing matches, which makes CLI usage and AI-agent integration easier to diagnose.

## Quick start (local)

```bash
cd /path/to/repo
PYTHONPATH=src python3 -m openapi_doc_cli build --input /path/to/larkopenapidoc.json
PYTHONPATH=src python3 -m openapi_doc_cli grep "多维表格 高级权限" --limit 10
```

## Verify locally

Run the full test suite from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Skill usage (standalone)

After installing the skill, run it from the skill directory:

```bash
cd ~/.codex/skills/feishu-openapi-doc-rag
python3 scripts/bootstrap_index_from_cdn.py
PYTHONPATH=vendor python3 -m openapi_doc_cli grep "发送语音" --limit 10
```

The vendored CLI under `skills/feishu-openapi-doc-rag/vendor/openapi_doc_cli/` is kept in sync with `src/openapi_doc_cli/`, so search behavior stays consistent between local development and the packaged skill.

## Release Notes

### Version history

- `0.1.1` (2026-03-02): bump `openapi_doc_cli` version and align vendored skill version; add strict version assertion in CLI smoke test.
- `0.1.0` (2026-02-27): initial release of offline-first Feishu OpenAPI doc RAG CLI + standalone skill bundle.

### Latest package download

- Latest release package: [feishu-openapi-doc-rag.zip](https://magic-builder.tos-cn-beijing.volces.com/uploads/1772382386892_feishu-openapi-doc-rag.zip)

### Install via AI

Tell your AI assistant to install the skill from the URL above, for example:

```text
Please install this Codex skill from:
https://magic-builder.tos-cn-beijing.volces.com/uploads/1772382386892_feishu-openapi-doc-rag.zip
```
