"""
JDE Manufacturing Chatbot — Starlette backend, zero pydantic, zero FastAPI
Works on Python 3.9 – 3.14+ with no compiler or build tools required.
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from app.jde_client import JDEClient, JDEConfig
from app.ollama_client import OllamaClient
from app.chat_engine import ChatEngine
from config.manufacturing_datamodel import ALL_TABLES, MODULE_GROUPS, get_field_info

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── App state ─────────────────────────────────────────────────────────────────

app_state: dict = {
    "config": {
        "ollama_url":      "http://localhost:11434",
        "ollama_model":    "llama3.1",
        "jde_ais_url":     "http://localhost:8080/jderest/v2",
        "jde_username":    "",
        "jde_password":    "",
        "jde_environment": "JDV920",
        "jde_role":        "*ALL",
        "default_plant":   "",
    },
}


def rebuild_clients():
    cfg = app_state["config"]
    app_state["ollama"] = OllamaClient(base_url=cfg["ollama_url"],
                                        model=cfg["ollama_model"])
    app_state["jde"] = JDEClient(JDEConfig(
        ais_url=cfg["jde_ais_url"],
        username=cfg["jde_username"],
        password=cfg["jde_password"],
        environment=cfg["jde_environment"],
        role=cfg["jde_role"],
        timeout=30,
    ))
    app_state["engine"] = ChatEngine(
        ollama=app_state["ollama"],
        jde=app_state["jde"],
        config=cfg,
    )
    logger.info("Clients ready — model=%s  env=%s",
                cfg["ollama_model"], cfg["jde_environment"])


# ── Route handlers ────────────────────────────────────────────────────────────

async def index(request: Request):
    return FileResponse("frontend/index.html")


async def health(request: Request):
    result = {"status": "ok", "ollama": False, "jde": False, "models": []}
    try:
        models = await app_state["ollama"].list_models()
        result["ollama"] = True
        result["models"] = models
    except Exception as e:
        result["ollama_error"] = str(e)
    try:
        ok = await app_state["jde"].ping()
        result["jde"]           = ok
        result["jde_ais_url"]   = app_state["jde"].config.ais_base
        result["jde_auth_mode"] = "Basic Auth"
        result["jde_environment"] = app_state["config"]["jde_environment"]
        if not ok:
            result["jde_error"] = "Ping failed — check AIS URL and credentials"
    except Exception as e:
        result["jde"]         = False
        result["jde_error"]   = str(e)
        result["jde_ais_url"] = app_state["jde"].config.ais_base
    return JSONResponse(result)


async def get_config(request: Request):
    safe = {k: v for k, v in app_state["config"].items() if k != "jde_password"}
    safe["jde_password"] = "***" if app_state["config"].get("jde_password") else ""
    return JSONResponse(safe)


async def update_config(request: Request):
    body = await request.json()
    allowed = {"ollama_url", "ollama_model", "jde_ais_url", "jde_username",
               "jde_password", "jde_environment", "jde_role", "default_plant"}
    patch = {k: v for k, v in body.items() if k in allowed and v is not None and v != ""}
    app_state["config"].update(patch)
    rebuild_clients()
    safe = {k: v for k, v in app_state["config"].items() if k != "jde_password"}
    safe["jde_password"] = "***" if app_state["config"].get("jde_password") else ""
    return JSONResponse({"status": "updated", "config": safe})


async def list_models(request: Request):
    try:
        models = await app_state["ollama"].list_models()
        return JSONResponse({"models": models})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


async def chat(request: Request):
    body    = await request.json()
    message = body.get("message", "").strip()
    history = body.get("history", [])

    if not message:
        return JSONResponse({"error": "message required"}, status_code=400)

    engine: ChatEngine = app_state["engine"]

    async def event_stream():
        try:
            async for event in engine.stream_response(history, message):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def datamodel(request: Request):
    return JSONResponse({
        "modules": MODULE_GROUPS,
        "tables": {
            name: {
                "description": t.description,
                "module":      t.module,
                "key_fields":  t.key_fields,
                "related":     t.related_tables,
                "fields": [
                    {"alias": f.alias, "name": f.name,
                     "type": f.data_type, "description": f.description}
                    for f in t.fields
                ],
            }
            for name, t in ALL_TABLES.items()
        },
    })


async def table_detail(request: Request):
    table_name = request.path_params["table_name"].upper()
    info = get_field_info(table_name)
    if not info:
        return JSONResponse({"error": f"Table {table_name} not in data model"}, status_code=404)
    return JSONResponse({"table": table_name, "detail": info})


# ── App wiring ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    rebuild_clients()
    yield
    if app_state.get("ollama"):
        await app_state["ollama"].close()
    if app_state.get("jde"):
        await app_state["jde"].close()


routes = [
    Route("/",                       index),
    Route("/api/health",             health),
    Route("/api/config",             get_config,    methods=["GET"]),
    Route("/api/config",             update_config, methods=["POST"]),
    Route("/api/models",             list_models),
    Route("/api/chat",               chat,          methods=["POST"]),
    Route("/api/datamodel",          datamodel),
    Route("/api/datamodel/{table_name}", table_detail),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"],
               allow_methods=["*"], allow_headers=["*"]),
]

app = Starlette(
    routes=routes,
    middleware=middleware,
    lifespan=lifespan,
)
