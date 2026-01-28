"""Metrics service for tracking graph API performance and usage."""

import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class GraphMetrics:
    """Simple in-memory metrics collector for graph API."""

    def __init__(self):
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
        self._latencies = defaultdict(list)
        self._node_counts = defaultdict(list)
        self._downsampled_counts = defaultdict(int)

    def record_request(
        self,
        user_id: str,
        document_id: str,
        node_count: int,
        link_count: int,
        duration_ms: int,
        downsampled: bool = False,
    ) -> None:
        """Record a successful graph request.

        Args:
            user_id: User ID
            document_id: Document ID
            node_count: Number of nodes returned
            link_count: Number of links returned
            duration_ms: Request duration in milliseconds
            downsampled: Whether the graph was downsampled
        """
        self._request_counts["total"] += 1
        self._latencies["total"].append(duration_ms)
        self._node_counts["total"].append(node_count)

        if downsampled:
            self._downsampled_counts["total"] += 1

        logger.debug(
            "Metrics recorded",
            extra={
                "user_id": user_id,
                "document_id": document_id,
                "node_count": node_count,
                "link_count": link_count,
                "duration_ms": duration_ms,
                "downsampled": downsampled,
            },
        )

    def record_error(
        self,
        error_code: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> None:
        """Record an error.

        Args:
            error_code: Error code (e.g., "NOT_FOUND", "BAD_REQUEST")
            user_id: Optional user ID
            document_id: Optional document ID
        """
        self._error_counts[error_code] += 1

        logger.warning(
            "Error recorded",
            extra={
                "error_code": error_code,
                "user_id": user_id,
                "document_id": document_id,
            },
        )

    def get_metrics(self) -> dict:
        """Get current metrics summary.

        Returns:
            dict: Metrics summary
        """
        total_requests = self._request_counts.get("total", 0)
        total_errors = sum(self._error_counts.values())

        # Calculate p50 and p95 latency
        latencies = self._latencies.get("total", [])
        p50_latency = 0
        p95_latency = 0
        if latencies:
            sorted_latencies = sorted(latencies)
            p50_latency = sorted_latencies[len(sorted_latencies) // 2]
            p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]

        # Calculate average node count
        node_counts = self._node_counts.get("total", [])
        avg_node_count = 0
        if node_counts:
            avg_node_count = sum(node_counts) / len(node_counts)

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            "p50_latency_ms": p50_latency,
            "p95_latency_ms": p95_latency,
            "avg_node_count": avg_node_count,
            "downsampled_count": self._downsampled_counts.get("total", 0),
            "error_counts": dict(self._error_counts),
        }


# Global metrics instance
metrics = GraphMetrics()
