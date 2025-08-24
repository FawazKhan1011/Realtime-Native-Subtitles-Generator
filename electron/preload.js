const { contextBridge, ipcRenderer } = require('electron');

// Existing subtitle API
contextBridge.exposeInMainWorld("subtitleAPI", {
  connect: (onMessage, onOpen, onClose, onError) => {
    const ws = new WebSocket("ws://localhost:8765/");
    
    ws.onopen = () => {
      console.log("[client] Connected to WebSocket server");
      if (onOpen) onOpen();
    };
    
    ws.onmessage = (event) => {
      if (onMessage) onMessage(event.data);
    };
    
    ws.onclose = () => {
      console.log("[client] WebSocket closed");
      if (onClose) onClose();
    };
    
    ws.onerror = (err) => {
      console.error("[client] WebSocket error", err);
      if (onError) onError(err);
    };
    
    return ws; // Return websocket instance for manual control if needed
  },
  
  // Helper function to get window dimensions
  getWindowSize: () => {
    return {
      width: window.innerWidth,
      height: window.innerHeight
    };
  }
});

// New Electron API for app controls
contextBridge.exposeInMainWorld('electronAPI', {
  closeApp: () => ipcRenderer.invoke('close-app'),
  minimizeApp: () => ipcRenderer.invoke('minimize-app'),
  maximizeApp: () => ipcRenderer.invoke('maximize-app'),
  
  // Optional: Window control methods
  onWindowResize: (callback) => ipcRenderer.on('window-resized', callback),
  onWindowMove: (callback) => ipcRenderer.on('window-moved', callback),
  
  // Optional: Get app info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
});