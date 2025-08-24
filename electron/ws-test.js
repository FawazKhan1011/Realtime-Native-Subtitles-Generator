const WebSocket = require('ws');

const ws = new WebSocket('ws://127.0.0.1:8765/');

ws.on('open', () => console.log('✅ Node client connected'));

ws.on('message', (msg) => console.log('📥 Node received:', msg.toString()));

ws.on('close', () => console.log('🔌 Node closed'));

ws.on('error', (err) => console.error('🚨 Node error', err));
