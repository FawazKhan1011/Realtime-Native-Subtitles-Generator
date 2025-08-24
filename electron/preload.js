const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("subtitleAPI", {
  connect: (onMessage) => {
    const ws = new WebSocket("ws://localhost:8765/");
    ws.onopen = () => console.log("[client] Connected to WebSocket server");
    ws.onmessage = (event) => onMessage(event.data);
    ws.onclose = () => console.log("[client] WebSocket closed");
    ws.onerror = (err) => console.error("[client] WebSocket error", err);
  }
});
