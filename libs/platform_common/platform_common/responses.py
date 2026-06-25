from __future__ import annotations

from fastapi import Response


def set_duplicate_warning(response: Response, message: str) -> None:
    response.headers["X-Duplicate-Warning"] = message

