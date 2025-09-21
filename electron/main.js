const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

let mainWindow;
let pythonProcess;

// ---------- CREATE MAIN WINDOW ----------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 150,
    minWidth: 300,
    minHeight: 80,
    maxWidth: 1400,
    maxHeight: 400,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    movable: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      enableRemoteModule: false,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));

  mainWindow.on("resize", () => {
    const [width, height] = mainWindow.getSize();
    mainWindow.webContents.send("window-resized", { width, height });
  });

  mainWindow.on("move", () => {
    const [x, y] = mainWindow.getPosition();
    mainWindow.webContents.send("window-moved", { x, y });
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ---------- WINDOW CONTROLS ----------
ipcMain.handle("close-app", () => app.quit());
ipcMain.handle("minimize-app", () => mainWindow?.minimize());
ipcMain.handle("maximize-app", () => {
  if (mainWindow) {
    mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
  }
});
ipcMain.handle("get-app-version", () => app.getVersion());

// ---------- PYTHON BACKEND STARTER ----------
function startPythonServer() {
  const isDev = !app.isPackaged;

  let pythonPath;
  let scriptPath;

  if (isDev) {
    // Dev mode: local Python + script
    scriptPath = path.join(__dirname, "../main.py");
    pythonPath = process.platform === "win32"
      ? path.join(__dirname, "../venv/Scripts/python.exe")
      : path.join(__dirname, "../venv/bin/python");
  } else {
    // Packaged mode: script inside exe folder
    const exeDir = path.dirname(process.execPath);
    scriptPath = path.join(exeDir, "python", "main.py");
    pythonPath = process.platform === "win32"
      ? path.join(exeDir, "python", "venv", "Scripts", "python.exe")
      : path.join(exeDir, "python", "venv/bin/python");
  }

  if (!fs.existsSync(pythonPath)) {
    console.warn("⚠️ Python interpreter not found, using system python");
    pythonPath = "python"; // fallback to system Python
  }

  console.log("🐍 Python interpreter:", pythonPath);
  console.log("📄 Python script path:", scriptPath);

  pythonProcess = spawn(pythonPath, [scriptPath]);

  pythonProcess.stdout.on("data", (data) => console.log(`[python] ${data}`));
  pythonProcess.stderr.on("data", (data) => console.error(`[python error] ${data}`));
  pythonProcess.on("close", (code) => console.log(`Python exited with code ${code}`));
}

// ---------- APP LIFECYCLE ----------
app.whenReady().then(() => {
  createWindow();
  startPythonServer();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  if (pythonProcess) {
    console.log("🛑 Killing Python process before exit...");
    pythonProcess.kill();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// Prevent external navigation
app.on("web-contents-created", (event, contents) => {
  contents.on("new-window", (event) => event.preventDefault());
});
