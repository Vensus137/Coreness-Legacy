# Coreness Flow

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Electron](https://img.shields.io/badge/Electron-React-47848F.svg?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2B-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Language:** [Русский](README.md) | **English**

Most AI assistants are chat-based. `Coreness Flow` is different.

The agent doesn't wait for messages — it **reacts to events**: incoming webhooks, schedules, signals from plugins. On receiving an event, it runs a **scenario** — a chain of steps with LLM calls, branching, and third-party service actions. Logic is defined in **YAML** and can be changed without touching code.

Everything runs locally. Windows. Single user, full control.

## 🏗️ How It Works

```
Event (chat / webhook / cron / API)
         ↓
Scenario engine — matches triggers, runs step chains
         ↓
Plugins — execute actions, call LLMs, write to storage
         ↓
UI receives results via API Bus
```

Layers don't depend on each other directly. **UI** — React on Electron — talks to the backend only via WebSocket and API Bus. **Plugins** — isolated Python modules; the core discovers them via `config.json`, registers actions, and delegates execution. A new integration is just a new folder, no core changes.

## ✨ Features

**📋 YAML scenarios**  
Triggers (message, webhook, cron), steps, conditional branching, cross-scenario calls. Data flows through `_cache` and placeholders — no code needed for simple chains.

**⚡ Async actions**  
Long-running work runs in the background via `call_nowait`; the scenario continues without blocking. Completion is checked via `_async_action` placeholders.

**🔌 Plugin system and UI contributions**  
Architecture similar to VS Code: `config.json` describes metadata, settings, actions, and **contributes**. Via contributes, a plugin adds tabs, sidebar items, settings sections — the frontend builds the UI from a single `get_contributions` call. Model inspired by [VS Code Contribution Points](https://code.visualstudio.com/api/references/contribution-points), adapted for this app.

**🤖 LLM and RAG**  
Request routing by complexity: simple tasks to cheaper models, complex ones to more powerful. Local RAG: BGE-M3 ONNX INT8 + Qdrant embedded, no mandatory external services.

## 🛠 Stack

| Component | Technology |
| :-- | :-- |
| Frontend | Electron + React |
| Backend | Python 3.11 |
| Transport | WebSocket, API Bus (actions + events) |
| LLM | OpenAI-compatible API (aggregators) |
| RAG | BGE-M3 ONNX INT8 + Qdrant embedded |
| Storage | SQLite + JSON (config) + YAML (scenarios) |

## 🎬 Demo

### Startup and main chat

Splash intro: app launch, then main chat — ask a question and get an answer right away.

<img src="https://habrastorage.org/webt/v9/ud/0t/v9ud0tfxjq0m7bmcea0dh1iplu8.gif" width="560" alt="Splash intro"/>

### Chat

Clearing chat history and starting new conversations.

<img src="https://habrastorage.org/webt/j5/d_/dz/j5d_dzcamjcqndvciw8k5devyy4.gif" width="560" alt="Chat"/>

### General settings

General settings and options.

<img src="https://habrastorage.org/webt/fp/1t/ep/fp1tep2dacjxpngwbmlfgktke9i.gif" width="560" alt="General settings"/>

### AI and vector storage

AI provider settings, vector store, and management: view and delete chunks.

<img src="https://habrastorage.org/webt/5z/gf/re/5zgfrer-o4eebhvjcht-bpeevxy.gif" width="560" alt="AI and vector storage"/>

## 👥 Who It's For

- **Engineers and analysts** — personal automation without SaaS subscriptions
- **Managers and team leads** — single place for routine: statuses, reports, monitoring
- **Developers** — example of an event-driven desktop app with plugins and UI contributions

## 🚀 Quick Start

**From source** (requires Python 3.11, Node.js, Windows):

```powershell
pip install -r requirements.txt
cd frontend && npm install && cd ..
.\scripts\run-dev.ps1
```

Backend and app window start with one command and hot reload.

**Or install from releases:** go to the **Releases** section on the repo page, download the Windows installer, and follow the instructions in the release notes.

## 📖 Documentation

| Section | Document |
| :-- | :-- |
| Architecture | [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) |
| Plugins | [PLUGINS.md](docs/architecture/PLUGINS.md) |
| Scenarios | [SCENARIO_CONFIG_GUIDE.md](docs/configuration/SCENARIO_CONFIG_GUIDE.md) |
| UI contributions | [CONTRIBUTION_REFERENCE.md](docs/reference/CONTRIBUTION_REFERENCE.md) |
| UI guidelines | [UI_GUIDELINES.md](docs/architecture/UI_GUIDELINES.md) |

Section index — **[docs/README.md](docs/README.md)**.

## 📄 License

Distributed under the [MIT](LICENSE) license.

<p align="center">
  <strong>Coreness</strong> — Create. Automate. Scale.
</p>
