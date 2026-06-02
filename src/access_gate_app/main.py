import os
import http.client
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "access-gate")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.4.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8000")
CAMERA_SERVICE_URL = os.getenv("CAMERA_SERVICE_URL", "http://camera:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notify:8000")


app = FastAPI(
    title="FIT4110 Lab 04 - Access Gate Service",
    version=SERVICE_VERSION,
    description=(
        "Dockerized Access Gate API for Smart Campus entry events. "
        "External service URLs are configured for later multi-service integration."
    ),
)


class AccessDecision(str, Enum):
    granted = "granted"
    denied = "denied"
    manual_review = "manual_review"


class CredentialType(str, Enum):
    card = "card"
    qr = "qr"
    face = "face"
    license_plate = "license_plate"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class IntegrationConfig(BaseModel):
    core_service_url: str
    camera_service_url: str
    notification_service_url: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    integrations: IntegrationConfig


class AccessEventCreate(BaseModel):
    gate_id: str = Field(..., min_length=3, examples=["GATE-A01"])
    credential_id: str = Field(..., min_length=3, examples=["CARD-1001"])
    credential_type: CredentialType = Field(..., examples=["card"])
    person_id: Optional[str] = Field(default=None, examples=["STU-2026-0001"])
    decision: AccessDecision = Field(..., examples=["granted"])
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Boundary range used for gate verification confidence: 0 to 1.",
        examples=[0.95],
    )
    reason: Optional[str] = Field(default=None, max_length=120, examples=["policy_pass"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class AccessEvent(BaseModel):
    event_id: str
    gate_id: str
    credential_id: str
    credential_type: CredentialType
    person_id: Optional[str] = None
    decision: AccessDecision
    confidence: Optional[float] = None
    reason: Optional[str] = None
    timestamp: str
    created_at: str


class AccessEventCreated(BaseModel):
    event_id: str
    gate_id: str
    decision: AccessDecision
    accepted: bool
    created_at: str


ACCESS_EVENTS: List[Dict] = []


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=http.client.responses.get(exc.status_code, "HTTP Error"),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", http.client.responses.get(exc.status_code, "HTTP Error"))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_event_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"AG-{today}-{len(ACCESS_EVENTS) + 1:04d}"


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        integrations=IntegrationConfig(
            core_service_url=CORE_SERVICE_URL,
            camera_service_url=CAMERA_SERVICE_URL,
            notification_service_url=NOTIFICATION_SERVICE_URL,
        ),
    )


@app.post(
    "/access-events",
    response_model=AccessEventCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
    },
)
def create_access_event(
    payload: AccessEventCreate, response: Response
) -> AccessEventCreated:
    if payload.decision == AccessDecision.denied:
        response.headers["X-Warning"] = "access-denied"
    elif payload.confidence is not None and payload.confidence < 0.5:
        response.headers["X-Warning"] = "low-confidence"

    event_id = next_event_id()
    created_at = now_iso()

    item = {
        "event_id": event_id,
        "gate_id": payload.gate_id,
        "credential_id": payload.credential_id,
        "credential_type": payload.credential_type.value,
        "person_id": payload.person_id,
        "decision": payload.decision.value,
        "confidence": payload.confidence,
        "reason": payload.reason,
        "timestamp": payload.timestamp,
        "created_at": created_at,
    }
    ACCESS_EVENTS.append(item)

    return AccessEventCreated(
        event_id=event_id,
        gate_id=payload.gate_id,
        decision=payload.decision,
        accepted=True,
        created_at=created_at,
    )


@app.get("/access-events/latest", dependencies=[Depends(verify_bearer_token)])
def latest_access_events(
    gate_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, List[Dict]]:
    items = ACCESS_EVENTS

    if gate_id:
        items = [item for item in items if item["gate_id"] == gate_id]

    return {"items": items[-limit:]}


@app.get("/access-events/{event_id}", dependencies=[Depends(verify_bearer_token)])
def get_access_event(event_id: str) -> Dict:
    for item in ACCESS_EVENTS:
        if item["event_id"] == event_id:
            return item

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Access event {event_id} does not exist",
            instance=f"/access-events/{event_id}",
            problem_type="https://smart-campus.local/problems/not-found",
        ),
    )
