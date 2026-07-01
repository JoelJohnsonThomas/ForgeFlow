# Tutorials

Goal-oriented, step-by-step walkthroughs. Each one is self-contained, states its
prerequisites, and ends with an expected result and next steps. Every command
here is run against the real API and has been kept in sync with the codebase.

| # | Tutorial | You'll learn | Time |
|---|---|---|---|
| 1 | [Your first workflow](01-first-workflow.md) | Boot the stack and run `sales_ops` end to end, including human approval | ~15 min |
| 2 | [Run fully offline with Ollama](02-run-offline-with-ollama.md) | Execute workflows with a local LLM — no OpenAI key, no egress | ~15 min |
| 3 | [Stream & debug a run](03-streaming-and-debugging.md) | Watch agent reasoning over SSE, read per-agent traces, and diagnose failures | ~10 min |
| 4 | [Semantic memory](04-semantic-memory.md) | Store and recall context with pgvector | ~10 min |

## Before you start

All tutorials assume:

- **Docker Desktop** running (`docker info` succeeds).
- The repo cloned and `cp .env.example .env` done.
- **One** of: an `OPENAI_API_KEY` in `.env`, or Ollama (Tutorial 2).

Enterprise connectors are **optional** — without credentials they run as mocks,
so the `sales_ops` demo works with no external accounts.

## Related

- [Quickstart](../../README.md#-quickstart) — the condensed version of Tutorial 1
- [Examples](../examples.md) — copy-paste snippets (curl, Python, streaming)
- [API reference](../api-reference.md) · [Glossary](../glossary.md) · [FAQ](../faq.md)
- [Troubleshooting](../troubleshooting.md) — when a step doesn't behave
