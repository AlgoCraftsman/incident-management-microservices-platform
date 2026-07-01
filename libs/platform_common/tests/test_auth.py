from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from platform_common.auth import (
    GLOBAL_SCOPE,
    has_required_scope,
    parse_api_keys,
    require_api_key,
)


def test_parse_legacy_api_keys_grants_global_scope():
    principals = parse_api_keys("dev-platform-key, another-key")

    assert [principal.key for principal in principals] == ["dev-platform-key", "another-key"]
    assert principals[0].scopes == frozenset({GLOBAL_SCOPE})


def test_parse_structured_api_keys_with_scopes():
    principals = parse_api_keys(
        """
        [
          {"name": "incidents-client", "key": "incident-key", "scopes": ["incidents-service:access"]},
          {"name": "reader", "key": "status-key", "scopes": ["status-page-service:*"]}
        ]
        """
    )

    assert principals[0].name == "incidents-client"
    assert principals[0].scopes == frozenset({"incidents-service:access"})
    assert principals[1].scopes == frozenset({"status-page-service:*"})


def test_scope_matching_allows_global_and_service_wildcards():
    assert has_required_scope({"platform:*"}, {"incidents-service:access"}) is True
    assert has_required_scope({"incidents-service:*"}, {"incidents-service:access"}) is True
    assert has_required_scope({"alerts-service:access"}, {"incidents-service:access"}) is False


def test_dependency_returns_principal_for_authorized_key():
    dependency = require_api_key(
        parse_api_keys('[{"name": "incidents-client", "key": "incident-key", "scopes": ["incidents-service:*"]}]'),
        required_scopes={"incidents-service:access"},
    )

    principal = asyncio.run(dependency("incident-key"))

    assert principal.name == "incidents-client"


def test_dependency_rejects_valid_key_without_required_scope():
    dependency = require_api_key(
        parse_api_keys('[{"name": "alerts-client", "key": "alerts-key", "scopes": ["alerts-service:access"]}]'),
        required_scopes={"incidents-service:access"},
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(dependency("alerts-key"))

    assert exc.value.status_code == 403
