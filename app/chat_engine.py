"""
JDE Manufacturing Chat Engine — pure Python, no pydantic, no FastAPI
"""

import json
import logging
from typing import AsyncIterator, List, Dict, Any

from app.jde_client import JDEClient, parse_ais_response, format_rows_as_text
from app.ollama_client import OllamaClient, MFG_TOOLS
from config.manufacturing_datamodel import get_table_summary, WO_STATUS_CODES, MFG_DOC_TYPES

logger = logging.getLogger(__name__)


def build_system_prompt(jde_environment: str, jde_plant: str = "") -> str:
    table_summary = get_table_summary()
    status_ref = "\n".join(f"  {k}: {v}" for k, v in WO_STATUS_CODES.items())
    doc_ref    = "\n".join(f"  {k}: {v}" for k, v in MFG_DOC_TYPES.items())
    plant_line = f"  |  DEFAULT PLANT: {jde_plant}" if jde_plant else ""
    return f"""You are an expert JD Edwards EnterpriseOne 9.2 Manufacturing assistant.
You have deep knowledge of JDE manufacturing and direct access to live JDE data via AIS tools.

ENVIRONMENT: {jde_environment}{plant_line}

## Capabilities
- Answer JDE Manufacturing process, setup, and configuration questions
- Query live JDE data: work orders, BOMs, routings, shop floor, MRP, inventory, costing
- Explain JDE field names, table structures, and business logic
- Diagnose issues: MRP exceptions, WO variances, BOM errors

## CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY

### RULE 1 — NEVER FABRICATE DATA AND NEVER REPEAT TABLES
NEVER invent, assume, or reuse data from a previous query to answer a new question.
Every question that asks for JDE data MUST trigger a fresh tool call.

CRITICAL — DO NOT REPEAT THE TABLE:
After a tool call returns data, the table is ALREADY displayed in the UI automatically.
Your text response MUST NOT include a markdown table or repeat the rows.
Instead, write a SHORT summary sentence only, for example:
  "Found 11 work orders in status 40 for plant M30. All are for items 2001–8630R."
Do NOT write | DOCO | MCU | ... table syntax. The user can already see the table above your text.

### RULE 2 — ALWAYS CALL A TOOL FOR DATA QUESTIONS
If the user asks about work orders, BOMs, inventory, costs, or any JDE data:
CALL THE APPROPRIATE TOOL. No exceptions. Do not answer from memory or prior results.

### RULE 3 — CORRECT STATUS CODES AND TOOL SELECTION
Work order status codes: 10=Entered, 20=Approved, 25=Parts Committed,
30=Released, 35=Parts Issued, 40=In Process, 90=Complete, 99=Closed.
"Approved" = status 20. "In Process" = status 40. "Released" = status 30.

TOOL SELECTION — CRITICAL:
- User gives a SPECIFIC WO NUMBER (e.g. "work order 20001", "WO 451021"):
  → ALWAYS call get_work_order(wo_number=20001)
  → NEVER call search_work_orders for a specific number
- User searches by STATUS or PLANT without a specific number:
  → call search_work_orders(status="40", plant="M30")
- NEVER carry forward status, plant, or any filter from a previous query.
  Each question is independent. Only pass parameters the user explicitly stated NOW.
  If user says "work order 20001 in M30" — pass ONLY wo_number=20001. No status filter.

### RULE 4 — PAGINATION
If the tool result says "MORE RECORDS EXIST", tell the user how many were returned
and offer to search with a higher limit or more specific filters.

### RULE 5 — TOOL SELECTION
Use search_work_orders for F4801 queries (not generic_data_request).
Use get_bom for F3002. Use get_routing for F3003.
Only use generic_data_request for tables not covered by specific tools.
Never use generic_data_request with empty conditions.

### RULE 6 — NO LOOPS
Do not call the same tool with the same arguments more than once per turn.
If a query returns no data, tell the user clearly what was searched and ask for clarification.

### RULE 7 — NEVER OUTPUT RAW JSON OR FUNCTION CALLS AS TEXT
NEVER write {{"name": "...", "parameters": {{...}}}} as text output.
NEVER write tool call syntax as plain text.
If you want to call a tool, USE THE TOOL CALLING MECHANISM — do not describe it in text.
If you cannot call the tool directly, say what data you need and ask the user to rephrase.

### RULE 8 — RAW MATERIALS vs PARTS LIST
- "Raw materials" or "raw material list" for a work order → call get_wo_raw_material_list (queries F3111)
- "Parts list", "components issued", "parts issued" → call get_wo_parts_list (queries F4802)
- "Operations", "routing", "work centers" → call get_wo_operations (also queries F3111 for operations)
- F3111 contains BOTH routing operations AND raw material (CPIT = component item, UORG = qty required)

### RULE 9 — ONLY USE DEFINED TOOLS
Only call tools explicitly defined. Do not invent tool names.
Available tools: get_work_order, search_work_orders, get_bom, get_routing,
get_wo_parts_list, get_wo_operations, get_wo_raw_material_list,
get_mrp_messages, get_item_inventory, get_item_cost, generic_data_request.

## Known working data from your JDE instance
- Plant/Business Unit: M30 (confirmed working)
- Work orders exist with items: 2001, 2004, 2005, 220 in plant M30
- WO status 40 = In Process (confirmed records exist)
- When user asks for work orders without specifying plant, use M30 as default

## JDE Manufacturing Data Model
{table_summary}

## Work Order Status Codes (F4801.SRST)
{status_ref}

## Manufacturing Document Types
{doc_ref}

## Cost Components (F30026.CDCD)
  B1: Purchased material    C1: Direct labor
  C2: Machine/equipment     C3: Outside processing
  D1: Variable overhead     D2: Fixed overhead

## Response style
- Use tables for multi-row data. Show field aliases alongside readable labels.
- Format dates as DD/MM/YYYY. Include UOM with quantities.
- Decode status codes to descriptions when showing WO data.
- If no data found, say so clearly and suggest possible reasons.
"""


