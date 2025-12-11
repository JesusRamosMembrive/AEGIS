# SPDX-License-Identifier: MIT
"""Persistencia de reportes de linters y notificaciones en SQLite."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from sqlmodel import Session, select, desc

from ..database import get_engine, init_db
from ..models import LinterReportDB, NotificationDB
from .report_schema import (
    CheckStatus,
    LintersReport,
    Severity,
    report_from_dict,
    report_to_dict,
)


def _normalize_root(root: Optional[str | Path]) -> Optional[str]:
    if root is None:
        return None
    return str(Path(root).expanduser().resolve())


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def _safe_check_status(value: Any) -> CheckStatus:
    try:
        return CheckStatus(value)
    except Exception:
        return CheckStatus.PASS


def _safe_severity(value: Any) -> Severity:
    try:
        return Severity(value)
    except Exception:
        return Severity.INFO


def _coerce_int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(float(value))
            except ValueError:
                return default
    return default


@dataclass(frozen=True)
class StoredLintersReport:
    """Representa un reporte almacenado con metadatos."""

    id: int
    generated_at: datetime
    root_path: str
    overall_status: CheckStatus
    issues_total: int
    critical_issues: int
    report: LintersReport


@dataclass(frozen=True)
class StoredNotification:
    """Representa una notificación persistida."""

    id: int
    created_at: datetime
    channel: str
    severity: Severity
    title: str
    message: str
    payload: Optional[Dict[str, Any]]
    root_path: Optional[str]
    read: bool


def record_linters_report(
    report: LintersReport, *, env: Optional[Mapping[str, str]] = None
) -> int:
    """Inserta un nuevo reporte de linters en la base de datos."""
    payload = report_to_dict(report)
    summary = payload.get("summary", {})
    overall_status = summary.get("overall_status", CheckStatus.PASS.value)
    issues_total = _coerce_int(summary.get("issues_total", 0), default=0)
    critical_issues = _coerce_int(summary.get("critical_issues", 0), default=0)

    engine = get_engine(_normalize_path_map(env))
    init_db(engine)

    with Session(engine) as session:
        db_report = LinterReportDB(
            generated_at=datetime.now(timezone.utc), # report.generated_at string? handle coercion
            root_path=_normalize_root(payload.get("root_path")) or "",
            overall_status=overall_status,
            issues_total=issues_total,
            critical_issues=critical_issues,
            payload=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        session.add(db_report)
        session.commit()
        session.refresh(db_report)
        return db_report.id or 0


def _db_to_report(db_item: LinterReportDB) -> StoredLintersReport:
    payload = json.loads(db_item.payload)
    return StoredLintersReport(
        id=db_item.id or 0,
        generated_at=db_item.generated_at,
        root_path=db_item.root_path,
        overall_status=_safe_check_status(db_item.overall_status),
        issues_total=_coerce_int(db_item.issues_total),
        critical_issues=_coerce_int(db_item.critical_issues),
        report=report_from_dict(payload),
    )


def get_linters_report(
    report_id: int, *, env: Optional[Mapping[str, str]] = None
) -> Optional[StoredLintersReport]:
    """Obtiene un reporte por ID."""
    engine = get_engine(_normalize_path_map(env))
    with Session(engine) as session:
        item = session.get(LinterReportDB, report_id)
        if not item:
            return None
        return _db_to_report(item)


def get_latest_linters_report(
    *,
    env: Optional[Mapping[str, str]] = None,
    root_path: Optional[str | Path] = None,
) -> Optional[StoredLintersReport]:
    """Obtiene el reporte más reciente, opcionalmente filtrado por root."""
    engine = get_engine(_normalize_path_map(env))
    normalized_root = _normalize_root(root_path)
    
    with Session(engine) as session:
        statement = select(LinterReportDB).order_by(desc(LinterReportDB.generated_at)).limit(1)
        if normalized_root:
            statement = statement.where(LinterReportDB.root_path == normalized_root)
        
        result = session.exec(statement).first()
        
        if not result:
            return None
        return _db_to_report(result)


def list_linters_reports(
    *,
    limit: int = 20,
    offset: int = 0,
    env: Optional[Mapping[str, str]] = None,
    root_path: Optional[str | Path] = None,
) -> List[StoredLintersReport]:
    """Lista reportes ordenados por fecha de creación descendente."""
    normalized_root = _normalize_root(root_path)
    engine = get_engine(_normalize_path_map(env))

    with Session(engine) as session:
        statement = select(LinterReportDB)
        if normalized_root:
            statement = statement.where(LinterReportDB.root_path == normalized_root)
        
        statement = statement.order_by(desc(LinterReportDB.generated_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()
        
        return [_db_to_report(item) for item in results]


def record_notification(
    *,
    channel: str,
    severity: Severity,
    title: str,
    message: str,
    root_path: Optional[str | Path] = None,
    payload: Optional[Dict[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> int:
    """Almacena una notificación vinculada al ecosistema de linters."""
    created_at = datetime.now(timezone.utc).isoformat()
    serialized_payload = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if payload
        else None
    )
    normalized_root = _normalize_root(root_path)

    engine = get_engine(_normalize_path_map(env))
    init_db(engine)

    with Session(engine) as session:
        notif = NotificationDB(
            created_at=datetime.now(timezone.utc),
            channel=channel,
            severity=severity.value,
            title=title,
            message=message,
            payload=serialized_payload,
            root_path=normalized_root,
            read=False
        )
        session.add(notif)
        session.commit()
        session.refresh(notif)
        return notif.id or 0


def _db_to_notification(db_item: NotificationDB) -> StoredNotification:
    payload = json.loads(db_item.payload) if db_item.payload else None
    return StoredNotification(
        id=db_item.id or 0,
        created_at=db_item.created_at,
        channel=db_item.channel,
        severity=_safe_severity(db_item.severity),
        title=db_item.title,
        message=db_item.message,
        payload=payload,
        root_path=db_item.root_path,
        read=db_item.read,
    )


def get_notification(
    notification_id: int,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[StoredNotification]:
    """Obtiene una notificación por ID."""
    with open_database(env) as connection:
        row = connection.execute(
            """
            SELECT id, created_at, channel, severity, title, message, payload, root_path, read
            FROM notifications
            WHERE id = ?
            """,
            (notification_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_notification(row)


def list_notifications(
    *,
    limit: int = 50,
    unread_only: bool = False,
    env: Optional[Mapping[str, str]] = None,
    root_path: Optional[str | Path] = None,
) -> List[StoredNotification]:
    """Recupera notificaciones ordenadas por fecha descendente."""
    normalized_root = _normalize_root(root_path)
    engine = get_engine(_normalize_path_map(env))

    with Session(engine) as session:
        statement = select(NotificationDB)
        if unread_only:
            statement = statement.where(NotificationDB.read == False)
        if normalized_root:
            from sqlmodel import or_
            statement = statement.where(or_(NotificationDB.root_path == None, NotificationDB.root_path == normalized_root)) # type: ignore
        
        statement = statement.order_by(desc(NotificationDB.created_at)).limit(limit)
        results = session.exec(statement).all()
        return [_db_to_notification(item) for item in results]


def mark_notification_read(
    notification_id: int,
    *,
    env: Optional[Mapping[str, str]] = None,
    read: bool = True,
) -> bool:
    """Actualiza el estado de leído de una notificación."""
    engine = get_engine(_normalize_path_map(env))
    with Session(engine) as session:
        notif = session.get(NotificationDB, notification_id)
        if not notif:
            return False
        
        notif.read = read
        session.add(notif)
        session.commit()
        return True
