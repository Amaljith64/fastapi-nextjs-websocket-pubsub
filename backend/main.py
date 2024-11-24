import uuid,json
from fastapi import FastAPI,APIRouter,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List,Dict
from api.routes import router
from config import Settings
from redis import Redis
import asyncio


app = FastAPI()
settings = Settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis = Redis(host='redis', port=6379, db=0)

# Store active websocket connections
active_connections: List[WebSocket] = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis_client = redis
    
    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        # Generate a simple session ID
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        return session_id
    
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(session_id)

    async def listen_to_redis(self, session_id: str):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(f"task_status_{session_id}")

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    await self.send_message(session_id, json.loads(message['data']))
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pubsub.unsubscribe()
            pubsub.close()

manager = ConnectionManager()


app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
app.mount("/converted", StaticFiles(directory=str(settings.CONVERTED_DIR)), name="converted")


# Include routers
app.include_router(router, prefix="/api")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    
    session_id = await manager.connect(websocket)
    print('session--- id',session_id)

    try:

        # Send session ID to client 
        await websocket.send_json({
            "type": "session_id",
            "session_id": session_id
        })
        
        redis_listener_task = asyncio.create_task(manager.listen_to_redis(session_id))

        try:

            while True:
                await websocket.receive_json()
                
        except WebSocketDisconnect:
            print("WebSocket disconnected")
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            redis_listener_task.cancel()
            await manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket connection error: {e}")