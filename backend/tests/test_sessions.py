"""Tests for session CRUD endpoints."""


class TestSessionCRUD:
    async def test_create_session(self, client):
        resp = await client.post("/api/sessions", json={"title": "Sprint Planning"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Sprint Planning"
        assert "id" in data
        assert "created_at" in data
        assert data["message_count"] == 0

    async def test_create_session_default_title(self, client):
        resp = await client.post("/api/sessions")
        assert resp.status_code == 201
        assert resp.json()["title"] == "Session 1"

    async def test_list_sessions_empty(self, client):
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_sessions_includes_created(self, client):
        await client.post("/api/sessions", json={"title": "A"})
        await client.post("/api/sessions", json={"title": "B"})
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()]
        assert "A" in titles
        assert "B" in titles

    async def test_get_session_by_id(self, client):
        create_resp = await client.post("/api/sessions", json={"title": "Test"})
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id
        assert resp.json()["title"] == "Test"

    async def test_get_session_not_found(self, client):
        resp = await client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    async def test_delete_session(self, client):
        create_resp = await client.post("/api/sessions", json={"title": "Delete Me"})
        session_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 404

    async def test_delete_session_not_found(self, client):
        resp = await client.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404
