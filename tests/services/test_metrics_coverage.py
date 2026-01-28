"""Coverage tests for metrics service to reach 100%."""

from services.metrics import GraphMetrics


def test_record_request_with_downsampling():
    """Test recording a request with downsampling."""
    metrics = GraphMetrics()
    metrics.record_request(
        user_id="user1",
        document_id="doc1",
        node_count=50,
        link_count=30,
        duration_ms=100,
        downsampled=True,
    )

    result = metrics.get_metrics()
    assert result["total_requests"] == 1
    assert result["downsampled_count"] == 1
    assert result["avg_node_count"] == 50


def test_record_request_without_downsampling():
    """Test recording a request without downsampling."""
    metrics = GraphMetrics()
    metrics.record_request(
        user_id="user1",
        document_id="doc1",
        node_count=50,
        link_count=30,
        duration_ms=100,
        downsampled=False,
    )

    result = metrics.get_metrics()
    assert result["total_requests"] == 1
    assert result["downsampled_count"] == 0


def test_get_metrics_with_multiple_requests():
    """Test get_metrics with multiple requests."""
    metrics = GraphMetrics()
    metrics.record_request(
        user_id="user1",
        document_id="doc1",
        node_count=50,
        link_count=30,
        duration_ms=100,
    )
    metrics.record_request(
        user_id="user2",
        document_id="doc2",
        node_count=75,
        link_count=40,
        duration_ms=150,
    )

    result = metrics.get_metrics()
    assert result["total_requests"] == 2
    assert result["avg_node_count"] == 62.5
    assert result["p50_latency_ms"] == 150
    assert result["p95_latency_ms"] == 150


def test_get_metrics_with_errors():
    """Test get_metrics with error tracking."""
    metrics = GraphMetrics()
    metrics.record_error("NOT_FOUND", user_id="user1", document_id="doc1")
    metrics.record_error("BAD_REQUEST", user_id="user2")

    result = metrics.get_metrics()
    assert result["total_errors"] == 2
    assert result["error_rate"] == 0  # No successful requests yet
    assert "NOT_FOUND" in result["error_counts"]
    assert "BAD_REQUEST" in result["error_counts"]


def test_get_metrics_empty():
    """Test get_metrics with no data."""
    metrics = GraphMetrics()
    result = metrics.get_metrics()

    assert result["total_requests"] == 0
    assert result["total_errors"] == 0
    assert result["error_rate"] == 0
    assert result["p50_latency_ms"] == 0
    assert result["p95_latency_ms"] == 0
    assert result["avg_node_count"] == 0
    assert result["downsampled_count"] == 0
