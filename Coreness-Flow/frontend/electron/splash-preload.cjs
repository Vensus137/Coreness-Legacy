/**
 * Preload для splash: приём прогресса от main process.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('splashAPI', {
  onProgress: (callback) => {
    const fn = (_, value, text) => callback(value, text);
    ipcRenderer.on('splash:progress', fn);
    return () => ipcRenderer.removeListener('splash:progress', fn);
  },
});
