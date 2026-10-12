/**
 * Preload: передаёт в renderer только нужные вызовы окна (minimize, maximize, close).
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
  onMaximizedChange: (callback) => {
    const fn = (_, isMax) => callback(isMax);
    ipcRenderer.on('window:maximized-change', fn);
    return () => ipcRenderer.removeListener('window:maximized-change', fn);
  },
  getBackendPort: () => ipcRenderer.invoke('backend:getPort'),
});
