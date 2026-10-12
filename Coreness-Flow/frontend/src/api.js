/**
 * Клиент WebSocket к backend: вызов actions и подписка на events.
 */

const DEFAULT_WS_PORT = 29773;

let ws = null;
let wsPort = null;
let nextId = 1;
const pending = new Map();
const eventListeners = new Map();
/** Единая попытка подключения: при конкурентных call() все ждут один и тот же сокет, иначе создаётся несколько соединений и события приходят по каждому — дубли. */
let connectionPromise = null;

async function getBackendPort() {
  if (wsPort !== null) {
    return wsPort;
  }
  if (typeof window !== 'undefined' && window.electronAPI) {
    const port = await window.electronAPI.getBackendPort();
    if (port) {
      wsPort = port;
      return port;
    }
  }
  return DEFAULT_WS_PORT;
}

function connect() {
  if (ws?.readyState === WebSocket.OPEN) {
    return Promise.resolve();
  }
  if (connectionPromise) {
    return connectionPromise;
  }
  connectionPromise = getBackendPort().then((port) => {
    const WS_URL = `ws://127.0.0.1:${port}`;
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(WS_URL);
      ws = socket;
      socket.onopen = () => {
        connectionPromise = null;
        resolve();
      };
      socket.onerror = (e) => {
        connectionPromise = null;
        ws = null;
        reject(e);
      };
      socket.onclose = () => {
        connectionPromise = null;
        ws = null;
        pending.forEach((rej) => rej(new Error('WebSocket closed')));
        pending.clear();
      };
      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.id !== undefined && msg.id !== null) {
            const settle = pending.get(msg.id);
            if (settle) {
              pending.delete(msg.id);
              settle.resolve(msg.result);
            }
          } else if (msg.event) {
            const list = eventListeners.get(msg.event);
            if (list) list.forEach((cb) => cb(msg.data));
          }
        } catch (_) {}
      };
    });
  });
  return connectionPromise;
}

export function call(action, payload = {}) {
  const id = nextId++;
  return connect().then(() => {
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, action, payload }));
    });
  });
}

export function on(event, callback) {
  if (!eventListeners.has(event)) eventListeners.set(event, []);
  eventListeners.get(event).push(callback);
  return () => {
    const list = eventListeners.get(event);
    if (list) {
      const i = list.indexOf(callback);
      if (i >= 0) list.splice(i, 1);
    }
  };
}

export function isConnected() {
  return ws?.readyState === WebSocket.OPEN;
}
