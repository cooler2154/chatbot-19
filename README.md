# JDE EnterpriseOne 9.2 — Manufacturing Chatbot

A local AI chatbot for JD Edwards EnterpriseOne 9.2 Manufacturing, powered by **Ollama** (local LLM) and **JDE AIS** (Application Interface Services).

---

## Features

- 🤖 **Local LLM** via Ollama — no cloud, no data leaves your network
- 🏭 **JDE Manufacturing data model** — Work Orders, BOMs, Routings, MRP, Shop Floor, Costing
- 🔌 **Live JDE queries** via AIS REST endpoints (token auth, BROWSE/FETCH)
- 📡 **Streaming responses** via Server-Sent Events
- 🔍 **10 built-in tools** for the most common manufacturing queries
- 🗄️ **Generic data request** tool for any JDE table not covered by specific tools

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | [python.org](https://python.org) |
| Ollama | [ollama.com](https://ollama.com) — install and pull a model |
| JDE 9.2 with AIS enabled | AIS Tools Release 9.2 Update 4+ recommended |

### Recommended Ollama models (tool-calling support)
```
ollama pull llama3.1        # Best balance — recommended
ollama pull mistral-nemo    # Faster, good tool use
ollama pull qwen2.5         # Excellent for structured queries
```

---

## Quick Start

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### Windows
```
start.bat
```

### Manual
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Then open **http://localhost:8000** in your browser.

---

## Configuration

Open the **⚙️ Config** panel in the UI and fill in:

| Field | Example | Notes |
|---|---|---|
| Ollama URL | `http://localhost:11434` | Default Ollama port |
| Ollama Model | `llama3.1` | Must support tool calling |
| AIS Server URL | `http://jde-server:8080/jderest/v3` | Your JDE AIS endpoint |
| Username | `JDE_USER` | JDE login with read access |
| Password | `••••••` | Stored in memory only, never on disk |
| Environment | `JDV920` | JDE environment name |
| Role | `*ALL` | JDE role |
| Default Plant | `MFG01` | Optional — pre-fills plant prompts |

---

## Project Structure

```
jde-chatbot/
├── run.py                          # Entry point
├── start.sh / start.bat            # Quick start scripts
├── requirements.txt
├── frontend/
│   └── index.html                  # Single-file chat UI
├── app/
│   ├── main.py                     # FastAPI app + routes
│   ├── chat_engine.py              # LLM orchestration + tool loop
│   ├── ollama_client.py            # Ollama streaming client + tool definitions
│   └── jde_client.py               # JDE AIS HTTP client
└── config/
    └── manufacturing_datamodel.py  # Full JDE manufacturing data model
```

---

## JDE Manufacturing Data Model Covered

### Work Orders (Module 48)
| Table | Description |
|---|---|
| F4801 | Work Order Master — header, status, quantities, costs |
| F4801T | Work Order Text — notes and instructions |
| F4802 | Work Order Parts List — components required vs issued |

### Bill of Materials (Module 30)
| Table | Description |
|---|---|
| F3002 | BOM Master — component items, quantities, operations |

### Routings (Module 30)
| Table | Description |
|---|---|
| F3003 | Routing Master — operations, work centers, hours |
| F3006 | Work Center Master — capacities and cost rates |

### Shop Floor Control (Module 31)
| Table | Description |
|---|---|
| F3111 | WO Routing Instructions — actual operations on a WO |
| F3112 | WO Time Transactions — labor/machine time reported |
| F3116 | WO Completions — finished goods received |

### MRP / Planning (Module 34)
| Table | Description |
|---|---|
| F3411 | MRP Detail Messages — planning action messages |
| F3413 | MRP Lower Level Requirements — pegged demand |

### Inventory / Item Master
| Table | Description |
|---|---|
| F4101 | Item Master — all items including manufactured/phantom |
| F4102 | Item Branch/Plant — per-plant settings, reorder policy |
| F41021 | Item Location — lot/location balances |

### Product Costing
| Table | Description |
|---|---|
| F30026 | Frozen Cost Components — standard cost by component |
| F4105 | Item Cost File — unit costs by cost method |

---

## Available Chat Tools

| Tool | JDE Table(s) | What it does |
|---|---|---|
| `get_work_order` | F4801 | Fetch a specific WO by number |
| `search_work_orders` | F4801 | Search WOs by plant / item / status |
| `get_bom` | F3002 | BOM components for an item |
| `get_routing` | F3003 | Routing operations for an item |
| `get_wo_parts_list` | F4802 | Parts required/issued for a WO |
| `get_wo_operations` | F3111 | Operations and hours for a WO |
| `get_mrp_messages` | F3411 | Unprocessed MRP action messages |
| `get_item_inventory` | F41021 | Inventory balances by lot/location |
| `get_item_cost` | F30026 | Standard cost components for item |
| `generic_data_request` | Any | Query any JDE table with filters |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Chat UI |
| `POST` | `/api/chat` | SSE streaming chat |
| `GET` | `/api/health` | Ollama + JDE connectivity |
| `GET` | `/api/config` | Current configuration |
| `POST` | `/api/config` | Update configuration |
| `GET` | `/api/models` | Available Ollama models |
| `GET` | `/api/datamodel` | Full manufacturing table reference |
| `GET` | `/api/datamodel/{table}` | Specific table field detail |

---

## Extending

### Add a new JDE table to the data model
Edit `config/manufacturing_datamodel.py` — add a `JDETable` object and register it in `ALL_TABLES`.

### Add a new tool
1. Add the tool definition to `MFG_TOOLS` in `app/ollama_client.py`
2. Add the convenience method to `JDEClient` in `app/jde_client.py`
3. Add the dispatch case in `dispatch_tool()` in `app/chat_engine.py`

### Add Orchestrator / Form Request support
The `JDEClient` can be extended with an `orchestrator_request()` method calling `/jderest/v3/orchestrator` — useful for triggering JDE business processes from the chatbot.

---

## Security Notes

- Credentials are stored **in memory only** — never written to disk
- All JDE calls go through AIS token auth (25-min TTL, auto-renewed)
- Intended for **internal/local use** — add auth middleware before exposing externally
- Use a JDE user with **read-only** security to limit exposure

---

## Troubleshooting

**Ollama not responding**
```bash
ollama serve          # Make sure Ollama is running
ollama list           # Check available models
```

**JDE AIS auth fails**
- Confirm AIS Tools is enabled in JDE Server Manager
- Check the AIS URL includes `/jderest/v3` (not `/jderest/v2`)
- Verify the user has `EnterpriseOne` login and AIS access

**Tool calls not working / LLM ignores tools**
- Switch to `llama3.1` or `qwen2.5` — they have the best tool-calling support
- Avoid `phi3` or small models (<7B) for tool use
