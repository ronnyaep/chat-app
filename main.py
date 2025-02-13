from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import json
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI()

# Configuration CORS pour les WebSockets
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")

# Créer le dossier static s'il n'existe pas
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Monter le dossier static seulement s'il existe
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory="templates")

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.usernames: Set[str] = set()

    async def connect(self, websocket: WebSocket, username: str):
        try:
            await websocket.accept()
            self.active_connections[username] = websocket
            self.usernames.add(username)
            await self.broadcast({"type": "users", "users": list(self.usernames)})
        except Exception as e:
            print(f"Error connecting: {e}")

    async def disconnect(self, username: str):
        if username in self.active_connections:
            try:
                await self.active_connections[username].close()
            except:
                pass
            self.active_connections.pop(username)
            self.usernames.remove(username)
            await self.broadcast({"type": "users", "users": list(self.usernames)})

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections.values()):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")
                continue

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...)):
    if username in manager.usernames:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Ce pseudo est déjà pris"}
        )
    request.session["username"] = username
    return RedirectResponse(url="/chat", status_code=303)

@app.get("/chat", response_class=HTMLResponse)
async def get_chat(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "username": username
    })

@app.get("/logout")
async def logout(request: Request):
    username = request.session.get("username")
    if username:
        await manager.disconnect(username)
    request.session.clear()
    return RedirectResponse(url="/")

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    if username in manager.usernames:
        await websocket.close(code=1008, reason="Username already taken")
        return
        
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Message received from {username}: {data}")  # Debug log
            message = {
                "type": "message",
                "user": username,
                "message": data
            }
            await manager.broadcast(message)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for {username}")  # Debug log
        await manager.disconnect(username)
    except Exception as e:
        print(f"Error in websocket: {e}")  # Debug log
        await manager.disconnect(username)
