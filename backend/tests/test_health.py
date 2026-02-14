"""Tests for health endpoint."""

from unittest.mock import patch


class TestHealthEndpoint:
    async def test_health_ok_when_configured(self, client):
        with patch("app.routes.health.settings") as mock_settings:
            mock_settings.anthropic_configured = True
            resp = await client.get("/api/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["anthropic_configured"] is True
        assert "version" in data

    async def test_health_degraded_when_no_key(self, client):
        with patch("app.routes.health.settings") as mock_settings:
            mock_settings.anthropic_configured = False
            resp = await client.get("/api/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["anthropic_configured"] is False

    async def test_health_response_shape(self, client):
        with patch("app.routes.health.settings") as mock_settings:
            mock_settings.anthropic_configured = True
            resp = await client.get("/api/health")

        data = resp.json()
        assert set(data.keys()) == {"status", "version", "anthropic_configured"}
