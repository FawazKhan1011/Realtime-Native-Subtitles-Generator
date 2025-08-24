const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 150,
    minWidth: 300,           // minimum window width
    minHeight: 80,           // minimum window height
    maxWidth: 1400,          // maximum window width  
    maxHeight: 400,          // maximum window height
    frame: false,            // no chrome
    transparent: true,       // allows CSS semi-transparent bg
    alwaysOnTop: true,
    resizable: true,         // enable resizing
    movable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      enableRemoteModule: false,
      nodeIntegration: false   // Security best practice
    }
  });

  mainWindow.loadFile('index.html');
  
  // Optional: Remember window size and position
  mainWindow.on('resize', () => {
    const [width, height] = mainWindow.getSize();
    console.log(`Window resized to: ${width}x${height}`);
    
    // Send resize event to renderer if needed
    mainWindow.webContents.send('window-resized', { width, height });
  });

  mainWindow.on('move', () => {
    const [x, y] = mainWindow.getPosition();
    console.log(`Window moved to: ${x}, ${y}`);
    
    // Send move event to renderer if needed
    mainWindow.webContents.send('window-moved', { x, y });
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Optional: Open DevTools in development
  // mainWindow.webContents.openDevTools();
}

// IPC handlers for window controls
ipcMain.handle('close-app', () => {
  console.log('Close app requested');
  app.quit();
});

ipcMain.handle('minimize-app', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

ipcMain.handle('maximize-app', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

app.whenReady().then(() => {
  createWindow();
  
  // macOS: Re-create window when app is activated
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
  });
});

// Optional: Handle before quit (for cleanup)
app.on('before-quit', (event) => {
  console.log('App is about to quit');
  // You can add cleanup logic here if needed
  // event.preventDefault(); // Uncomment to prevent quit and handle cleanup
});