const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 150,
    frame: false,             // no chrome
    transparent: true,        // allows CSS semi-transparent bg
    alwaysOnTop: true,
    resizable: true,
    movable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(createWindow);
