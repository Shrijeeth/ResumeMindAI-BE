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

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=node_types,
            max_depth=3,
        )

        # Verify query was called
        mock_client.select_graph.assert_called_once_with(f"resume_kg_{user_id}")
        mock_graph.query.assert_called_once()
        call_args = mock_graph.query.call_args
        assert "Skill" in call_args[0][0]
        assert "Company" in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_error_handling():
    """Test query_document_graph raises error on client error."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_graph.query.side_effect = Exception("DB error")
    mock_client.select_graph.return_value = mock_graph

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

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()

    # Create mock Node and Edge objects (actual FalkorDB format)
    mock_node = MagicMock()
    mock_node.id = 1
    mock_node.labels = ["Skill"]
    mock_node.properties = {"name": "Python"}

    mock_edge = MagicMock()
    mock_edge.id = 1
    mock_edge.type = "HAS_SKILL"
    mock_edge.src_node = 1
    mock_edge.dest_node = 2
    mock_edge.properties = {}

    mock_result.result_set = [
        [mock_node, [mock_edge]]  # List format: [node, relationships]
    ]
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=document_id,
        )

        assert len(nodes) == 1
        assert nodes[0]["id"] == 1
        assert len(links) == 1
        assert links[0]["relationship"] == "HAS_SKILL"


@pytest.mark.asyncio
async def test_query_document_graph_user_level_without_node_types():
    """Test query_document_graph for user-level graph without node types."""
    user_id = "test-user"

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=None,  # User-level query
            node_types=None,  # No node type filter
        )

        # Verify query was called
        mock_client.select_graph.assert_called_once_with(f"resume_kg_{user_id}")
        mock_graph.query.assert_called_once()


@pytest.mark.asyncio
async def test_query_document_graph_parse_error_handling():
    """Test query_document_graph handles parsing errors correctly."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()

    # Create a mock node that raises exception when accessing id
    mock_node = MagicMock()
    type(mock_node).id = property(
        lambda _: (_ for _ in ()).throw(Exception("Parse error"))
    )

    mock_result.result_set = [
        [mock_node, None]  # Node that raises on id access
    ]
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        with pytest.raises(Exception, match="Parse error"):
            await query_document_graph(
                user_id=user_id,
                document_id=document_id,
            )


@pytest.mark.asyncio
async def test_query_document_graph_invalid_node_types():
    """Test query_document_graph raises ValueError for invalid node types."""
    user_id = "test-user"
    document_id = str(uuid4())
    node_types = ["Skill; DROP ALL", "Company"]  # Invalid: contains semicolon

    mock_client = MagicMock()

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        with pytest.raises(ValueError, match="Invalid node type identifiers"):
            await query_document_graph(
                user_id=user_id,
                document_id=document_id,
                node_types=node_types,
            )


@pytest.mark.asyncio
async def test_query_document_graph_max_depth_one_with_types():
    """Test query_document_graph with max_depth=1 and node_types."""
    user_id = "test-user"
    document_id = str(uuid4())
    node_types = ["Skill"]

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=node_types,
            max_depth=1,
        )

        call_args = mock_graph.query.call_args
        # Should use single hop [r] not variable [r*1..]
        assert "-[r]->" in call_args[0][0]
        assert "[r*1.." not in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_max_depth_default_with_types():
    """Test query_document_graph with max_depth=0 and node_types (uses default)."""
    user_id = "test-user"
    document_id = str(uuid4())
    node_types = ["Skill"]

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=node_types,
            max_depth=0,
        )

        call_args = mock_graph.query.call_args
        # Should use default depth of 5
        assert "[r*1..5]" in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_max_depth_one_without_types():
    """Test query_document_graph with max_depth=1 and no node_types."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=None,
            max_depth=1,
        )

        call_args = mock_graph.query.call_args
        # Should use single hop [r] not variable [r*1..]
        assert "-[r]->" in call_args[0][0]
        assert "[r*1.." not in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_max_depth_default_without_types():
    """Test query_document_graph with max_depth=0 and no node_types (uses default)."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=None,
            max_depth=0,
        )

        call_args = mock_graph.query.call_args
        # Should use default depth of 5
        assert "[r*1..5]" in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_max_depth_greater_than_one_no_types():
    """Test query_document_graph with max_depth > 1 and no node_types."""
    user_id = "test-user"
    document_id = str(uuid4())

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        await query_document_graph(
            user_id=user_id,
            document_id=document_id,
            node_types=None,
            max_depth=3,
        )

        call_args = mock_graph.query.call_args
        # Should use variable hop [r*1..3]
        assert "[r*1..3]" in call_args[0][0]


@pytest.mark.asyncio
async def test_query_document_graph_with_target_node():
    """Test query_document_graph parses target node correctly."""
    user_id = "test-user"

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()

    # Create mock nodes - source and target are different
    mock_source_node = MagicMock()
    mock_source_node.id = 1
    mock_source_node.labels = ["Document"]
    mock_source_node.properties = {"name": "Resume"}

    mock_target_node = MagicMock()
    mock_target_node.id = 2
    mock_target_node.labels = ["Skill"]
    mock_target_node.properties = {"name": "Python"}

    mock_edge = MagicMock()
    mock_edge.id = 1
    mock_edge.type = "HAS_SKILL"
    mock_edge.src_node = 1
    mock_edge.dest_node = 2
    mock_edge.properties = {}

    # Record has 3 elements: source node, edge, target node
    mock_result.result_set = [[mock_source_node, mock_edge, mock_target_node]]
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=None,  # User-level query to get 3-element records
        )

        # Should have both source and target nodes
        assert len(nodes) == 2
        assert {n["id"] for n in nodes} == {1, 2}
        assert len(links) == 1
        assert links[0]["relationship"] == "HAS_SKILL"


@pytest.mark.asyncio
async def test_query_document_graph_user_level_with_node_types():
    """Test query_document_graph for user-level graph with node types."""
    user_id = "test-user"
    node_types = ["Skill", "Company"]

    mock_client = MagicMock()
    mock_graph = AsyncMock()
    mock_result = MagicMock()
    mock_result.result_set = []
    mock_graph.query.return_value = mock_result
    mock_client.select_graph.return_value = mock_graph

    with patch("services.graph_service.get_falkordb_client", return_value=mock_client):
        nodes, links = await query_document_graph(
            user_id=user_id,
            document_id=None,  # User-level query
            node_types=node_types,  # With node type filter
        )

        # Verify query was called
        mock_client.select_graph.assert_called_once_with(f"resume_kg_{user_id}")
        mock_graph.query.assert_called_once()

        # Validate query structure - should use WITH to chain properly
        call_args = mock_graph.query.call_args
        assert "WHERE n:Skill OR n:Company" in call_args[0][0]
        assert "WITH n" in call_args[0][0]
        assert "OPTIONAL MATCH (n)-[r]->(m)" in call_args[0][0]
