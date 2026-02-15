"""
API integration tests.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        response = await client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "securepassword123"}
        await client.post("/auth/register", json=payload)
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient):
        await client.post("/auth/register", json={
            "email": "login@example.com",
            "password": "securepassword123",
        })
        response = await client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "securepassword123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/auth/register", json={
            "email": "wrong@example.com",
            "password": "securepassword123",
        })
        response = await client.post("/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me(self, auth_client: AsyncClient):
        response = await auth_client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401


class TestProjectsAPI:
    @pytest.mark.asyncio
    async def test_create_project(self, auth_client: AsyncClient):
        response = await auth_client.post("/projects/", json={
            "name": "Test Project",
            "description": "A test project",
            "region": "us-east-1",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["status"] == "created"

    @pytest.mark.asyncio
    async def test_list_projects(self, auth_client: AsyncClient):
        await auth_client.post("/projects/", json={"name": "P1"})
        await auth_client.post("/projects/", json={"name": "P2"})

        response = await auth_client.get("/projects/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_project(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/projects/", json={"name": "Get Me"})
        project_id = create_resp.json()["id"]

        response = await auth_client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, auth_client: AsyncClient):
        response = await auth_client.get("/projects/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/projects/", json={"name": "Delete Me"})
        project_id = create_resp.json()["id"]

        response = await auth_client.delete(f"/projects/{project_id}")
        assert response.status_code == 204

        # Verify deleted
        response = await auth_client.get(f"/projects/{project_id}")
        assert response.status_code == 404


class TestConfigAPI:
    @pytest.mark.asyncio
    async def test_get_default_config(self, auth_client: AsyncClient):
        response = await auth_client.get("/config/")
        assert response.status_code == 200
        data = response.json()
        assert data["default_region"] == "us-east-1"
        assert data["default_vpc"] is True

    @pytest.mark.asyncio
    async def test_update_config(self, auth_client: AsyncClient):
        response = await auth_client.put("/config/", json={
            "default_region": "eu-west-1",
            "default_vpc": False,
            "naming_convention": "snake_case",
            "tags": {"env": "dev"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["default_region"] == "eu-west-1"

    @pytest.mark.asyncio
    async def test_aws_credentials_lifecycle(self, auth_client: AsyncClient):
        # Check no credentials
        response = await auth_client.get("/config/aws-credentials/status")
        assert response.json()["configured"] is False

        # Set credentials
        response = await auth_client.put("/config/aws-credentials", json={
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        })
        assert response.status_code == 200

        # Check credentials set
        response = await auth_client.get("/config/aws-credentials/status")
        assert response.json()["configured"] is True

        # Delete credentials
        response = await auth_client.delete("/config/aws-credentials")
        assert response.status_code == 200

        # Verify deleted
        response = await auth_client.get("/config/aws-credentials/status")
        assert response.json()["configured"] is False
