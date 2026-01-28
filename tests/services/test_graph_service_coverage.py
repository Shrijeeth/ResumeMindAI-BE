"""Coverage tests for graph service to reach 100%."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.graph_service import query_document_graph


@pytest.mark.asyncio
async def test_query_document_graph_with_node_types():
    """Test query_document_graph with node type filter."""
    user_id = "test-user"
    document_id = str(uuid4())
    node_types = ["Skill", "Company"]

    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_client.execute_query.return_value = mock_result

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=node_types,
            max_depth=3,
        )

        # Verify query was called
        mock_client.execute_query.assert_called_once()
        call_args = mock_client.execute_query.call_args
        assert call_args[0][0] == f"resume_kg_{user_id}"
        assert "Skill" in call_args[0][1]
        assert "Company" in call_args[0][1]


@pytest.mark.asyncio
async def test_query_document_graph_error_handling():
    """Test query_document_graph raises error on client error."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = AsyncMock()
    mock_client.execute_query.side_effect = Exception("DB error")

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        with pytest.raises(Exception, match="DB error"):
            await query_document_graph(
                user_id=user_id,
                document_id=document_id,
            )


@pytest.mark.asyncio
async def test_query_document_graph_parse_results():
    """Test query_document_graph parses results correctly."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = [
        {
            "n": {
                "id": 1,
                "labels": ["Skill"],
                "properties": {"name": "Python"},
            },
            "r": [
                {
                    "id": 1,
                    "type": "HAS_SKILL",
                    "start": 1,
                    "end": 2,
                    "properties": {},
                }
            ],
        }
    ]
    mock_client.execute_query.return_value = mock_result

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=document_id,
        )

        assert len(nodes) == 1
        assert nodes[0]["id"] == 1
        assert len(links) == 1
        assert links[0]["relationship"] == "HAS_SKILL"
