"""Tests for /api/v1/todos covering every scenario in specs/todos/spec.md."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import future_iso


pytestmark = pytest.mark.asyncio


# ---------- Create ----------


async def test_create_todo_happy_path(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    payload = {
        "title": "Prepare Architecture Document",
        "description": "Write TDD for Todo system",
        "priority": 3,
        "dueDate": future_iso(),
    }
    resp = await client.post("/api/v1/todos", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == payload["title"]
    assert body["status"] == "Pending"
    assert body["priority"] == 3
    assert body["id"]
    assert body["createdAt"]


async def test_create_todo_default_status_is_pending(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.post(
        "/api/v1/todos",
        json={"title": "No status"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "Pending"


async def test_create_todo_rejects_missing_title(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.post("/api/v1/todos", json={"priority": 2}, headers=headers)
    assert resp.status_code == 422


async def test_create_todo_rejects_empty_title(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.post("/api/v1/todos", json={"title": ""}, headers=headers)
    assert resp.status_code == 422


async def test_create_todo_rejects_title_over_200(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.post(
        "/api/v1/todos", json={"title": "x" * 201}, headers=headers
    )
    assert resp.status_code == 422


async def test_create_todo_rejects_priority_out_of_range(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    for bad in (0, 4, 99):
        resp = await client.post(
            "/api/v1/todos",
            json={"title": "x", "priority": bad},
            headers=headers,
        )
        assert resp.status_code == 422, (bad, resp.text)


async def test_create_todo_rejects_past_due_date(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    past = (future_iso(0))  # not actually past; we'll use a clearly past date
    from datetime import datetime, timezone, timedelta

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = await client.post(
        "/api/v1/todos",
        json={"title": "x", "dueDate": past},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_create_todo_rejects_unknown_status(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.post(
        "/api/v1/todos",
        json={"title": "x", "status": "Done"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------- List ----------


async def test_list_todos_returns_only_own(client: AsyncClient, auth_headers):
    a = await auth_headers("alice@example.com")
    b = await auth_headers("bob@example.com")
    await client.post("/api/v1/todos", json={"title": "alice 1"}, headers=a)
    await client.post("/api/v1/todos", json={"title": "alice 2"}, headers=a)
    await client.post("/api/v1/todos", json={"title": "bob 1"}, headers=b)

    resp = await client.get("/api/v1/todos", headers=a)
    assert resp.status_code == 200
    titles = sorted(t["title"] for t in resp.json())
    assert titles == ["alice 1", "alice 2"]


async def test_list_todos_filter_by_status(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    r1 = await client.post("/api/v1/todos", json={"title": "a"}, headers=headers)
    todo_id = r1.json()["id"]
    await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "InProgress"},
        headers=headers,
    )
    await client.post("/api/v1/todos", json={"title": "b"}, headers=headers)

    resp = await client.get("/api/v1/todos?status=Pending", headers=headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["b"]

    resp = await client.get("/api/v1/todos?status=InProgress", headers=headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["a"]


async def test_list_todos_filter_by_priority(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    await client.post("/api/v1/todos", json={"title": "p1", "priority": 1}, headers=headers)
    await client.post("/api/v1/todos", json={"title": "p3", "priority": 3}, headers=headers)

    resp = await client.get("/api/v1/todos?priority=3", headers=headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["p3"]


async def test_list_todos_rejects_invalid_status_filter(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.get("/api/v1/todos?status=Done", headers=headers)
    assert resp.status_code == 400


async def test_list_todos_rejects_invalid_priority_filter(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.get("/api/v1/todos?priority=5", headers=headers)
    assert resp.status_code == 422


async def test_list_todos_combines_filters(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    r1 = await client.post(
        "/api/v1/todos", json={"title": "x", "priority": 3}, headers=headers
    )
    todo_id = r1.json()["id"]
    await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "InProgress"},
        headers=headers,
    )
    await client.post(
        "/api/v1/todos", json={"title": "y", "priority": 3}, headers=headers
    )
    await client.post(
        "/api/v1/todos", json={"title": "z", "priority": 1}, headers=headers
    )

    resp = await client.get(
        "/api/v1/todos?status=Pending&priority=3", headers=headers
    )
    titles = [t["title"] for t in resp.json()]
    assert titles == ["y"]


# ---------- Get by id ----------


async def test_get_todo_own(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    created = await client.post(
        "/api/v1/todos", json={"title": "x"}, headers=headers
    )
    todo_id = created.json()["id"]

    resp = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "x"


async def test_get_todo_other_user_returns_404(client: AsyncClient, auth_headers):
    a = await auth_headers("alice@example.com")
    b = await auth_headers("bob@example.com")
    created = await client.post(
        "/api/v1/todos", json={"title": "x"}, headers=a
    )
    todo_id = created.json()["id"]

    resp = await client.get(f"/api/v1/todos/{todo_id}", headers=b)
    assert resp.status_code == 404


async def test_get_todo_unknown_id_returns_404(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    resp = await client.get(f"/api/v1/todos/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


# ---------- Update ----------


async def test_update_todo_happy_path(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    created = await client.post(
        "/api/v1/todos", json={"title": "old"}, headers=headers
    )
    todo_id = created.json()["id"]

    resp = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Prepare Architecture Document", "status": "InProgress", "priority": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Todo updated successfully"}

    got = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    assert got.json()["status"] == "InProgress"
    assert got.json()["title"] == "Prepare Architecture Document"


async def test_update_todo_rejects_validation_errors(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    created = await client.post("/api/v1/todos", json={"title": "x"}, headers=headers)
    todo_id = created.json()["id"]

    # title > 200
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "x" * 201},
        headers=headers,
    )
    assert r.status_code == 422

    # priority out of range
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"priority": 9},
        headers=headers,
    )
    assert r.status_code == 422

    # invalid status
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "Done"},
        headers=headers,
    )
    assert r.status_code == 422

    # past due date
    from datetime import datetime, timezone, timedelta

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"dueDate": past},
        headers=headers,
    )
    assert r.status_code == 422


async def test_update_rejects_completed_to_pending(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    created = await client.post("/api/v1/todos", json={"title": "x"}, headers=headers)
    todo_id = created.json()["id"]

    # Drive the todo to Completed via valid transitions.
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "InProgress"},
        headers=headers,
    )
    assert r.status_code == 200
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "Completed"},
        headers=headers,
    )
    assert r.status_code == 200

    # Reverting to Pending must be rejected.
    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"status": "Pending"},
        headers=headers,
    )
    assert r.status_code == 400


async def test_update_other_user_returns_404(client: AsyncClient, auth_headers):
    a = await auth_headers("alice@example.com")
    b = await auth_headers("bob@example.com")
    created = await client.post("/api/v1/todos", json={"title": "x"}, headers=a)
    todo_id = created.json()["id"]

    r = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "hijack"},
        headers=b,
    )
    assert r.status_code == 404

    # Confirm alice's todo was NOT modified.
    got = await client.get(f"/api/v1/todos/{todo_id}", headers=a)
    assert got.json()["title"] == "x"


# ---------- Delete ----------


async def test_delete_todo_own(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    created = await client.post("/api/v1/todos", json={"title": "x"}, headers=headers)
    todo_id = created.json()["id"]

    r = await client.delete(f"/api/v1/todos/{todo_id}", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"message": "Todo deleted successfully"}

    get = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    assert get.status_code == 404


async def test_delete_other_user_returns_404(client: AsyncClient, auth_headers):
    a = await auth_headers("alice@example.com")
    b = await auth_headers("bob@example.com")
    created = await client.post("/api/v1/todos", json={"title": "x"}, headers=a)
    todo_id = created.json()["id"]

    r = await client.delete(f"/api/v1/todos/{todo_id}", headers=b)
    assert r.status_code == 404

    got = await client.get(f"/api/v1/todos/{todo_id}", headers=a)
    assert got.status_code == 200


async def test_delete_unknown_id_returns_404(client: AsyncClient, auth_headers):
    headers = await auth_headers("alice@example.com")
    r = await client.delete(f"/api/v1/todos/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404
