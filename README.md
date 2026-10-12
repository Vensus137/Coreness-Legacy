# Coreness Legacy

Frozen Coreness projects, kept as they were when development stopped. Each project lives in its own folder as a snapshot of its repository; git history is not included, so the archive holds a single commit.

Snapshots are stored byte-for-byte — `* -text` in `.gitattributes` disables line-ending conversion. Nothing inside a snapshot is filtered out or rewritten, and no `.env` files or private keys were ever part of one.

| Folder | What it is | Last commit |
| --- | --- | --- |
| [`Coreness-Platform/`](Coreness-Platform/) | Multitenant platform for Telegram bots and AI agents: YAML scenarios, plugin system, row-level security in PostgreSQL, RAG over a vector store | 2026-02-25 |
| [`Coreness-Flow/`](Coreness-Flow/) | Event-driven desktop AI agent: YAML scenarios, local RAG, LLM routing, plugins with UI contributions | 2026-02-28 |

> **Frozen.** Nothing here is maintained: no fixes, no updates, no support. A finished project arrives as one more folder.

## License

MIT — see [LICENSE](LICENSE). Every snapshot keeps its own `LICENSE`, `README` and `README_EN` as well.

---

Maintained by @Vensus137 — additions only.
