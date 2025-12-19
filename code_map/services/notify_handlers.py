# SPDX-License-Identifier: MIT
"""
Sistema extensible de handlers para notificación de cambios externos.

Para agregar una nueva característica, solo hay que añadir un handler a la lista:

    from code_map.services.notify_handlers import CHANGE_HANDLERS

    class MiNuevoHandler(ChangeHandler):
        @property
        def name(self) -> str:
            return "mi_nuevo_handler"

        async def handle(self, state, result) -> None:
            # Lógica del handler
            pass

    CHANGE_HANDLERS.append(MiNuevoHandler())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..state import AppState

logger = logging.getLogger(__name__)


@dataclass
class NotifyResult:
    """Resultado del procesamiento de cambios externos."""

    processed: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = []


class ChangeHandler(ABC):
    """Interfaz base para handlers de cambios."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador único del handler."""
        ...

    @abstractmethod
    async def handle(self, state: "AppState", result: NotifyResult) -> None:
        """Ejecuta la lógica del handler."""
        ...


class SSEBroadcastHandler(ChangeHandler):
    """Notifica cambios a clientes SSE conectados."""

    @property
    def name(self) -> str:
        return "sse_broadcast"

    async def handle(self, state: "AppState", result: NotifyResult) -> None:
        if result.processed == 0:
            return

        # Extraer paths procesados
        updated_paths = [
            d["path"] for d in result.details if d.get("status") == "processed"
        ]
        if updated_paths:
            payload = {
                "updated": updated_paths,
                "deleted": [],
            }
            await state.event_queue.put(payload)
            logger.debug("SSE broadcast: %d files", len(updated_paths))


class LintersScheduleHandler(ChangeHandler):
    """Agenda ejecución de linters tras cambios."""

    @property
    def name(self) -> str:
        return "linters_schedule"

    async def handle(self, state: "AppState", result: NotifyResult) -> None:
        if result.processed == 0:
            return

        state.linters.schedule(pending_changes=result.processed)
        logger.debug("Linters scheduled after %d changes", result.processed)


class InsightsScheduleHandler(ChangeHandler):
    """Agenda generación de insights tras cambios."""

    @property
    def name(self) -> str:
        return "insights_schedule"

    async def handle(self, state: "AppState", result: NotifyResult) -> None:
        if result.processed == 0:
            return

        state.insights.schedule()
        logger.debug("Insights scheduled after %d changes", result.processed)


# =============================================================================
# Lista extensible de handlers
# Para agregar nuevas características, solo hay que añadir un handler aquí.
# =============================================================================

CHANGE_HANDLERS: List[ChangeHandler] = [
    SSEBroadcastHandler(),
    LintersScheduleHandler(),
    InsightsScheduleHandler(),
]


async def run_all_handlers(state: "AppState", result: NotifyResult) -> List[str]:
    """
    Ejecuta todos los handlers registrados.

    Returns:
        Lista de nombres de handlers ejecutados.
    """
    triggered: List[str] = []

    for handler in CHANGE_HANDLERS:
        try:
            await handler.handle(state, result)
            triggered.append(handler.name)
            logger.debug("Handler '%s' executed successfully", handler.name)
        except Exception as e:
            logger.error("Handler '%s' failed: %s", handler.name, e)
            # Continuar con los demás handlers

    return triggered
