"""Tests covering specs/auth/spec.md."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_request_without_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/todos")
    assert resp.status_code == 401


async def test_request_with_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/todos", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401


async def test_request_with_valid_token_works(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.get("/api/v1/todos", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_listing_returns_only_own_todos(client: AsyncClient, auth_headers):
    a = await auth_headers("alice@example.com")
    b = await auth_headers("bob@example.com")
    await client.post("/api/v1/todos", json={"title": "alice todo"}, headers=a)
    await client.post("/api/v1/todos", json={"title": "bob todo"}, headers=b)

    alice = (await client.get("/api/v1/todos", headers=a)).json()
    bob = (await client.get("/api/v1/todos", headers=b)).json()

    assert {t["title"] for t in alice} == {"alice todo"}
    assert {t["title"] for t in bob} == {"bob todo"}


async def test_invalid_payload_rejected_before_db_access(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    # Invalid status should be rejected by Pydantic before any DB call.
    resp = await client.post(
        "/api/v1/todos",
        json={"title": "x", "status": "Done"},
        headers=headers,
    )
    assert resp.status_code == 422

    # Listing after this should be empty (no partial writes).
    listing = await client.get("/api/v1/todos", headers=headers)
    assert listing.json() == []


async def test_register_and_login_flow(client: AsyncClient):
    # Register
    resp = await client.post(
        "/auth/register",
        json={
            "name": "Alice",
            "email": "alice-new@example.com",
            "password": "Password123!",
        },
    )
    assert resp.status_code == 201, resp.text

    # Login via the OAuth2 form endpoint
    resp = await client.post(
        "/auth/token",
        data={"username": "alice-new@example.com", "password": "Password123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    # Use the issued token to call a protected endpoint
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = await client.get("/api/v1/todos", headers=headers)
    assert resp.status_code == 200


async def test_register_rejects_duplicate_email(client: AsyncClient):
    payload = {
        "name": "Alice",
        "email": "dup@example.com",
        "password": "Password123!",
    }
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 409
