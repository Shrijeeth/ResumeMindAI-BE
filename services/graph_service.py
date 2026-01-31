"""Service layer for querying and processing graph data from FalkorDB.

This module provides functions to:
- Query graph data for a specific document
- Filter nodes by type
- Downsample graphs to enforce node limits
- Prune links to retained node sets
"""

import logging
import re
from typing import Any, Optional

from api.schemas.graph import (
    GraphData,
    GraphLink,
    GraphLinkData,
    GraphNode,
    GraphNodeData,
    NodeType,
    RelationshipType,
    get_node_color,
)
from configs.falkordb import get_falkordb_client

# Valid Cypher identifier pattern (labels, types)
_CYPHER_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

logger = logging.getLogger(__name__)


async def query_document_graph(
    user_id: str,
    document_id: Optional[str] = None,
    node_types: Optional[list[str]] = None,
    max_depth: Optional[int] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Query graph data from FalkorDB for a user or document.

    Args:
        user_id: User ID for graph namespacing
        document_id: Optional document UUID to query (None for user-level graph)
        node_types: Optional list of node types to filter
        max_depth: Optional maximum traversal depth

    Returns:
        tuple: (nodes, links) as lists of dictionaries

    Raises:
        RuntimeError: If FalkorDB client is not initialized
    """
    client = await get_falkordb_client()
    graph_name = f"resume_kg_{user_id}"

    # Build Cypher query
    if document_id:
        # Document-scoped query (legacy behavior)
        query = """
        MATCH (d:Document {document_id: $document_id})
        """
        params = {"document_id": document_id}
    else:
        # User-level query - aggregate across all documents
        query = "MATCH (n) "
        params = {}

    if node_types:
        # Validate node_types to prevent Cypher injection
        invalid_types = [t for t in node_types if not _CYPHER_ID_PATTERN.match(t)]
        if invalid_types:
            raise ValueError(
                f"Invalid node type identifiers: {invalid_types}. "
                "Node types must match Cypher label syntax: "
                "start with letter, followed by letters, digits, or underscores."
            )
        type_filter = " OR ".join([f"n:{t}" for t in node_types])
        if document_id:
            # Document-scoped query with node type filter
            if max_depth == 1:
                query += f"""
                OPTIONAL MATCH (d)-[r]->(n)
                WHERE {type_filter}
                RETURN DISTINCT n, r
                """
            elif max_depth and max_depth > 1:
                query += f"""
                OPTIONAL MATCH (d)-[r*1..{max_depth}]->(n)
                WHERE {type_filter}
                RETURN DISTINCT n, r
                """
            else:
                # max_depth is None or 0, use default depth of 5
                query += f"""
                OPTIONAL MATCH (d)-[r*1..5]->(n)
                WHERE {type_filter}
                RETURN DISTINCT n, r
                """
        else:
            # User-level query with node type filter - use WITH to chain properly
            query += f"WHERE {type_filter} WITH n "
    else:
        if document_id:
            # Document-scoped query without node type filter
            if max_depth == 1:
                query += """
                OPTIONAL MATCH (d)-[r]->(n)
                RETURN DISTINCT n, r
                """
            elif max_depth and max_depth > 1:
                query += f"""
                OPTIONAL MATCH (d)-[r*1..{max_depth}]->(n)
                RETURN DISTINCT n, r
                """
            else:
                # max_depth is None or 0, use default depth of 5
                query += """
                OPTIONAL MATCH (d)-[r*1..5]->(n)
                RETURN DISTINCT n, r
                """
        else:
            query += " "

    # For user-level queries, just return all nodes and relationships
    if not document_id:
        query += """
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        """

    # Execute query
    try:
        graph = client.select_graph(graph_name)
        result = await graph.query(query, params)
    except Exception as e:
        logger.error(f"Error querying graph for user {user_id}: {e}")
        raise

    # Parse results
    nodes = []
    links = []
    node_map = {}
    seen_rel_ids = set()

    for record in result.result_set:
        # Parse nodes (first element in record)
        node = record[0] if len(record) > 0 else None
        if node:
            node_id = getattr(node, "id", None)
            if node_id is not None and node_id not in node_map:
                node_map[node_id] = {
                    "id": node_id,
                    "labels": getattr(node, "labels", []),
                    "properties": getattr(node, "properties", {}),
                }
                nodes.append(node_map[node_id])

        # Parse relationships (second element in record)
        rel_data = record[1] if len(record) > 1 else None
        if rel_data:
            relationships = rel_data if isinstance(rel_data, list) else [rel_data]
            for rel in relationships:
                if rel:
                    # Handle FalkorDB Edge object attributes
                    source = getattr(rel, "src_node", None) or getattr(
                        rel, "start", None
                    )
                    target = getattr(rel, "dest_node", None) or getattr(
                        rel, "end", None
                    )
                    rel_type = getattr(rel, "type", None) or getattr(
                        rel, "relation", None
                    )
                    rel_id = getattr(rel, "id", None)
                    # Handle falsy but valid IDs (e.g., 0)
                    if source and target and rel_type and rel_id is not None:
                        if rel_id not in seen_rel_ids:
                            seen_rel_ids.add(rel_id)
                            links.append(
                                {
                                    "id": rel_id,
                                    "relationship": rel_type,
                                    "source": source,
                                    "target": target,
                                    "properties": getattr(rel, "properties", {}),
                                }
                            )

        # Parse target node (third element in record) - ensure target nodes are included
        target_node = record[2] if len(record) > 2 else None
        if target_node:
            target_node_id = getattr(target_node, "id", None)
            if target_node_id is not None and target_node_id not in node_map:
                node_map[target_node_id] = {
                    "id": target_node_id,
                    "labels": getattr(target_node, "labels", []),
                    "properties": getattr(target_node, "properties", {}),
                }
                nodes.append(node_map[target_node_id])

    return nodes, links


def downsample_nodes(
    nodes: list[dict[str, Any]],
    max_nodes: int,
    document_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Downsample nodes to enforce max_nodes limit.

    Strategy:
    1. For document-level graphs: Always keep the Document node
    2. For user-level graphs: Prioritize nodes by relevance_score (if available)
    3. Then by degree centrality (number of connections)
    4. Finally by recency (date field if available)

    Args:
        nodes: List of node dictionaries
        max_nodes: Maximum nodes to return
        document_id: Optional document ID to prioritize (None for user-level graphs)

    Returns:
        list: Downsampled nodes
    """
    if len(nodes) <= max_nodes:
        return nodes

    # For user-level graphs, just sort by priority
    if not document_id:
        # Sort by relevance_score, then by degree, then by recency
        def sort_key(node: dict[str, Any]) -> tuple:
            props = node.get("properties", {})
            relevance = props.get("relevance_score", 0)
            # Count connections (we'll approximate this)
            degree = props.get("degree", 0)
            # Try to get date
            date = props.get("date", "")
            return (-relevance, -degree, date)

        return sorted(nodes, key=sort_key)[:max_nodes]

    # Document-level graph - separate document node from others
    document_node = None
    other_nodes = []

    for node in nodes:
        props = node.get("properties", {})
        if props.get("document_id") == document_id:
            document_node = node
        else:
            other_nodes.append(node)

    # Sort other nodes by priority
    def sort_key(node: dict[str, Any]) -> tuple:
        props = node.get("properties", {})
        relevance = props.get("relevance_score", 0)
        degree = props.get("degree", 0)
        date = props.get("date", "")
        return (-relevance, -degree, date)

    sorted_nodes = sorted(other_nodes, key=sort_key)

    # Combine document node with top other nodes
    result = []
    if document_node:
        result.append(document_node)
        remaining_slots = max_nodes - 1
    else:
        remaining_slots = max_nodes

    result.extend(sorted_nodes[:remaining_slots])
    return result


def prune_links(
    links: list[dict[str, Any]],
    kept_node_ids: set[int],
) -> list[dict[str, Any]]:
    """Prune links to only those between kept nodes.

    Args:
        links: List of link dictionaries
        kept_node_ids: Set of node IDs that were kept

    Returns:
        list: Pruned links
    """
    pruned_links = []
    for link in links:
        source = link.get("source")
        target = link.get("target")
        if source in kept_node_ids and target in kept_node_ids:
            pruned_links.append(link)
    return pruned_links


def convert_to_graph_format(
    nodes: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> GraphData:
    """Convert raw FalkorDB data to GraphData format.

    Args:
        nodes: List of node dictionaries from FalkorDB
        links: List of link dictionaries from FalkorDB

    Returns:
        GraphData: Formatted graph data
    """
    graph_nodes = []
    graph_links = []

    for node in nodes:
        props = node.get("properties", {})
        labels = node.get("labels", [])
        node_type = labels[0] if labels else "Unknown"

        # Extract node data
        node_data = GraphNodeData(
            name=props.get("name", props.get("canonical_name", "Unknown")),
            type=NodeType(node_type),
            description=props.get("description"),
            level=props.get("level"),
            years=props.get("years"),
            institution=props.get("institution"),
            date=props.get("date"),
            relevance_score=props.get("relevance_score"),
        )

        graph_node = GraphNode(
            id=node.get("id", -1),
            labels=labels,
            color=get_node_color(node_type),
            visible=True,
            data=node_data,
        )
        graph_nodes.append(graph_node)

    for link in links:
        props = link.get("properties", {})
        relationship_type = link.get("relationship", "UNKNOWN")

        link_data = GraphLinkData(
            label=props.get("label"),
            weight=props.get("weight"),
            start_date=props.get("start_date"),
            end_date=props.get("end_date"),
        )

        try:
            graph_link = GraphLink(
                id=link.get("id", -1),
                relationship=RelationshipType(relationship_type),
                color="#94a3b8",
                source=link.get("source", -1),
                target=link.get("target", -1),
                visible=True,
                data=link_data,
            )
            graph_links.append(graph_link)
        except ValueError:
            # Skip invalid relationship types
            logger.warning(f"Invalid relationship type: {relationship_type}")
            continue

    return GraphData(nodes=graph_nodes, links=graph_links)


async def get_graph_data(
    user_id: str,
    document_id: Optional[str],
    node_types: Optional[list[str]] = None,
    max_nodes: int = 100,
    max_depth: Optional[int] = None,
) -> GraphData:
    """Get graph data for a document with downsampling and pruning.

    Args:
        user_id: User ID for graph namespacing
        document_id: Document UUID to query (None for user-level aggregated graph)
        node_types: Optional list of node types to filter
        max_nodes: Maximum nodes to return (enforced)
        max_depth: Optional maximum traversal depth

    Returns:
        GraphData: Formatted graph data with max 100 nodes
    """
    # Query graph from FalkorDB
    nodes, links = await query_document_graph(
        user_id=user_id,
        document_id=document_id,
        node_types=node_types,
        max_depth=max_depth,
    )

    # Downsample nodes if needed
    original_count = len(nodes)
    if original_count > max_nodes:
        nodes = downsample_nodes(nodes, max_nodes, document_id)
        logger.info(
            f"Downsampled graph for {f'document {document_id}' if document_id else 'user'} from "  # noqa: E501
            f"{original_count} to {max_nodes} nodes"
        )

    # Prune links to kept nodes
    kept_node_ids = {node.get("id") for node in nodes if node.get("id") is not None}
    links = prune_links(links, kept_node_ids)

    # Convert to GraphData format
    graph_data = convert_to_graph_format(nodes, links)

    logger.info(
        f"Retrieved graph for {f'document {document_id}' if document_id else 'user'}: "
        f"{len(graph_data.nodes)} nodes, {len(graph_data.links)} links"
    )

    return graph_data
