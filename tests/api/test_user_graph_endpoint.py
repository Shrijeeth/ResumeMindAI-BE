"""Unit tests for user graph API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.schemas.graph import GraphData, NodeType
from app import app
from configs.postgres import get_db
from middlewares.auth import get_current_user


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = "test-user-id"
    return user


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


class TestUserGraphEndpoint:
    """Tests for GET /api/user/graph endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_graph_success(self, client, mock_user, mock_session):
        """Test successful user graph retrieval."""
        # Mock dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        with patch("services.graph_service.query_document_graph") as mock_query:
            with patch("services.graph_service.downsample_nodes") as mock_downsample:
                with patch("services.graph_service.prune_links") as mock_prune:
                    with patch(
                        "services.graph_service.convert_to_graph_format"
                    ) as mock_convert:
                        # Mock graph data
                        mock_graph_data = GraphData(
                            nodes=[
                                {
                                    "id": 1,
                                    "labels": ["Skill"],
                                    "color": "#10b981",
                                    "visible": True,
                                    "data": {
                                        "name": "Python",
                                        "type": NodeType.SKILL,
                                        "relevance_score": 0.9,
                                    },
                                }
                            ],
                            links=[],
                        )
                        mock_query.return_value = ([], [])
                        mock_downsample.return_value = []
                        mock_prune.return_value = []
                        mock_convert.return_value = mock_graph_data

                        response = client.get("/api/user/graph")

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert "nodes" in data
                        assert "links" in data
                        assert len(data["nodes"]) == 1
                        assert data["nodes"][0]["data"]["name"] == "Python"

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_invalid_node_type(
        self, client, mock_user, mock_session
    ):
        """Test user graph retrieval with invalid node type filter."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        response = client.get("/api/user/graph?types=InvalidType")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "BAD_REQUEST"

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_max_nodes_validation(
        self, client, mock_user, mock_session
    ):
        """Test user graph retrieval with max_nodes validation."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        # Test max_nodes > 100
        response = client.get("/api/user/graph?max_nodes=150")

        # FastAPI validation should reject this
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_max_depth_validation(
        self, client, mock_user, mock_session
    ):
        """Test user graph retrieval with max_depth validation."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        # Test max_depth > 5
        response = client.get("/api/user/graph?max_depth=10")

        # FastAPI validation should reject this
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_with_type_filter(
        self, client, mock_user, mock_session
    ):
        """Test user graph retrieval with node type filter."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        with patch("services.graph_service.query_document_graph") as mock_query:
            with patch("services.graph_service.downsample_nodes") as mock_downsample:
                with patch("services.graph_service.prune_links") as mock_prune:
                    with patch(
                        "services.graph_service.convert_to_graph_format"
                    ) as mock_convert:
                        mock_graph_data = GraphData(nodes=[], links=[])
                        mock_query.return_value = ([], [])
                        mock_downsample.return_value = []
                        mock_prune.return_value = []
                        mock_convert.return_value = mock_graph_data

                        response = client.get("/api/user/graph?types=Skill,Company")

                        assert response.status_code == status.HTTP_200_OK
                        # Verify node_types were passed correctly
                        mock_query.assert_called_once()
                        call_kwargs = mock_query.call_args[1]
                        assert "node_types" in call_kwargs
                        assert "Skill" in call_kwargs["node_types"]
                        assert "Company" in call_kwargs["node_types"]

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_empty_result(self, client, mock_user, mock_session):
        """Test user graph retrieval when no graph data exists."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        with patch("services.graph_service.query_document_graph") as mock_query:
            with patch("services.graph_service.downsample_nodes") as mock_downsample:
                with patch("services.graph_service.prune_links") as mock_prune:
                    with patch(
                        "services.graph_service.convert_to_graph_format"
                    ) as mock_convert:
                        mock_graph_data = GraphData(nodes=[], links=[])
                        mock_query.return_value = ([], [])
                        mock_downsample.return_value = []
                        mock_prune.return_value = []
                        mock_convert.return_value = mock_graph_data

                        response = client.get("/api/user/graph")

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["nodes"] == []
                        assert data["links"] == []

        app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_user_graph_server_error(self, client, mock_user, mock_session):
        """Test user graph retrieval when server error occurs."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_session

        with patch(
            "services.graph_service.get_graph_data",
            side_effect=Exception("DB error"),
        ):
            response = client.get("/api/user/graph")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "detail" in data
            assert data["detail"]["error"]["code"] == "INTERNAL"

        app.dependency_overrides = {}
