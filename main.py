from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Set
import json
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.usernames: Set[str] = set()

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket
        self.usernames.add(username)
        await self.broadcast({"type": "users", "users": list(self.usernames)})

    async def disconnect(self, username: str):
        if username in self.active_connections:
            self.active_connections.pop(username)
            self.usernames.remove(username)
            await self.broadcast({"type": "users", "users": list(self.usernames)})

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except:
                continue

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), request: Request):
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
            message = {
                "type": "message",
                "user": username,
                "message": data
            }
            await manager.broadcast(message)
    except WebSocketDisconnect:
        await manager.disconnect(username)
