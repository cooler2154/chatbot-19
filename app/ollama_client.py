"""
Ollama client — pure Python, no pydantic, streaming + graceful error handling
"""

import json
import logging
from typing import AsyncIterator, List, Optional
import httpx

logger = logging.getLogger(__name__)

MFG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_work_order",
            "description": "Retrieve a specific JDE Work Order from F4801 by work order number. Returns header: status, item, quantities, dates, costs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wo_number": {"type": "integer", "description": "Work order document number (DOCO)"},
                    "company":   {"type": "string",  "description": "Company number, default 00000"},
                },
                "required": ["wo_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_work_orders",
            "description": "Search JDE Work Orders in F4801. Filter by plant, item, or status. Status codes: 10=Entered, 20=Approved, 25=Parts Committed, 30=Released, 35=Parts Issued, 40=In Process, 90=Complete, 99=Closed. Default returns 50 rows. If result says MORE RECORDS EXIST, increase max_rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant":       {"type": "string",  "description": "Plant / business unit (MCU) e.g. M30"},
                    "item_number": {"type": "string",  "description": "Item number (LITM)"},
                    "status":      {"type": "string",  "description": "WO status code: 20=Approved, 40=In Process, 30=Released"},
                    "doc_type":    {"type": "string",  "description": "Document type, default WO"},
                    "max_rows":    {"type": "integer", "description": "Max records to return, default 50, max 200"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bom",
            "description": "Retrieve Bill of Materials (F3002) for a manufactured item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_number": {"type": "string", "description": "Item number (LITM)"},
                    "plant":       {"type": "string", "description": "Branch/plant (MMCU)"},
                    "revision":    {"type": "string", "description": "BOM revision level"},
                },
                "required": ["item_number", "plant"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_routing",
            "description": "Retrieve Routing (F3003) for a manufactured item — operations, work centers, hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_number": {"type": "string", "description": "Item number (LITM)"},
                    "plant":       {"type": "string", "description": "Branch/plant (MMCU)"},
                },
                "required": ["item_number", "plant"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wo_parts_list",
            "description": "Get Parts List (F4802) for a work order — components required vs issued vs scrapped.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wo_number": {"type": "integer", "description": "Work order number"},
                },
                "required": ["wo_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wo_operations",
            "description": "Get routing operations (F3111) for a work order — steps, work centers, planned vs actual hours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wo_number": {"type": "integer", "description": "Work order number"},
                },
                "required": ["wo_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mrp_messages",
            "description": "Retrieve unprocessed MRP planning messages (F3411). Types: 01=New Order, 02=Expedite, 03=Defer, 04=Cancel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant":       {"type": "string", "description": "Manufacturing plant"},
                    "item_number": {"type": "string", "description": "Optional item filter"},
                },
                "required": ["plant"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_item_inventory",
            "description": "Get inventory balances (F41021) — on-hand, committed, available by lot/location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_number": {"type": "string", "description": "Item number (LITM)"},
                    "plant":       {"type": "string", "description": "Optional plant filter"},
                },
                "required": ["item_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wo_raw_material_list",
            "description": (
                "Get Raw Material List from F3111 (Work Order Routing Instructions) for a work order. "
                "Returns raw materials/components with quantities, work centers, planned vs actual hours, "
                "operation status, and dates. Use this when user asks about raw materials, "
                "components, ingredients, or materials needed for a specific work order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "wo_number": {"type": "integer", "description": "Work order number (DOCO)"},
                },
                "required": ["wo_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_item_cost",
            "description": "Get standard cost components (F30026). B1=Material, C1=Labor, C2=Machine, C3=Overhead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_number": {"type": "string", "description": "Item number (LITM)"},
                    "plant":       {"type": "string", "description": "Branch/plant"},
                    "cost_method": {"type": "string", "description": "07=Standard (default)"},
                },
                "required": ["item_number", "plant"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generic_data_request",
            "description": "Flexible AIS data request against any JDE manufacturing table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "JDE table name e.g. F4801"},
                    "conditions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "controlID": {"type": "string"},
                                "operator":  {"type": "string"},
                                "value":     {"type": "string"},
                                "dataType":  {"type": "string"},
                            },
                            "required": ["controlID", "operator", "value", "dataType"],
                        },
                    },
                    "return_fields": {"type": "string"},
                    "max_rows":      {"type": "integer"},
                },
                "required": ["table", "conditions", "return_fields"],
            },
        },
    },
]

OLLAMA_NOT_RUNNING = (
    "Ollama is not running or not reachable at the configured URL.\n\n"
    "To fix this:\n"
    "1. Install Ollama from https://ollama.com\n"
    "2. Open a terminal and run:  ollama serve\n"
    "3. Pull a model:             ollama pull llama3.1\n"
    "4. Then re-send your message.\n\n"
    "If Ollama is on a different host, update the Ollama URL in the Config panel."
)

OLLAMA_TIMEOUT = (
    "The model took too long to respond (timeout).\n\n"
    "This usually means the model is too large for your machine\'s RAM/GPU.\n\n"
    "Recommended fix — switch to a smaller, faster model:\n"
    "  ollama pull qwen2.5:3b       (smallest, fastest — good tool use)\n"
    "  ollama pull llama3.2:3b      (fast, good for chat)\n"
    "  ollama pull mistral:7b       (good balance)\n\n"
    "Then update the model name in the Config panel and retry.\n\n"
    "If you want to keep llama3.1 (8B), make sure you have at least 8GB free RAM."
)


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=300)  # 5 min — large models can be slow on first token

    async def close(self):
        await self._client.aclose()

    async def chat_stream(
        self,
        messages: List[dict],
        tools: Optional[List] = None,
        temperature: float = 0.1,
    ) -> AsyncIterator[dict]:
        payload = {
            "model":    self.model,
            "messages": messages,
            "stream":   True,
            "options":  {"temperature": temperature, "num_predict": 2048},
        }
        if tools:
            payload["tools"] = tools

        try:
            async with self._client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                if resp.status_code == 404:
                    yield {"type": "text", "content":
                           f"Model '{self.model}' not found in Ollama.\n"
                           f"Run:  ollama pull {self.model}"}
                    yield {"type": "done"}
                    return

                if resp.status_code != 200:
                    body = await resp.aread()
                    yield {"type": "text", "content":
                           f"Ollama error {resp.status_code}: {body.decode()[:200]}"}
                    yield {"type": "done"}
                    return

                tool_calls_buf = None
                buf = ""

                async for chunk in resp.aiter_bytes():
                    buf += chunk.decode("utf-8", errors="replace")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        msg = data.get("message", {})
                        if msg.get("content"):
                            yield {"type": "text", "content": msg["content"]}
                        if msg.get("tool_calls"):
                            tool_calls_buf = msg["tool_calls"]
                        if data.get("done"):
                            if tool_calls_buf:
                                yield {"type": "tool_calls", "tool_calls": tool_calls_buf}
                            yield {"type": "done"}
                            return

        except httpx.ConnectError as e:
            yield {"type": "text", "content": OLLAMA_NOT_RUNNING}
            yield {"type": "done"}
        except (httpx.ReadTimeout, httpx.TimeoutException):
            yield {"type": "text", "content": OLLAMA_TIMEOUT}
            yield {"type": "done"}
        except OSError:
            yield {"type": "text", "content": OLLAMA_NOT_RUNNING}
            yield {"type": "done"}

    async def list_models(self) -> List[str]:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
