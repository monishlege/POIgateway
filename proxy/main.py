"""Proof-of-Intent HTTP gateway."""

from __future__ import annotations

import json
import os
import re
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Any, Callable, cast
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.responses import Response

from proxy.zk_engine import verify_proof


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DAG_PATH = Path(os.environ.get("POI_POLICY_DAG", str(BASE_DIR / "policy_dag.json")))
TERMS_PATH = PROJECT_ROOT / "TERMS_OF_SERVICE.md"
PRIVACY_PATH = PROJECT_ROOT / "PRIVACY_POLICY.md"
SUPPORT_EMAIL = os.environ.get(
    "POI_SUPPORT_EMAIL", "support@proof-of-intent.example"
)
MAX_BODY_BYTES = int(os.environ.get("POI_MAX_BODY_BYTES", str(2 * 1024 * 1024)))
MAX_UPSTREAM_RESPONSE_BYTES = int(
    os.environ.get("POI_MAX_UPSTREAM_RESPONSE_BYTES", str(16 * 1024 * 1024))
)
UPSTREAM_TIMEOUT_SECONDS = float(os.environ.get("POI_UPSTREAM_TIMEOUT_SECONDS", "30"))
FIELD_ELEMENT_LIMIT = 21888242871839275222246405745257275088548364400416034343698204186575808495617
HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")
HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _allowed_hosts() -> set[str]:
    return {
        host.strip().rstrip(".").lower()
        for host in os.environ.get("POI_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }


def _load_edges() -> set[tuple[str, str]]:
    try:
        raw_data = json.loads(DAG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            raise ValueError("unsupported policy DAG format")
        data = cast(dict[str, Any], raw_data)
        edge_data = data.get("edges")
        if data.get("version") != 1 or not isinstance(edge_data, list):
            raise ValueError("unsupported policy DAG format")
        edge_list = cast(list[Any], edge_data)
        edges: set[tuple[str, str]] = set()
        adjacency: dict[str, set[str]] = {}
        for edge in edge_list:
            if not isinstance(edge, dict):
                raise ValueError("each policy edge must be an object")
            current = _canonical_field(edge["currentStateHash"])
            following = _canonical_field(edge["nextStateHash"])
            if current == following:
                raise ValueError("policy DAG cannot contain self-edges")
            edges.add((current, following))
            adjacency.setdefault(current, set()).add(following)

        nodes = set(adjacency)
        for destinations in adjacency.values():
            nodes.update(destinations)
        indegrees = {state: 0 for state in nodes}
        for destinations in adjacency.values():
            for destination in destinations:
                indegrees[destination] += 1
        ready = [state for state, indegree in indegrees.items() if indegree == 0]
        visited_count = 0
        while ready:
            state = ready.pop()
            visited_count += 1
            for destination in adjacency.get(state, set()):
                indegrees[destination] -= 1
                if indegrees[destination] == 0:
                    ready.append(destination)
        if visited_count != len(nodes):
            raise ValueError("policy graph contains a cycle")
        return edges
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unable to load policy DAG at {DAG_PATH}: {exc}") from exc


def _canonical_field(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("field elements must be unsigned decimal integers")
    if isinstance(value, int):
        integer = value
    elif isinstance(value, str) and value.isdecimal():
        integer = int(value)
    else:
        raise ValueError("field elements must be unsigned decimal integers")
    if not 0 <= integer < FIELD_ELEMENT_LIMIT:
        raise ValueError("field element is outside the BN254 scalar field")
    return str(integer)


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_url: str = Field(min_length=1, max_length=2048)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    currentStateHash: str | int
    proposedNextStateHash: str | int
    proof: dict[str, Any]

    @field_validator("currentStateHash", "proposedNextStateHash")
    @classmethod
    def validate_field(cls, value: str | int) -> str:
        return _canonical_field(value)

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 100:
            raise ValueError("too many headers")
        for name, header_value in value.items():
            if not HEADER_NAME_PATTERN.fullmatch(name):
                raise ValueError("invalid header name")
            if "\r" in header_value or "\n" in header_value:
                raise ValueError("invalid header value")
        return value


def _validate_target(target_url: str) -> None:
    try:
        parsed = urlsplit(target_url)
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Target URL is not permitted") from exc
    hosts = _allowed_hosts()
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or not HOSTNAME_PATTERN.fullmatch(hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
        or hostname not in hosts
    ):
        raise HTTPException(status_code=400, detail="Target URL is not permitted")


class RequestSizeLimitMiddleware:
    def __init__(self, app: Callable[..., Any], max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > self.max_body_bytes:
                    await self._send_too_large(send)
                    return
            except ValueError:
                await self._send_too_large(send)
                return

        buffered_messages: list[dict[str, Any]] = []
        received_bytes = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            received_bytes += len(message.get("body", b""))
            if received_bytes > self.max_body_bytes:
                await self._send_too_large(send)
                return
            buffered_messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive() -> dict[str, Any]:
            if buffered_messages:
                return buffered_messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _send_too_large(send: Callable[..., Any]) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.policy_edges = _load_edges()
    except RuntimeError as exc:
        raise RuntimeError(str(exc)) from exc
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(UPSTREAM_TIMEOUT_SECONDS),
        follow_redirects=False,
        trust_env=False,
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="Proof-of-Intent Gateway",
    version="1.0.0",
    description=(
        "A FastAPI gateway that checks proposed state transitions against the "
        "configured policy DAG and verifies Groth16 proofs before forwarding "
        "approved requests to allowlisted HTTPS upstreams. A valid proof does "
        "not by itself bind the upstream request body or destination to the "
        "proved intent. See the [Terms of Service](/terms) and "
        "[Privacy Policy](/privacy)."
    ),
    terms_of_service="/terms",
    contact={
        "name": "Proof-of-Intent Gateway Support",
        "email": SUPPORT_EMAIL,
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    lifespan=lifespan,
)
app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=MAX_BODY_BYTES)


def _legal_document(path: Path, title: str) -> HTMLResponse:
    try:
        markdown = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Legal document unavailable") from exc

    page = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title></head><body><main><pre>"
        f"{escape(markdown)}</pre></main></body></html>"
    )
    return HTMLResponse(content=page)


@app.get("/terms", response_class=HTMLResponse, tags=["Legal"])
async def terms_of_service() -> HTMLResponse:
    """Serve the Terms of Service as escaped, readable Markdown text."""
    return _legal_document(TERMS_PATH, "Terms of Service")


@app.get("/privacy", response_class=HTMLResponse, tags=["Legal"])
async def privacy_policy() -> HTMLResponse:
    """Serve the Privacy Policy as escaped, readable Markdown text."""
    return _legal_document(PRIVACY_PATH, "Privacy Policy")


@app.post("/v1/proxy/execute")
async def execute(payload: ExecuteRequest, request: Request) -> Any:
    _validate_target(payload.target_url)

    current_hash = _canonical_field(payload.currentStateHash)
    next_hash = _canonical_field(payload.proposedNextStateHash)
    if (current_hash, next_hash) not in request.app.state.policy_edges:
        raise HTTPException(status_code=403, detail="Goal Drift Detected")

    if not await verify_proof(
        payload.proof,
        [current_hash, next_hash],
    ):
        raise HTTPException(status_code=403, detail="Goal Drift Detected")

    connection_value = next(
        (value for name, value in payload.headers.items() if name.lower() == "connection"),
        "",
    )
    connection_tokens = {token.strip().lower() for token in connection_value.split(",") if token.strip()}
    headers = {
        name: value
        for name, value in payload.headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS | connection_tokens
    }
    try:
        async with request.app.state.http_client.stream(
            method="POST",
            url=payload.target_url,
            headers=headers,
            json=payload.body,
        ) as upstream:
            chunks: list[bytes] = []
            received_bytes = 0
            async for chunk in upstream.aiter_bytes():
                received_bytes += len(chunk)
                if received_bytes > MAX_UPSTREAM_RESPONSE_BYTES:
                    raise HTTPException(status_code=502, detail="Upstream response too large")
                chunks.append(chunk)
            response_content = b"".join(chunks)
            response_status = upstream.status_code
            response_headers = {
                name: value
                for name, value in upstream.headers.items()
                if name.lower() not in HOP_BY_HOP_HEADERS | {"content-encoding"}
            }
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Upstream request timed out") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Upstream request failed") from exc

    return Response(
        content=response_content,
        status_code=response_status,
        headers=response_headers,
    )