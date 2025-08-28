from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """<!DOCTYPE html>
<html>
  <head><title>Chat</title></head>
  <body>
    <h1>WebSocket Chat</h1>
    <h2>Your ID: <span id="ws-id"></span></h2>
    <form onsubmit="sendMessage(event)">
      <input type="text" id="messageText" autocomplete="off"/>
      <button>Send</button>
    </form>
    <ul id='messages'></ul>
    <script>
      var client_id = Date.now();
      document.querySelector("#ws-id").textContent = client_id;
      // ★ 경로에 client_id 포함
      var ws = new WebSocket(`ws://${location.host}/ws/${client_id}`);
      ws.onmessage = function(event) {
        var messages = document.getElementById('messages');
        var li = document.createElement('li');
        li.textContent = event.data;
        messages.appendChild(li);
      };
      function sendMessage(event) {
        var input = document.getElementById("messageText");
        ws.send(input.value);
        input.value = '';
        event.preventDefault();
      }
    </script>
  </body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        # 실패한 연결은 조용히 제거
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)

# ★ 경로에 {client_id} 추가
@app.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    print(f"Websocket 연결 시도 client_id: {client_id}")
    await manager.connect(websocket)
    # 접속 직후 서버가 관측한 클라이언트 IP를 내려줌
    await websocket.send_text(f"[server_sent_ip] {websocket.client.host}")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
