# SPDX-License-Identifier: MIT
"""
Audit endpoints to track agent sessions and events.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..audit import (
    AuditEvent,
    AuditRun,
    append_event,
    close_run,
    create_run,
    get_run,
    list_events,
    list_runs,
)
from ..state import AppState
from .deps import get_app_state
from .schemas import (
    AuditEventCreateRequest,
    AuditEventListResponse,
    AuditEventSchema,
    AuditRunCloseRequest,
    AuditRunCreateRequest,
    AuditRunListResponse,
    AuditRunSchema,
)

router = APIRouter(prefix="/audit", tags=["audit"])


def _serialize_run(run: AuditRun) -> AuditRunSchema:
    return AuditRunSchema(
        id=run.id,
        name=run.name,
        status=run.status,
        root_path=run.root_path,
        notes=run.notes,
        created_at=run.created_at,
        closed_at=run.closed_at,
        event_count=run.event_count,
    )


def _serialize_event(event: AuditEvent) -> AuditEventSchema:
    return AuditEventSchema(
        id=event.id,
        run_id=event.run_id,
        type=event.type,
        title=event.title,
        detail=event.detail,
        actor=event.actor,
        phase=event.phase,
        status=event.status,
        ref=event.ref,
        payload=event.payload,
        created_at=event.created_at,
    )


def _validate_run_root(run: AuditRun, state: AppState) -> None:
    if not run.root_path:
        return
    current_root = Path(state.settings.root_path).expanduser().resolve()
    run_root = Path(run.root_path).expanduser().resolve()
    if current_root != run_root:
        raise HTTPException(
            status_code=404,
            detail="Run not found for this workspace",
        )


@router.get("/runs", response_model=AuditRunListResponse)
async def list_audit_runs(
    state: AppState = Depends(get_app_state),
    limit: int = Query(20, ge=1, le=200, description="Maximum runs to fetch"),
) -> AuditRunListResponse:
    """List recent audit runs for the current workspace."""
    runs = list_runs(limit=limit, root_path=state.settings.root_path)
    return AuditRunListResponse(runs=[_serialize_run(run) for run in runs])


@router.post("/runs", response_model=AuditRunSchema)
async def create_audit_run(
    payload: AuditRunCreateRequest,
    state: AppState = Depends(get_app_state),
) -> AuditRunSchema:
    """Create a new auditable session."""
    root_path = payload.root_path or state.settings.root_path
    run = create_run(
        name=payload.name,
        root_path=root_path,
        notes=payload.notes,
    )
    return _serialize_run(run)


@router.get("/runs/{run_id}", response_model=AuditRunSchema)
async def get_audit_run(
    run_id: int,
    state: AppState = Depends(get_app_state),
) -> AuditRunSchema:
    """Retrieve a single run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _validate_run_root(run, state)
    return _serialize_run(run)


@router.post("/runs/{run_id}/close", response_model=AuditRunSchema)
async def close_audit_run(
    run_id: int,
    payload: AuditRunCloseRequest,
    state: AppState = Depends(get_app_state),
) -> AuditRunSchema:
    """Mark a run as closed."""
    run = close_run(run_id, status=payload.status or "closed", notes=payload.notes)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _validate_run_root(run, state)
    return _serialize_run(run)


@router.get(
    "/runs/{run_id}/events",
    response_model=AuditEventListResponse,
)
async def list_audit_events(
    run_id: int,
    state: AppState = Depends(get_app_state),
    limit: int = Query(
        200, ge=1, le=500, description="Maximum number of events to return"
    ),
    after_id: int | None = Query(
        default=None, description="Return events with id greater than this value"
    ),
) -> AuditEventListResponse:
    """List events for a run in chronological order."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _validate_run_root(run, state)
    events = list_events(run_id, limit=limit, after_id=after_id)
    return AuditEventListResponse(events=[_serialize_event(event) for event in events])


@router.post(
    "/runs/{run_id}/events",
    response_model=AuditEventSchema,
)
async def append_audit_event(
    run_id: int,
    payload: AuditEventCreateRequest,
    state: AppState = Depends(get_app_state),
) -> AuditEventSchema:
    """Append a new event to a run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    _validate_run_root(run, state)

    try:
        event = append_event(
            run_id,
            type=payload.type,
            title=payload.title,
            detail=payload.detail,
            actor=payload.actor,
            phase=payload.phase,
            status=payload.status,
            ref=payload.ref,
            payload=payload.payload,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _serialize_event(event)