async def dispatch_tool(tool_name: str, args: Dict[str, Any], jde: JDEClient) -> str:
    logger.info("Tool: %s  args: %s", tool_name, args)
    try:
        # Alias mapping — handle common LLM naming variations
        tool_aliases = {
            "get_raw_materials":        "get_wo_raw_material_list",
            "get_components":           "get_wo_parts_list",
            "get_wo_components":        "get_wo_parts_list",
            "get_materials":            "get_wo_raw_material_list",
            "get_wo_materials":         "get_wo_raw_material_list",
            "get_work_order_details":   "get_work_order",
            "search_orders":            "search_work_orders",
            "get_work_orders":          "search_work_orders",
        }
        tool_name = tool_aliases.get(tool_name.lower(), tool_name)

        if tool_name == "get_work_order":
            wo_num = args.get("wo_number") or args.get("DOCO") or args.get("doco", 0)
            raw = await jde.get_work_order(int(wo_num), args.get("company", "00000"))
        elif tool_name == "search_work_orders":
            _max = args.get("max_rows", 20)
            try:
                _max = int(_max) if _max is not None else 20
            except (ValueError, TypeError):
                _max = 20
            raw = await jde.search_work_orders(
                plant=args.get("plant"),
                item_number=args.get("item_number"),
                status=args.get("status"),
                doc_type=args.get("doc_type", "WO"),
                max_rows=_max,
            )
        elif tool_name == "get_bom":
            raw = await jde.get_bom(args["item_number"], args["plant"],
                                     args.get("revision", " "))
        elif tool_name == "get_routing":
            raw = await jde.get_routing(args["item_number"], args["plant"])
        elif tool_name == "get_wo_parts_list":
            raw = await jde.get_wo_parts_list(int(args["wo_number"]))
        elif tool_name == "get_wo_operations":
            raw = await jde.get_wo_operations(int(args["wo_number"]))
        elif tool_name == "get_wo_raw_material_list":
            wo_num = args.get("wo_number") or args.get("DOCO") or 0
            raw = await jde.get_wo_raw_material_list(int(wo_num))
        elif tool_name == "get_mrp_messages":
            raw = await jde.get_mrp_messages(args["plant"], args.get("item_number"))
        elif tool_name == "get_item_inventory":
            raw = await jde.get_item_inventory(args["item_number"], args.get("plant"))
        elif tool_name == "get_item_cost":
            raw = await jde.get_item_cost(args["item_number"], args["plant"],
                                           args.get("cost_method", "07"))
        elif tool_name == "generic_data_request":
            table = args.get("table", "").strip()
            if not table:
                return "Error: table name is required. Please specify the JDE table name e.g. F4801, F3002."
            conditions = args.get("conditions", [])
            active_conditions = [c for c in conditions if str(c.get("value","")).strip()]
            if not active_conditions:
                return (
                    f"Cannot query {table} without filter conditions — JDE returns no data "
                    f"for unfiltered queries on large tables.\n"
                    f"Please use search_work_orders (for F4801), get_bom, get_routing, "
                    f"get_item_inventory, or get_item_cost instead, which have proper filters built in.\n"
                    f"Or ask the user to provide a specific value to filter by."
                )
            raw = await jde.generic_data_request(
                table=table,
                conditions=args.get("conditions", []),
                return_fields=args.get("return_fields", "*"),
                max_rows=int(args.get("max_rows", 25)),
            )
        else:
            return f"Unknown tool: {tool_name}"

        rows = parse_ais_response(raw)
        return format_rows_as_text(rows, table_name=args.get("table", tool_name))

    except PermissionError as e:
        return f"JDE authentication error: {e}"
    except Exception as e:
        logger.exception("Tool %s failed", tool_name)
        return f"Error in {tool_name}: {type(e).__name__}: {e}"


