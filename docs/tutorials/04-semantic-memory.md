# Tutorial 4 — Semantic memory

**Goal:** store a few pieces of context and recall them by meaning (not keyword)
using ForgeFlow's pgvector-backed memory.

**Time:** ~10 minutes.

## Prerequisites

- A running stack. Memory read/write needs a role with `write:memory` /
  `read:memory` — the seeded `rep-1` (`sales_rep`) has both.

```bash
REP=$(curl -s http://localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"rep-1","password":"change-me-locally-only"}' | jq -r .access_token)
```

## 1. Store some memories

Each entry is text plus an optional `namespace` that scopes it (so one workflow
can't recall another's data). ForgeFlow embeds the content on write.

```bash
curl -s -X POST http://localhost:8000/memory/store \
  -H "Authorization: Bearer $REP" -H 'Content-Type: application/json' \
  -d '{
        "content": "Stripe declined a 2025 expansion, citing an existing Adyen contract through Q2 2026.",
        "namespace": "sales/stripe"
      }' | jq .

curl -s -X POST http://localhost:8000/memory/store \
  -H "Authorization: Bearer $REP" -H 'Content-Type: application/json' \
  -d '{
        "content": "Net-new ARR over $100K requires VP-level approval before sending a proposal.",
        "namespace": "policy/global"
      }' | jq .
```

Each call returns the stored entry's id.

## 2. Recall by meaning

Search is semantic — the query doesn't have to share words with the stored text:

```bash
curl -s -G "http://localhost:8000/memory/search" \
  -H "Authorization: Bearer $REP" \
  --data-urlencode "q=Is there a competitor blocking the Stripe deal?" \
  --data-urlencode "limit=5" | jq '.[] | {namespace, similarity, content}'
```

Expected: the Adyen/Stripe memory ranks first, with a high `similarity` (cosine),
even though the query never says "Adyen".

## 3. Delete a memory

```bash
curl -s -X DELETE "http://localhost:8000/memory/$MEMORY_ID" \
  -H "Authorization: Bearer $REP" | jq .
```

## How agents use it

Workers recall memory as a tool call (`memory.recall`) during a run — for
example, the `analyzer` pulls prior context on a company before scoring it. You
can watch this in the run trace ([Tutorial 3](03-streaming-and-debugging.md#2-read-the-per-agent-trace))
and in the console's **Memory** view.

## Expected result

- Two stored memories in different namespaces.
- A semantic search that returns the most relevant entry first, by cosine
  similarity.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `403 Forbidden` | Your role lacks `read:memory` / `write:memory`; use `rep-1` or `admin`. |
| Empty results | Store entries first; check the `namespace` matches (or omit it to search all). |
| `400` on search | `q` is required; URL-encode it (use `--data-urlencode`). |

## Next steps

- [Glossary → Semantic memory](../glossary.md#memory--evaluation)
- [API reference → Memory](../api-reference.md#agents-a2a--memory--metrics--audit--workspaces--marketplace)
- [Architecture → semantic memory](../architecture.md)
