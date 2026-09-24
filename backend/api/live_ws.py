from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from backend.services import auth, live_feed, live_ws

router = APIRouter(tags=["live"])


@router.websocket("/ws/live")
async def live_socket(websocket: WebSocket) -> None:
    """Stream live updates only to authenticated HospitalFlow users."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        auth.decode_access_token(token)
    except Exception:
        await websocket.close(code=1008, reason="Invalid or expired authentication token")
        return
    await live_ws.manager.connect(websocket)
    try:
        status = live_feed.manager.status()
        await websocket.send_json(jsonable_encoder({
            "type": "connected",
            "status": status.__dict__,
        }))
        while True:
            # The client does not need to send commands. Keeping the socket open
            # lets the server push each simulator tick immediately.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await live_ws.manager.disconnect(websocket)
