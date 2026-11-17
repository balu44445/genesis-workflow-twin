"""Local-only API. Start with uvicorn genesis.api:app --host 127.0.0.1."""
from typing import Annotated, Literal
from pathlib import Path
import secrets
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import Field

from .model import Snapshot, StrictModel, lower
from .replay import replay
from .verifier import verify
from . import runtime
from .explain import ai_enabled, ai_explanation, local_explanation

app = FastAPI(title="GENESIS", version="0.2.0", docs_url=None, redoc_url=None,
              description="Local demo and bounded model evidence, not a ServiceNow platform safety certificate.")
configured_hosts = [os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")] + os.environ.get("GENESIS_PUBLIC_HOST", "").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"] + [h.strip() for h in configured_hosts if h.strip()])
assets = Path(__file__).with_name("static")
app.mount("/assets", StaticFiles(directory=assets, check_dir=False), name="assets")


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    request.state.script_nonce = secrets.token_urlsafe(24)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin mutations are disabled"}, status_code=403)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"detail": "Use application/json"}, status_code=415)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
    if request.url.path == "/docs":
        response.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net "
            f"'nonce-{request.state.script_nonce}'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(runtime.RuntimeErrorResponse)
async def runtime_failure(request, exc):
    return JSONResponse({"detail": exc.message}, status_code=exc.status)


class VerifyRequest(StrictModel):
    snapshot: Snapshot
    bound: Annotated[int, Field(ge=0, le=6)] = 3
    timeout_ms: Annotated[int, Field(ge=1, le=10000)] = 2000


class ReplayRequest(StrictModel):
    snapshot: Snapshot
    evidence: dict


ActorID = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class CreateRequest(StrictModel):
    snapshot: Snapshot
    actor: ActorID
    assigned_approver: ActorID


class ActionRequest(StrictModel):
    actor: ActorID
    action: Literal["submit", "approve", "fulfill"]
    expected_version: Annotated[int, Field(ge=0)]


class CompareRequest(VerifyRequest):
    proposed: Snapshot


class ExplainRequest(VerifyRequest):
    external_ai: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local_model_only"}


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(assets / "index.html")


@app.get("/docs", include_in_schema=False)
def api_reference(request: Request):
    html = get_swagger_ui_html(openapi_url="/openapi.json", title="GENESIS API reference").body.decode()
    return HTMLResponse(html.replace("<script>", f'<script nonce="{request.state.script_nonce}">'))


@app.get("/demo/config")
def demo_config():
    public = os.environ.get("GENESIS_PUBLIC_MODE", "").lower() == "true"
    return {"mode": "public_synthetic_demo" if public else "local_demo",
            "identity": "Synthetic actor selection, not authenticated PDI identity",
            "external_ai_enabled": False if public else ai_enabled(), "servicenow_writes": False,
            "session": "Isolated temporary visitor workspace" if public else "Private local workspace",
            "verification_bound_max": 3 if public else 6,
            "supported": ["submit", "approve", "fulfill", "distinct approver"],
            "unsupported": ["delegation", "amount thresholds", "multiple approval stages", "arbitrary scripts"]}


@app.get("/demo/examples/{name}")
def demo_example(name: Literal["vulnerable", "fixed"]):
    return FileResponse(assets / (name + ".json"), media_type="application/json")


@app.get("/demo/requests")
def demo_requests():
    return runtime.listing()


@app.post("/demo/requests", status_code=201)
def demo_create(request: CreateRequest):
    return runtime.create(request.snapshot, request.actor, request.assigned_approver)


@app.get("/demo/requests/{identifier}")
def demo_request(identifier: str):
    return runtime.get(identifier)


@app.post("/demo/requests/{identifier}/actions")
def demo_action(identifier: str, request: ActionRequest):
    return runtime.act(identifier, request.actor, request.action, request.expected_version)


@app.post("/compare")
def compare(request: CompareRequest):
    before, after = request.snapshot.model_dump(), request.proposed.model_dump()
    return {"changes": [{"field": key, "before": before[key], "after": after[key]}
                        for key in before if before[key] != after[key]],
            "current": verify(request.snapshot, request.bound, request.timeout_ms),
            "proposed": verify(request.proposed, request.bound, request.timeout_ms),
            "applied": False, "note": "Preview only. Existing requests retain their original policy."}


@app.post("/explain")
def explain(request: ExplainRequest):
    evidence = verify(request.snapshot, request.bound, request.timeout_ms)
    if request.external_ai:
        if not ai_enabled():
            raise HTTPException(409, "External AI is disabled; evidence has not been sent")
        try:
            explanation = ai_explanation(evidence)
        except Exception as exc:
            # Do not echo provider messages that can contain request details or secrets.
            raise HTTPException(503, "AI explanation unavailable; local verification remains available") from exc
    else:
        explanation = local_explanation(evidence)
    return {"evidence": evidence, "explanation": explanation}


@app.post("/model")
def model(snapshot: Snapshot):
    try:
        return lower(snapshot)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/verify")
def verify_endpoint(request: VerifyRequest):
    return verify(request.snapshot, request.bound, request.timeout_ms)


@app.post("/replay")
def replay_endpoint(request: ReplayRequest):
    try:
        return replay(request.snapshot, request.evidence)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise HTTPException(422, "Evidence is malformed, does not match, or cannot be replayed") from exc
