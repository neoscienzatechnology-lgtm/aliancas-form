"""Pipeline de visão computacional do FootScan (MVP 2D calibrado)."""

from .pipeline import (
    ProcessingError,
    process_capture,
    recompute_from_landmarks,
    render_overlay,
)

__all__ = [
    "ProcessingError",
    "process_capture",
    "recompute_from_landmarks",
    "render_overlay",
]
