"""
JDE EnterpriseOne AIS v2 Client
Uses HTTP Basic Authentication on every request — most reliable method,
confirmed working in Postman. No token management needed.

Per JDE docs: Basic Auth is supported on all AIS v2 endpoints.
Authorization: Basic base64(username:password)
"""

import base64
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class JDEConfig:
    def __init__(self, ais_url="http://localhost:8080/jderest/v2", username="",
                 password="", environment="JDV920", role="*ALL",
                 device_name="JDE-MFG-Chatbot", timeout=30):
        base = ais_url.rstrip("/")
        # Ensure /v2 is present
        if not (base.endswith("/v2") or "/v2/" in base):
            if base.endswith("/jderest"):
                base = base + "/v2"
        self.ais_base = base
        self.username = username
        self.password = password
        self.environment = environment
        self.role = role
        self.device_name = device_name
        self.timeout = timeout

    @property
    def basic_auth(self) -> str:
        """Base64 encoded Basic Auth value."""
        creds = f"{self.username}:{self.password}"
        return base64.b64encode(creds.encode()).decode()

    @property
    def auth_headers(self) -> Dict[str, str]:
        """Headers for every AIS request — Basic Auth per JDE docs."""
        return {
            "Authorization": f"Basic {self.basic_auth}",
            "Accept":        "application/json",
        }


