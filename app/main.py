"""
JDE Manufacturing Chatbot — Starlette backend, zero pydantic, zero FastAPI
Works on Python 3.9 – 3.14+ with no compiler or build tools required.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

from app.jde_client import JDEClient, JDEConfig
from app.ollama_client import OllamaClient, MFG_TOOLS
from app.chat_engine import ChatEngine
from config.manufacturing_datamodel import ALL_TABLES, MODULE_GROUPS, get_field_info
from config import skills_db

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── App state ───────────────────────────────────────────────────────────

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
        # admin API key can be supplied via env ADMIN_API_KEY or set here
        "admin_api_key":   os.environ.get("ADMIN_API_KEY", ""),
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


# ── Auth helper ─────────────────────────────────────────────────────────

def _get_request_api_key(request: Request) -> Optional[str]:
    # Prefer Authorization: Bearer <token>, fallback to X-API-Key
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return auth
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")


def require_admin(request: Request) -> Optional[JSONResponse]:
    key = app_state["config"].get("admin_api_key") or os.environ.get("ADMIN_API_KEY")
    if not key:
        # If no admin key configured, deny by default — safer than open
        return JSONResponse({"error": "admin API key not configured"}, status_code=401)
    provided = _get_request_api_key(request)
    if not provided or provided != key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return None


# ── Route handlers ─────────────────────────────────────────────────────────

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
        result["jde"] = ok
        result["jde_ais_url"] = app_state["jde"].config.ais_base
        result["jde_auth_mode"] = "Basic Auth"
        result["jde_environment"] = app_state["config"]["jde_environment"]
        if not ok:
            result["jde_error"] = "Ping failed — check AIS URL and credentials"
    except Exception as e:
        result["jde"] = False
        result["jde_error"] = str(e)
        try:
            result["jde_ais_url"] = app_state["jde"].config.ais_base
        except Exception:
            pass
    return JSONResponse(result)


async def get_config(request: Request):
    # admin only
    auth = require_admin(request)
    if auth:
        return auth
    safe = {k: v for k, v in app_state["config"].items() if k != "jde_password"}
    safe["jde_password"] = "***" if app_state["config"].get("jde_password") else ""
    return JSONResponse(safe)


async def update_config(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    body = await request.json()
    allowed = {"ollama_url", "ollama_model", "jde_ais_url", "jde_username",
               "jde_password", "jde_environment", "jde_role", "default_plant", "admin_api_key"}
    patch = {k: v for k, v in body.items() if k in allowed and v is not None}
    app_state["config"].update(patch)
    # persist admin_api_key in memory only — recommend using env var for production
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
    body = await request.json()
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


# ── Skills management endpoints ───────────────────────────────────────────
async def list_skills(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    return JSONResponse({"skills": skills_db.get_all()})


async def create_skill(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    body = await request.json()
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)
    skill = body
    skills_db.upsert(skill)
    return JSONResponse({"status": "created", "skill": skill})


async def get_skill(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    name = request.path_params["skill_name"]
    s = skills_db.get(name)
    if not s:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"skill": s})


async def update_skill(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    name = request.path_params["skill_name"]
    body = await request.json()
    s = skills_db.get(name)
    if not s:
        return JSONResponse({"error": "not found"}, status_code=404)
    s.update(body)
    skills_db.upsert(s)
    return JSONResponse({"status": "updated", "skill": s})


async def delete_skill(request: Request):
    auth = require_admin(request)
    if auth:
        return auth
    name = request.path_params["skill_name"]
    ok = skills_db.delete(name)
    return JSONResponse({"deleted": ok})


async def skill_chat(request: Request):
    # public chat endpoint for a named skill — invoking users need not be admins
    skill_name = request.path_params["skill_name"]
    skill = skills_db.get(skill_name)
    if not skill:
        return JSONResponse({"error": "skill not found"}, status_code=404)
    body = await request.json()
    message = body.get("message", "").strip()
    history = body.get("history", [])
    if not message:
        return JSONResponse({"error": "message required"}, status_code=400)

    # prepare overrides
    system_prompt = skill.get("system_prompt") or None
    allowed = skill.get("allowed_tools")
    tools = None
    if isinstance(allowed, list):
        tools = [t for t in MFG_TOOLS if t.get("function", {}).get("name") in allowed]
    model_override = skill.get("model")
    jde_overrides = skill.get("jde_overrides") or {}

    temp_ollama = None
    temp_jde = None
    try:
        # Decide Ollama client
        ollama_client = app_state["ollama"]
        if model_override:
            temp_ollama = OllamaClient(base_url=app_state["config"]["ollama_url"], model=model_override)
            ollama_client = temp_ollama

        # Decide JDE client
        jde_client = app_state["jde"]
        if jde_overrides:
            jcfg = JDEConfig(
                ais_url=jde_overrides.get("ais_url", app_state["config"]["jde_ais_url"]),
                username=jde_overrides.get("username", app_state["config"]["jde_username"]),
                password=jde_overrides.get("password", app_state["config"]["jde_password"]),
                environment=jde_overrides.get("environment", app_state["config"]["jde_environment"]),
                role=jde_overrides.get("role", app_state["config"]["jde_role"]),
            )
            temp_jde = JDEClient(jcfg)
            jde_client = temp_jde

        merged_config = dict(app_state["config"])
        merged_config.update({"default_plant": skill.get("default_plant", merged_config.get("default_plant"))})

        engine = ChatEngine(ollama=ollama_client, jde=jde_client, config=merged_config)

        async def event_stream():
            try:
                async for event in engine.stream_response(history, message, tools=tools, system_prompt=system_prompt):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                logger.exception("Skill chat stream error")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    finally:
        try:
            if temp_ollama:
                await temp_ollama.close()
        except Exception:
            pass
        try:
            if temp_jde:
                await temp_jde.close()
        except Exception:
            pass


# ── App wiring ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    # init DB/migrate skills and clients
    skills_db.init_db()
    skills_db.migrate_from_json()
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

    # Skills (admin)
    Route("/api/skills",             list_skills,   methods=["GET"]),
    Route("/api/skills",             create_skill,  methods=["POST"]),
    Route("/api/skills/{skill_name}", get_skill,     methods=["GET"]),
    Route("/api/skills/{skill_name}", update_skill,  methods=["PUT"]),
    Route("/api/skills/{skill_name}", delete_skill,  methods=["DELETE"]),

    # Public per-skill chat
    Route("/skill/{skill_name}/chat", skill_chat,    methods=["POST"]),
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
