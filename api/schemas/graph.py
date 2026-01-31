"""Pydantic schemas for graph API endpoints."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Node types in the knowledge graph."""

    PERSON = "Person"
    SKILL = "Skill"
    COMPANY = "Company"
    POSITION = "Position"
    EXPERIENCE = "Experience"
    UNIVERSITY = "University"
    DEGREE = "Degree"
    EDUCATION = "Education"
    CERTIFICATION = "Certification"
    PROJECT = "Project"
    JOB_POSTING = "JobPosting"
    REQUIREMENT = "Requirement"
    RESPONSIBILITY = "Responsibility"
    COVER_LETTER = "CoverLetter"
    DOCUMENT = "Document"


class RelationshipType(str, Enum):
    """Relationship types in the knowledge graph."""

    # Person relations
    HAS_SKILL = "HAS_SKILL"
    HAS_EXPERIENCE = "HAS_EXPERIENCE"
    HAS_EDUCATION = "HAS_EDUCATION"
    HAS_CERTIFICATION = "HAS_CERTIFICATION"
    WORKED_ON = "WORKED_ON"
    FROM_DOCUMENT = "FROM_DOCUMENT"

    # Experience relations
    AT_COMPANY = "AT_COMPANY"
    AS_POSITION = "AS_POSITION"
    USED_SKILL = "USED_SKILL"

    # Education relations
    AT_UNIVERSITY = "AT_UNIVERSITY"
    FOR_DEGREE = "FOR_DEGREE"

    # Project relations
    USES_SKILL = "USES_SKILL"

    # Job posting relations
    REQUIRES_SKILL = "REQUIRES_SKILL"
    HAS_REQUIREMENT = "HAS_REQUIREMENT"
    HAS_RESPONSIBILITY = "HAS_RESPONSIBILITY"
    FOR_POSITION = "FOR_POSITION"
    REQUIRES = "REQUIRES"

    # Legacy/alias relations
    WORKED_AT = "WORKED_AT"
    WORKS_AT = "WORKS_AT"
    EDUCATED_AT = "EDUCATED_AT"
    HAS_POSITION = "HAS_POSITION"
    HAS_DEGREE = "HAS_DEGREE"
    TARGETS = "TARGETS"


class GraphNodeData(BaseModel):
    """Data field for a graph node."""

    name: str
    type: NodeType
    description: Optional[str] = None
    level: Optional[str] = None
    years: Optional[str] = None
    institution: Optional[str] = None
    date: Optional[str] = None
    relevance_score: Optional[float] = None


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: int
    labels: list[str] = Field(default_factory=list)
    color: str = "#3b82f6"
    visible: bool = True
    data: GraphNodeData


class GraphLinkData(BaseModel):
    """Data field for a graph link."""

    label: Optional[str] = None
    weight: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class GraphLink(BaseModel):
    """A link/edge in the knowledge graph."""

    id: int
    relationship: RelationshipType
    color: str = "#94a3b8"
    source: int
    target: int
    visible: bool = True
    data: GraphLinkData = Field(default_factory=GraphLinkData)


class GraphData(BaseModel):
    """Complete graph data structure for the GraphViewer."""

    nodes: list[GraphNode] = Field(default_factory=list, max_length=100)
    links: list[GraphLink] = Field(default_factory=list)


class GraphQueryParams(BaseModel):
    """Query parameters for graph endpoint."""

    types: Optional[list[str]] = Field(
        default=None, description="Filter by node types (CSV)"
    )
    max_nodes: int = Field(
        default=100, ge=1, le=100, description="Maximum nodes to return"
    )
    max_depth: Optional[int] = Field(
        default=None, ge=1, le=5, description="Maximum traversal depth"
    )


class GraphError(BaseModel):
    """Error response for graph endpoint."""

    error: dict[str, Any]


# Color mapping for node types
NODE_TYPE_COLORS = {
    NodeType.PERSON: "#3b82f6",  # blue
    NodeType.SKILL: "#10b981",  # green
    NodeType.COMPANY: "#f59e0b",  # amber
    NodeType.POSITION: "#8b5cf6",  # violet
    NodeType.EXPERIENCE: "#06b6d4",  # cyan
    NodeType.UNIVERSITY: "#ec4899",  # pink
    NodeType.DEGREE: "#f97316",  # orange
    NodeType.EDUCATION: "#6366f1",  # indigo
    NodeType.CERTIFICATION: "#14b8a6",  # teal
    NodeType.PROJECT: "#84cc16",  # lime
    NodeType.JOB_POSTING: "#ef4444",  # red
    NodeType.REQUIREMENT: "#64748b",  # slate
    NodeType.RESPONSIBILITY: "#a855f7",  # purple
    NodeType.COVER_LETTER: "#f43f5e",  # rose
    NodeType.DOCUMENT: "#6b7280",  # gray
}


def get_node_color(node_type: str) -> str:
    """Get color for a node type."""
    try:
        return NODE_TYPE_COLORS[NodeType(node_type)]
    except (KeyError, ValueError):
        return "#3b82f6"
