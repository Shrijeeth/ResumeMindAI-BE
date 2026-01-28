"""Unit tests for graph schemas."""

from api.schemas.graph import get_node_color


def test_get_node_color_valid_type():
    """Test getting color for valid node type."""
    color = get_node_color("Skill")
    assert color == "#10b981"


def test_get_node_color_invalid_type():
    """Test getting color for invalid node type returns default."""
    color = get_node_color("InvalidType")
    assert color == "#3b82f6"
