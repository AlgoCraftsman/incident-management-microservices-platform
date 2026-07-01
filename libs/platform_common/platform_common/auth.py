from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import Header, HTTPException, status


GLOBAL_SCOPE = "platform:*"


@dataclass(frozen=True)
class APIKeyPrincipal:
    name: str
    key: str
    scopes: frozenset[str]


def parse_api_keys(raw_value: str | None) -> tuple[APIKeyPrincipal, ...]:
    if not raw_value:
        return ()
    value = raw_value.strip()
    if not value:
        return ()
    if value.startswith("[") or value.startswith("{"):
        return parse_structured_api_keys(value)
    return tuple(
        APIKeyPrincipal(name=f"legacy-key-{index}", key=item.strip(), scopes=frozenset({GLOBAL_SCOPE}))
        for index, item in enumerate(value.split(","), start=1)
        if item.strip()
    )


def parse_structured_api_keys(raw_value: str) -> tuple[APIKeyPrincipal, ...]:
    parsed = json.loads(raw_value)
    entries = parsed.get("keys", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(entries, list):
        raise ValueError("Structured API key configuration must be a JSON list or an object with a keys list")

    principals: list[APIKeyPrincipal] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError("Each structured API key entry must be an object")
        key = str(entry.get("key", "")).strip()
        if not key:
            raise ValueError("Each structured API key entry must include a non-empty key")
        raw_scopes = entry.get("scopes") or []
        if not isinstance(raw_scopes, list) or not all(isinstance(scope, str) for scope in raw_scopes):
            raise ValueError("Structured API key scopes must be a list of strings")
        name = str(entry.get("name") or f"api-key-{index}")
        principals.append(
            APIKeyPrincipal(
                name=name,
                key=key,
                scopes=frozenset(scope.strip() for scope in raw_scopes if scope.strip()),
            )
        )
    return tuple(principals)


def require_api_key(
    valid_keys: Iterable[APIKeyPrincipal],
    *,
    required_scopes: Iterable[str] | None = None,
):
    principals = tuple(valid_keys)
    scopes = frozenset(required_scopes or ())

    async def dependency(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> APIKeyPrincipal:
        if not principals:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API key authentication is not configured",
            )
        principal = find_principal(principals, x_api_key)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
        if scopes and not has_required_scope(principal.scopes, scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key is not authorized for this service",
            )
        return principal

    return dependency


def find_principal(principals: Iterable[APIKeyPrincipal], candidate: str | None) -> APIKeyPrincipal | None:
    if not candidate:
        return None
    for principal in principals:
        if secrets.compare_digest(candidate, principal.key):
            return principal
    return None


def has_required_scope(granted_scopes: Iterable[str], required_scopes: Iterable[str]) -> bool:
    grants = frozenset(granted_scopes)
    for required in required_scopes:
        if required in grants or "*" in grants or GLOBAL_SCOPE in grants:
            return True
        namespace = required.split(":", maxsplit=1)[0]
        if f"{namespace}:*" in grants:
            return True
    return False