class JDEClient:
    def __init__(self, config: JDEConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def close(self):
        await self._client.aclose()

    async def ping(self) -> bool:
        """Test connectivity — try a token request with Basic Auth to verify credentials."""
        try:
            resp = await self._client.post(
                f"{self.config.ais_base}/tokenrequest",
                headers={
                    "Authorization":          f"Basic {self.config.basic_auth}",
                    "Content-Type":           "application/json",
                    "jde-AIS-Auth-Environment": self.config.environment,
                    "jde-AIS-Auth-Role":       self.config.role,
                    "jde-AIS-Auth-Device":     self.config.device_name,
                },
                json={},
                timeout=10,
            )
            logger.info("Ping %s -> %s", self.config.ais_base, resp.status_code)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Ping failed: %s", e)
            return False

    # ── Core GET ─────────────────────────────────────────────────────────────

    async def _get(self, table: str, fields: List[str],
                   filters: List[str], limit: int = 25,
                   sort: Optional[str] = None) -> dict:
        """
        GET /jderest/v2/dataservice/table/{TABLE}
        with Basic Auth header + $filter / $field / $limit query params.

        Per JDE docs and confirmed via Postman:
          Authorization: Basic <base64(user:pass)>
        """
        params: List[tuple] = []
        for f in filters:
            params.append(("$filter", f))
        for f in fields:
            params.append(("$field", f))
        params.append(("$limit", str(limit)))
        if sort:
            params.append(("$sort", sort))
        # Always send environment — required for stateless Basic Auth sessions
        if self.config.environment:
            params.append(("$environment", self.config.environment))
        if self.config.role:
            params.append(("$role", self.config.role))

        url = f"{self.config.ais_base}/dataservice/table/{table}"
        logger.info("AIS GET %s  filters=%d  fields=%d  limit=%d",
                    table, len(filters), len(fields), limit)
        logger.debug("GET %s params=%s", url, params)

        resp = await self._client.get(
            url,
            headers=self.config.auth_headers,
            params=params,
        )

        body_text = resp.text
        logger.debug("Response %s  body_len=%d  body=%s",
                     resp.status_code, len(body_text), body_text[:800])

        if resp.status_code == 401:
            raise PermissionError(
                f"JDE auth failed (401) — check username and password.\n"
                f"URL: {url}"
            )
        if resp.status_code == 403:
            raise PermissionError(
                f"JDE access denied (403) — user may lack permission for {table}."
            )
        if resp.status_code == 404:
            raise ValueError(
                f"Not found (404) — check AIS URL. Tried: {url}"
            )
        if resp.status_code == 503:
            body = resp.text
            logger.error("JDE 503 for %s\n%s", url, body[:800])
            # 503 with "invalid inputs" means wrong field name or table not accessible
            raise ValueError(
                f"JDE returned 503 (Service Unavailable) for table {table}.\n"
                f"This usually means: invalid field alias, table not licensed, "
                f"or the table requires different filter fields.\n"
                f"Response: {body[:300]}"
            )
        if not resp.is_success:
            logger.error("JDE %s for %s\n%s", resp.status_code, url, resp.text[:500])
            raise ValueError(
                f"JDE AIS returned {resp.status_code} for {table}.\n"
                f"Response: {resp.text[:300]}"
            )

        return resp.json()

    # ── Filter helpers (v2 operators per docs) ────────────────────────────────

    def _eq(self, field: str, value: str) -> str:
        return f"{field} EQ {value}"

    def _ne(self, field: str, value: str) -> str:
        return f"{field} NE {value}"

    def _gt(self, field: str, value: str) -> str:
        return f"{field} GT {value}"

    def _ge(self, field: str, value: str) -> str:
        return f"{field} GE {value}"

    def _lt(self, field: str, value: str) -> str:
        return f"{field} LT {value}"

    def _sw(self, field: str, value: str) -> str:
        return f"{field} STARTSWITH {value}"

    def _contains(self, field: str, value: str) -> str:
        return f"{field} CONTAINS {value}"

    # ── Manufacturing query methods ───────────────────────────────────────────

    async def get_work_order(self, wo_number: int, company: str = "00000") -> dict:
        return await self._get("F4801",
            fields=["F4801.DOCO","F4801.DCTO","F4801.KCOO","F4801.MCU","F4801.ITM",
                    "F4801.LITM","F4801.SRST","F4801.UORG","F4801.TRQT","F4801.SOQS",
                    "F4801.DRQJ","F4801.STRT","F4801.SETK","F4801.ECST","F4801.ACST",
                    "F4801.BREV"],
            filters=[self._eq("F4801.DOCO", str(wo_number))],
            limit=1)

    async def search_work_orders(self, plant=None, item_number=None,
                                  status=None, doc_type="WO", max_rows=50) -> dict:
        plant       = plant.strip()       if plant       else None
        item_number = item_number.strip() if item_number else None
        status      = status.strip()      if status      else None
        doc_type    = (doc_type or "WO").strip()
        try:
            max_rows = int(max_rows) if max_rows is not None else 50
        except (ValueError, TypeError):
            max_rows = 50

        filters = []
        if doc_type:
            filters.append(self._eq("F4801.DCTO", doc_type))
        if status:
            filters.append(self._eq("F4801.SRST", status))
        if plant:
            filters.append(self._eq("F4801.MCU", plant))
        if item_number:
            filters.append(self._sw("F4801.LITM", item_number.upper()))

        # First: get total count — fetch with large limit and read summary.records
        # JDE summary.records = number of records IN this page, moreRecords tells if more exist
        # To get true total we fetch up to 500 and check moreRecords flag
        count_resp = await self._get("F4801",
            fields=["F4801.DOCO"], filters=filters, limit=500)
        total_count = 0
        more_exist  = False
        for key, val in count_resp.items():
            if key.startswith("fs_DATABROWSE_"):
                summary = ((val.get("data") or {})
                           .get("gridData", {})
                           .get("summary", {}))
                total_count = summary.get("records", 0)
                more_exist  = summary.get("moreRecords", False)
                break
        if more_exist:
            total_count = f"{total_count}+"

        # Then: fetch the actual rows up to max_rows
        rows_resp = await self._get("F4801",
            fields=["F4801.DOCO","F4801.LITM","F4801.MCU","F4801.SRST",
                    "F4801.UORG","F4801.TRQT","F4801.DRQJ","F4801.STRT",
                    "F4801.ECST","F4801.ACST"],
            filters=filters, limit=max_rows)

        # Inject total count into the summary
        for key, val in rows_resp.items():
            if key.startswith("fs_DATABROWSE_") and isinstance(val, dict):
                grid = (val.get("data") or {}).get("gridData", {})
                if "summary" not in grid:
                    grid["summary"] = {}
                grid["summary"]["totalRecords"] = total_count
                grid["summary"]["moreRecords"]  = more_exist
                break

        return rows_resp

    async def get_bom(self, item_number: str, plant: str, revision: str = " ") -> dict:
        # F3002 filter: use MMCU for plant, ITM for short item number
        # LKITL (2nd item number alias) is not queryable in v2 dataservice
        # Try plant filter; if item_number looks numeric use ITM, otherwise use LITM
        plant = plant.strip() if plant else ""
        filters = []
        if plant:
            filters.append(self._eq("F3002.MMCU", plant))
        # Try item as both short number and 2nd item number
        if item_number.strip().isdigit():
            filters.append(self._eq("F3002.ITM", item_number.strip()))
        else:
            # For alpha item numbers try LITM
            filters.append(self._eq("F3002.LITM", item_number.upper().strip()))
        return await self._get("F3002",
            fields=["F3002.ITM","F3002.LITM","F3002.MMCU","F3002.BREV","F3002.OPSC",
                    "F3002.CPNT","F3002.LNID","F3002.BQTY","F3002.UOM",
                    "F3002.EFFF","F3002.EFFT","F3002.CPNB","F3002.SCRAP"],
            filters=filters, limit=100)

    async def get_routing(self, item_number: str, plant: str) -> dict:
        plant = plant.strip() if plant else ""
        filters = []
        if plant:
            filters.append(self._eq("F3003.MMCU", plant))
        if item_number.strip().isdigit():
            filters.append(self._eq("F3003.ITM", item_number.strip()))
        else:
            filters.append(self._eq("F3003.LITM", item_number.upper().strip()))
        return await self._get("F3003",
            fields=["F3003.ITM","F3003.LITM","F3003.MMCU","F3003.RREV","F3003.OPSC",
                    "F3003.OPDS","F3003.WRKT","F3003.SETL","F3003.RUNL",
                    "F3003.MCHT","F3003.PRST","F3003.MOVD","F3003.QUEU"],
            filters=filters, limit=50)

    async def get_wo_parts_list(self, wo_number: int) -> dict:
        return await self._get("F4802",
            fields=["F4802.DOCO","F4802.DCTO","F4802.CPNT","F4802.ITM","F4802.LITM",
                    "F4802.LNID","F4802.TRQT","F4802.ISQT","F4802.SQOR",
                    "F4802.UOM","F4802.OPSC","F4802.LOCN","F4802.ECST","F4802.ACST"],
            filters=[self._eq("F4802.DOCO", str(wo_number)),
                     self._eq("F4802.DCTO", "WO")],
            limit=100)

    async def get_wo_operations(self, wo_number: int) -> dict:
        return await self._get("F3111",
            fields=["F3111.DOCO","F3111.OPSC","F3111.OPDS","F3111.WRKT","F3111.OPST",
                    "F3111.SETL","F3111.RUNL","F3111.MCHT","F3111.ASET","F3111.ARUN",
                    "F3111.AMCH","F3111.TRQT","F3111.SQOR","F3111.STRT","F3111.DRQJ",
                    "F3111.ASTRT","F3111.AEND"],
            filters=[self._eq("F3111.DOCO", str(wo_number))],
            limit=50)

    async def get_wo_raw_material_list(self, wo_number: int) -> dict:
        """Fetch raw materials from F3111 (WO Routing Instructions) by work order number."""
        return await self._get("F3111",
            fields=["F3111.DOCO","F3111.OPSC","F3111.OPDS","F3111.WRKT","F3111.OPST",
                    "F3111.SETL","F3111.RUNL","F3111.MCHT","F3111.ASET","F3111.ARUN",
                    "F3111.AMCH","F3111.TRQT","F3111.SQOR","F3111.STRT","F3111.DRQJ",
                    "F3111.ASTRT","F3111.AEND","F3111.CPIT","F3111.UORG"],
            filters=[self._eq("F3111.DOCO", str(wo_number)),
                     self._eq("F3111.DCTO", "WO")],
            limit=100)

    async def get_mrp_messages(self, plant: str,
                                item_number: Optional[str] = None) -> dict:
        filters = [self._eq("F3411.MMCU", plant)]
        if item_number:
            filters.append(self._eq("F3411.LITM", item_number.upper()))
        return await self._get("F3411",
            fields=["F3411.ITM","F3411.MMCU","F3411.TRDJ","F3411.MSGT","F3411.UORG",
                    "F3411.DRQJ","F3411.STRT","F3411.DOCO","F3411.PROC"],
            filters=filters, limit=50)

    async def get_item_inventory(self, item_number: str,
                                  plant: Optional[str] = None) -> dict:
        filters = [self._eq("F41021.LITM", item_number.upper())]
        if plant:
            filters.append(self._eq("F41021.MCU", plant))
        return await self._get("F41021",
            fields=["F41021.ITM","F41021.MCU","F41021.LOCN","F41021.LOTN",
                    "F41021.PQOH","F41021.PREQ","F41021.PQOA","F41021.LEXP",
                    "F41021.LOTS"],
            filters=filters, limit=50)

    async def get_item_cost(self, item_number: str, plant: str,
                             cost_method: str = "07") -> dict:
        return await self._get("F30026",
            fields=["F30026.ITM","F30026.MCU","F30026.CMTH","F30026.CDCD",
                    "F30026.CUNI","F30026.TCOS","F30026.UPMJ"],
            filters=[self._eq("F30026.LITM", item_number.upper()),
                     self._eq("F30026.MCU",  plant),
                     self._eq("F30026.CMTH", cost_method)],
            limit=20)

    # Default fields per table — used when LLM passes "*" or empty return_fields
    DEFAULT_FIELDS: Dict[str, List[str]] = {
        "F4801":  ["F4801.DOCO","F4801.LITM","F4801.MCU","F4801.SRST",
                   "F4801.UORG","F4801.TRQT","F4801.DRQJ","F4801.STRT",
                   "F4801.ECST","F4801.ACST"],
        "F4802":  ["F4802.DOCO","F4802.LITM","F4802.TRQT","F4802.ISQT",
                   "F4802.SQOR","F4802.UOM","F4802.OPSC","F4802.LOCN"],
        "F3002":  ["F3002.KIT","F3002.LITM","F3002.MMCU","F3002.BQTY",
                   "F3002.UOM","F3002.OPSC","F3002.CPNB","F3002.SCRAP"],
        "F3003":  ["F3003.LITM","F3003.MMCU","F3003.OPSC","F3003.OPDS",
                   "F3003.WRKT","F3003.SETL","F3003.RUNL","F3003.MCHT"],
        "F3111":  ["F3111.DOCO","F3111.OPSC","F3111.OPDS","F3111.WRKT",
                   "F3111.OPST","F3111.CPIT","F3111.UORG",
                   "F3111.ASET","F3111.ARUN","F3111.AMCH",
                   "F3111.TRQT","F3111.SQOR","F3111.STRT","F3111.DRQJ"],
        "F3112":  ["F3112.DOCO","F3112.OPSC","F3112.TRDJ","F3112.WRKT",
                   "F3112.SETL","F3112.RUNL","F3112.MCHT","F3112.TRQT"],
        "F3116":  ["F3116.DOCO","F3116.ITM","F3116.TRDJ","F3116.TRQT",
                   "F3116.LOCN","F3116.LOTN","F3116.ACST"],
        "F3411":  ["F3411.ITM","F3411.MMCU","F3411.TRDJ","F3411.MSGT",
                   "F3411.UORG","F3411.DRQJ","F3411.DOCO","F3411.PROC"],
        "F4101":  ["F4101.ITM","F4101.LITM","F4101.DSC1","F4101.STKT",
                   "F4101.UOM","F4101.LDTE","F4101.MMCU"],
        "F4102":  ["F4102.ITM","F4102.MCU","F4102.LOCN","F4102.RPOL",
                   "F4102.SSQT","F4102.PQOH","F4102.PREQ","F4102.SOQS"],
        "F41021": ["F41021.ITM","F41021.MCU","F41021.LOCN","F41021.LOTN",
                   "F41021.PQOH","F41021.PREQ","F41021.PQOA","F41021.LEXP"],
        "F30026": ["F30026.ITM","F30026.MCU","F30026.CMTH","F30026.CDCD",
                   "F30026.CUNI","F30026.TCOS"],
        "F4105":  ["F4105.ITM","F4105.MCU","F4105.CMTH","F4105.UNCS"],
        "F3006":  ["F3006.WRKT","F3006.MMCU","F3006.MDES","F3006.WCTP",
                   "F3006.WCEF","F3006.WCUL","F3006.SHFT","F3006.HOUR"],
    }

    async def generic_data_request(self, table: str, conditions: List[Dict],
                                    return_fields: str, max_rows: int = 25) -> dict:
        """Generic tool — converts LLM condition dicts to v2 filter strings."""
        OP_MAP = {
            "EQUAL":           "EQ",
            "NOT_EQUAL":       "NE",
            "GREATER":         "GT",
            "GREATER_EQUAL":   "GE",
            "LESS":            "LT",
            "LESS_EQUAL":      "LE",
            "STR_STARTS_WITH": "STARTSWITH",
            "CONTAINS":        "CONTAINS",
            "EQ": "EQ", "NE": "NE", "GT": "GT",
            "GE": "GE", "LT": "LT", "LE": "LE",
            "=":  "EQ", "!=": "NE", ">":  "GT",
            ">=": "GE", "<":  "LT", "<=": "LE",
        }
        filters = []
        for c in conditions:
            val = str(c.get("value", "")).strip()
            if not val:
                continue
            op    = OP_MAP.get(str(c.get("operator", "EQ")).upper().strip(), "EQ")
            field = c.get("controlID", c.get("field", "")).strip()
            if not field:
                continue
            if op == "STARTSWITH":
                filters.append(f"{field} STARTSWITH {val}")
            elif op == "CONTAINS":
                filters.append(f"{field} CONTAINS {val}")
            else:
                filters.append(f"{field} {op} {val}")

        # Resolve fields — "*" or empty → use table defaults
        raw_fields = return_fields.strip() if return_fields else ""
        if not raw_fields or raw_fields == "*":
            fields = self.DEFAULT_FIELDS.get(table.upper(),
                     [f"{table}.DOCO", f"{table}.MCU"])   # safe fallback
            logger.info("Using default fields for %s: %s", table, fields)
        else:
            fields = [f.strip() for f in raw_fields.split(",") if f.strip()]

        return await self._get(table, fields=fields, filters=filters, limit=max_rows)


# ── Response parsing ──────────────────────────────────────────────────────────
# v2 response: { "fs_DATABROWSE_F4801": { "data": { "gridData": { "rowset": [...] } } } }
# Row keys use underscore: F4801_DOCO (not F4801.DOCO)

class RowList(list):
    """List subclass that carries summary metadata from JDE AIS response."""
    def __init__(self, rows, summary=None):
        super().__init__(rows)
        self.summary = summary or {}


def parse_ais_response(raw: dict) -> "RowList":
    rowset = []
    summary = {}
    for key, val in raw.items():
        if key.startswith("fs_DATABROWSE_") and isinstance(val, dict):
            grid = (val.get("data") or {}).get("gridData", {})
            rowset = grid.get("rowset", [])
            summary = grid.get("summary", {})
            if rowset:
                break

    rows = []
    for row in rowset:
        flat = {}
        for k, v in row.items():
            # F4801_DOCO → DOCO  or  F4801.DOCO → DOCO
            if "_" in k:
                col = k.split("_", 1)[1]
            elif "." in k:
                col = k.split(".", 1)[1]
            else:
                col = k
            flat[col] = v
        if flat:
            rows.append(flat)

    return RowList(rows, summary)


def _get_summary(rows) -> dict:
    return getattr(rows, "summary", {})


def format_rows_as_text(rows: List[Dict], table_name: str = "") -> str:
    summary      = _get_summary(rows)
    more_records = summary.get("moreRecords", False)
    total        = summary.get("totalRecords", None)   # injected by search_work_orders
    if not rows:
        return f"No records found{f' in {table_name}' if table_name else ''}."
    cols   = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    sep    = "  ".join("-" * widths[c] for c in cols)
    body   = "\n".join(
        "  ".join(str(r.get(c) or "").ljust(widths[c]) for c in cols) for r in rows
    )
    n = len(rows)
    if total is not None:
        total_str = str(total)
        try:
            total_int = int(total_str.rstrip("+"))
            has_more  = total_str.endswith("+") or more_records or total_int > n
        except (ValueError, TypeError):
            has_more  = more_records
            total_str = str(total)
        if has_more:
            note = (f"\n(Showing {n} of {total_str} total records."
                    f" To see more, ask with a higher limit e.g. 'limit 200')")
        else:
            note = f"\n({n} of {total_str} total records — all shown)"
    elif more_records:
        note = f"\n({n} records returned — more exist in JDE. Ask with higher limit.)"
    else:
        note = f"\n({n} record{'s' if n != 1 else ''} returned)"
    return f"{header}\n{sep}\n{body}{note}"
