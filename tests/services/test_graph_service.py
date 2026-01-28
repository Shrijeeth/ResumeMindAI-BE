"""Unit tests for graph service layer."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from api.schemas.graph import NodeType, RelationshipType
from services.graph_service import (
    convert_to_graph_format,
    downsample_nodes,
    get_graph_data,
    prune_links,
)


class TestDownsampleNodes:
    """Tests for node downsampling logic."""

    def test_downsample_nodes_under_limit(self):
        """Test downsampling when node count is under limit."""
        nodes = [
            {"id": i, "properties": {"name": f"Node {i}", "relevance_score": 0.5}}
            for i in range(1, 51)
        ]
        document_id = str(uuid4())

        result = downsample_nodes(nodes, max_nodes=100, document_id=document_id)

        assert len(result) == 50

    def test_downsample_nodes_over_limit(self):
        """Test downsampling when node count exceeds limit."""
        nodes = [
            {
                "id": i,
                "properties": {
                    "name": f"Node {i}",
                    "relevance_score": 0.5 + (i % 10) * 0.05,
                },
            }
            for i in range(1, 151)
        ]
        document_id = str(uuid4())

        result = downsample_nodes(nodes, max_nodes=100, document_id=document_id)

        assert len(result) == 100

    def test_downsample_preserves_document_node(self):
        """Test that document node is always preserved."""
        document_id = str(uuid4())
        nodes = [
            {
                "id": 1,
                "properties": {
                    "name": "Document",
                    "document_id": document_id,
                    "relevance_score": 0.0,
                },
            },
            *[
                {
                    "id": i,
                    "properties": {"name": f"Node {i}", "relevance_score": 0.9},
                }
                for i in range(2, 102)
            ],
        ]

        result = downsample_nodes(nodes, max_nodes=10, document_id=document_id)

        # Document node should be in result
        document_node_ids = [
            n["id"]
            for n in result
            if n.get("properties", {}).get("document_id") == document_id
        ]
        assert len(document_node_ids) == 1
        assert document_node_ids[0] == 1


class TestPruneLinks:
    """Tests for link pruning logic."""

    def test_prune_links_keeps_valid_links(self):
        """Test that links between kept nodes are preserved."""
        links = [
            {"id": 1, "source": 1, "target": 2},
            {"id": 2, "source": 2, "target": 3},
            {"id": 3, "source": 3, "target": 4},
        ]
        kept_node_ids = {1, 2, 3}

        result = prune_links(links, kept_node_ids)

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_prune_links_removes_invalid_links(self):
        """Test that links to removed nodes are pruned."""
        links = [
            {"id": 1, "source": 1, "target": 2},
            {"id": 2, "source": 2, "target": 5},  # target not kept
            {"id": 3, "source": 6, "target": 3},  # source not kept
        ]
        kept_node_ids = {1, 2, 3}

        result = prune_links(links, kept_node_ids)

        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_prune_links_empty_result(self):
        """Test pruning when no links remain."""
        links = [
            {"id": 1, "source": 5, "target": 6},
            {"id": 2, "source": 7, "target": 8},
        ]
        kept_node_ids = {1, 2, 3}

        result = prune_links(links, kept_node_ids)

        assert len(result) == 0


class TestConvertToGraphFormat:
    """Tests for converting raw data to GraphData format."""

    def test_convert_nodes(self):
        """Test converting nodes to GraphData format."""
        nodes = [
            {
                "id": 1,
                "labels": ["Skill"],
                "properties": {
                    "name": "Python",
                    "relevance_score": 0.9,
                },
            }
        ]
        links = []

        result = convert_to_graph_format(nodes, links)

        assert len(result.nodes) == 1
        assert result.nodes[0].data.name == "Python"
        assert result.nodes[0].data.type == NodeType.SKILL
        assert result.nodes[0].color == "#10b981"

    def test_convert_links(self):
        """Test converting links to GraphData format."""
        nodes = [
            {
                "id": 1,
                "labels": ["Person"],
                "properties": {"name": "John"},
            },
            {
                "id": 2,
                "labels": ["Skill"],
                "properties": {"name": "Python"},
            },
        ]
        links = [
            {
                "id": 1,
                "relationship": "HAS_SKILL",
                "source": 1,
                "target": 2,
                "properties": {},
            }
        ]

        result = convert_to_graph_format(nodes, links)

        assert len(result.links) == 1
        assert result.links[0].relationship == RelationshipType.HAS_SKILL
        assert result.links[0].source == 1
        assert result.links[0].target == 2

    def test_convert_handles_invalid_relationships(self):
        """Test that invalid relationship types are skipped."""
        nodes = [
            {
                "id": 1,
                "labels": ["Person"],
                "properties": {"name": "John"},
            },
            {
                "id": 2,
                "labels": ["Skill"],
                "properties": {"name": "Python"},
            },
        ]
        links = [
            {
                "id": 1,
                "relationship": "INVALID_RELATIONSHIP",
                "source": 1,
                "target": 2,
                "properties": {},
            }
        ]

        result = convert_to_graph_format(nodes, links)

        # Invalid relationship should be skipped
        assert len(result.links) == 0


@pytest.mark.asyncio
class TestGetGraphData:
    """Tests for get_graph_data function."""

    async def test_get_graph_data_success(self):
        """Test successful graph data retrieval."""
        user_id = "test-user"
        document_id = str(uuid4())

        with patch("services.graph_service.query_document_graph") as mock_query:
            mock_query.return_value = (
                [
                    {
                        "id": 1,
                        "labels": ["Skill"],
                        "properties": {"name": "Python", "relevance_score": 0.9},
                    }
                ],
                [],
            )

            result = await get_graph_data(user_id, document_id)

            assert len(result.nodes) == 1
            assert result.nodes[0].data.name == "Python"

    async def test_get_graph_data_downsamples(self):
        """Test that graph data is downsampled when needed."""
        user_id = "test-user"
        document_id = str(uuid4())

        with patch("services.graph_service.query_document_graph") as mock_query:
            # Return 150 nodes
            nodes = [
                {
                    "id": i,
                    "labels": ["Skill"],
                    "properties": {"name": f"Skill {i}", "relevance_score": 0.5},
                }
                for i in range(1, 151)
            ]
            mock_query.return_value = (nodes, [])

            result = await get_graph_data(user_id, document_id, max_nodes=100)

            # Should be downsampled to 100
            assert len(result.nodes) == 100

    async def test_get_graph_data_prunes_links(self):
        """Test that links are pruned to kept nodes."""
        user_id = "test-user"
        document_id = str(uuid4())

        with patch("services.graph_service.query_document_graph") as mock_query:
            nodes = [
                {"id": 1, "labels": ["Skill"], "properties": {"name": "Skill 1"}},
                {"id": 2, "labels": ["Skill"], "properties": {"name": "Skill 2"}},
            ]
            links = [
                {
                    "id": 1,
                    "relationship": "HAS_SKILL",
                    "source": 1,
                    "target": 2,
                },
                {
                    "id": 2,
                    "relationship": "HAS_SKILL",
                    "source": 1,
                    "target": 3,
                },  # target not in nodes
            ]
            mock_query.return_value = (nodes, links)

            result = await get_graph_data(user_id, document_id)

            # Only the first link should remain
            assert len(result.links) == 1
            assert result.links[0].id == 1
