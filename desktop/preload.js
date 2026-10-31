const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('edgeguard', {
  platform: process.platform,
  version: '1.0.0',
  isDesktop: true
});
