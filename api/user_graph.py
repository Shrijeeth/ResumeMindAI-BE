"""User graph API endpoints."""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.errors import ErrorCode, create_error_response
from api.schemas.graph import GraphData, NodeType
from middlewares.auth import get_current_user
from services.graph_service import get_graph_data
from services.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/graph", response_model=GraphData)
async def get_user_graph(
    current_user=Depends(get_current_user),
    types: Optional[str] = Query(None, description="Filter by node types (CSV)"),
    max_nodes: int = Query(100, ge=1, le=100, description="Maximum nodes to return"),
    max_depth: Optional[int] = Query(
        None, ge=1, le=5, description="Maximum traversal depth"
    ),
):
    """
    Get knowledge graph data for a user.

    Returns nodes and links from the user's aggregated knowledge graph
    across all documents. Enforces a maximum of 100 nodes per response
    with deterministic downsampling.
    """
    user_id = current_user.id
    start_time = time.time()

    # Validate node types if provided
    node_types = None
    if types:
        type_list = [t.strip() for t in types.split(",")]
        # Validate each type is a valid NodeType
        for node_type in type_list:
            try:
                NodeType(node_type)
            except ValueError:
                logger.warning(
                    "Invalid node type provided",
                    extra={
                        "user_id": user_id,
                        "invalid_type": node_type,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=create_error_response(
                        code=ErrorCode.BAD_REQUEST,
                        message=f"Invalid node type: {node_type}",
                    ).model_dump(),
                )
        node_types = type_list

    try:
        # Get graph data (aggregated across all user documents)
        graph_data = await get_graph_data(
            user_id=user_id,
            document_id=None,  # No document filtering
            node_types=node_types,
            max_nodes=max_nodes,
            max_depth=max_depth,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Log observability data
        logger.info(
            "User graph data retrieved successfully",
            extra={
                "user_id": user_id,
                "node_count": len(graph_data.nodes),
                "link_count": len(graph_data.links),
                "duration_ms": duration_ms,
                "max_nodes": max_nodes,
                "node_types": node_types,
                "max_depth": max_depth,
                "downsampled": len(graph_data.nodes) == max_nodes,
            },
        )

        # Record metrics
        metrics.record_request(
            user_id=user_id,
            document_id="aggregated",
            node_count=len(graph_data.nodes),
            link_count=len(graph_data.links),
            duration_ms=duration_ms,
            downsampled=len(graph_data.nodes) == max_nodes,
        )

        return graph_data

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "Error retrieving user graph data",
            extra={
                "user_id": user_id,
                "duration_ms": duration_ms,
                "error": str(e),
            },
        )
        metrics.record_error(
            error_code="INTERNAL",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code=ErrorCode.INTERNAL,
                message="Failed to retrieve graph data",
            ).model_dump(),
        )
