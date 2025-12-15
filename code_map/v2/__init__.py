# SPDX-License-Identifier: MIT
"""
AEGIS v2: Instance Map + Class Truth

This package implements the v2 architecture focused on:
- Instance extraction from composition roots
- Wiring detection between components
- Contract verification against runtime behavior
"""

from .models import (
    CompositionRoot,
    CreationPattern,
    InstanceGraph,
    InstanceInfo,
    InstanceNode,
    InstanceRole,
    LifecycleCall,
    LifecycleMethod,
    Location,
    WiringEdge,
    WiringInfo,
)
from .builder import GraphBuilder
from .storage import InstanceGraphStore, StoredInstanceGraph
from .service import InstanceGraphService

__all__ = [
    # Enums
    "CreationPattern",
    "InstanceRole",
    "LifecycleMethod",
    # Core models (Phase 1)
    "Location",
    "InstanceInfo",
    "WiringInfo",
    "LifecycleCall",
    "CompositionRoot",
    # Graph models (Phase 2)
    "InstanceNode",
    "WiringEdge",
    "InstanceGraph",
    # Builder (Phase 2)
    "GraphBuilder",
    # Storage & Service (Phase 5)
    "StoredInstanceGraph",
    "InstanceGraphStore",
    "InstanceGraphService",
]
