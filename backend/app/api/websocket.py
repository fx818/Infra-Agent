"""
WebSocket route — streams Terraform execution logs in real-time.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/projects/{project_id}/logs")
async def stream_terraform_logs(websocket: WebSocket, project_id: int) -> None:
    """
    WebSocket endpoint to stream Terraform execution logs.

    Subscribes to Redis pub/sub channel `terraform_logs:{project_id}`
    and forwards messages to the WebSocket client.
    """
    await websocket.accept()
    logger.info("WebSocket connected for project %d logs", project_id)

    try:
        # Try to use Redis pub/sub for real-time streaming
        try:
            import redis.asyncio as aioredis
            from app.core.config import settings

            redis_client = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"terraform_logs:{project_id}")

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await websocket.send_text(data)

                # Check for incoming messages from client
                try:
                    client_msg = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.1
                    )
                    if client_msg == "close":
                        break
                except asyncio.TimeoutError:
                    pass

        except ImportError:
            # Redis not available — send periodic status updates
            logger.warning("Redis not available, WebSocket will provide polling updates")
            while True:
                await websocket.send_text(
                    json.dumps({"type": "info", "message": "Log streaming requires Redis. Polling for status..."})
                )
                await asyncio.sleep(5)

                # Check for close signal
                try:
                    client_msg = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.1
                    )
                    if client_msg == "close":
                        break
                except asyncio.TimeoutError:
                    pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for project %d", project_id)
    except Exception as e:
        logger.error("WebSocket error for project %d: %s", project_id, e)
        try:
            await websocket.close()
        except Exception:
            pass
