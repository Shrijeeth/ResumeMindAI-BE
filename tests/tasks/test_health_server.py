import asyncio
import json

import httpx
import pytest

from tasks import health_server


@pytest.mark.asyncio
async def test_health_handler_returns_json():
    resp = await health_server.health_handler(None)

    assert resp.status == 200
    assert json.loads(resp.body.decode()) == {
        "status": "healthy",
        "service": "taskiq-worker",
    }


@pytest.mark.asyncio
async def test_run_health_server_serves_health_endpoint():
    port = 8085
    server_task = asyncio.create_task(health_server.run_health_server(port))

    try:
        # wait briefly for server to start
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{port}/health")
            assert response.status_code == 200
            assert response.json() == {
                "status": "healthy",
                "service": "taskiq-worker",
            }
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