class ChatEngine:
    def __init__(self, ollama: OllamaClient, jde: JDEClient, config: dict):
        self.ollama = ollama
        self.jde    = jde
        self.config = config
        self.system_prompt = build_system_prompt(
            jde_environment=config.get("jde_environment", "JDV920"),
            jde_plant=config.get("default_plant", ""),
        )

    def _base_messages(self, history: List[dict]) -> List[dict]:
        return [{"role": "system", "content": self.system_prompt}] + history

    async def stream_response(
        self, history: List[dict], user_message: str
    ) -> AsyncIterator[dict]:
        messages = self._base_messages(history) + [
            {"role": "user", "content": user_message}
        ]

        recent_tool_calls: list = []   # track recent calls to detect loops

        for _ in range(4):   # max tool-call rounds — reduced to prevent looping
            accumulated_text  = ""
            tool_calls_received = []

            async for event in self.ollama.chat_stream(messages, tools=MFG_TOOLS):
                if event["type"] == "text":
                    accumulated_text += event["content"]
                    yield {"type": "text", "content": event["content"]}
                elif event["type"] == "tool_calls":
                    tool_calls_received = event["tool_calls"]
                elif event["type"] == "done":
                    pass

            if not tool_calls_received:
                yield {"type": "done"}
                return

            messages.append({
                "role":       "assistant",
                "content":    accumulated_text,
                "tool_calls": tool_calls_received,
            })

            for tc in tool_calls_received:
                fn        = tc.get("function", {})
                tool_name = fn.get("name", "unknown")
                raw_args  = fn.get("arguments", {})
                args      = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)

                # Loop detection — stop if same tool+args called 3 times
                call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                repeat_count = recent_tool_calls.count(call_sig)
                if repeat_count >= 2:
                    yield {"type": "text", "content":
                           f"\n\nI've already tried {tool_name} with the same parameters "
                           f"and got no results. Could you provide more specific details? "
                           f"For example: a plant code, item number, work order number, or status."}
                    yield {"type": "done"}
                    return
                recent_tool_calls.append(call_sig)

                yield {"type": "tool_start", "name": tool_name, "args": args}

                result_text = await dispatch_tool(tool_name, args, self.jde)
                row_count   = max(0, result_text.count("\n") - 2)

                yield {
                    "type":      "tool_result",
                    "name":      tool_name,
                    "row_count": row_count,
                    "preview":   result_text,   # full text — frontend renders as table
                }

                messages.append({
                    "role":    "tool",
                    "content": (
                        f"Tool: {tool_name}\nResult:\n{result_text}\n\n"
                        f"IMPORTANT: The table above is already displayed to the user in the UI. "
                        f"Do NOT repeat it as markdown. Write only a brief 1-2 sentence summary."
                    ),
                })

        yield {"type": "text", "content": "\n\nReached maximum tool-call rounds."}
        yield {"type": "done"}
