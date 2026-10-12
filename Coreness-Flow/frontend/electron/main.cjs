/**
 * Electron main process: сплеш при загрузке backend, затем окно с frontend.
 * Кастомный заголовок (frameless), preload для кнопок окна.
 */

const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const net = require('net');

const VITE_DEV_PORT = 29774;
const isDev = process.argv.includes('--dev');

/** Находит свободный порт для backend. */
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

/** Освобождает порт: завершает процессы, слушающие на нём (без прав админа — только свои). */
function freePort(port) {
  try {
    if (process.platform === 'win32') {
      const out = execSync(`netstat -ano`, { encoding: 'utf8', windowsHide: true });
      const pids = new Set();
      for (const line of out.split('\n')) {
        const trimmed = line.trim();
        if (trimmed.includes(`:${port}`) && trimmed.includes('LISTENING')) {
          const parts = trimmed.split(/\s+/);
          const pid = parts[parts.length - 1];
          if (/^\d+$/.test(pid)) pids.add(pid);
        }
      }
      for (const pid of pids) {
        try {
          execSync(`taskkill /PID ${pid} /F /T`, { encoding: 'utf8', windowsHide: true, stdio: 'ignore' });
        } catch (_) {}
      }
    } else {
      const out = execSync(`lsof -ti :${port}`, { encoding: 'utf8' }).trim();
      if (out) {
        for (const pid of out.split(/\s+/)) {
          try { execSync(`kill -9 ${pid}`, { stdio: 'ignore' }); } catch (_) {}
        }
      }
    }
  } catch (_) {
    // Порт свободен или нет прав — продолжаем
  }
}

let backendProcess = null;
let backendPort = null;
let splashWindow = null;
let mainWindow = null;

function getBackendCommand(port) {
  if (app.isPackaged) {
    const resourcesPath = process.resourcesPath;
    const backendExe = path.join(resourcesPath, 'backend', process.platform === 'win32' ? 'coreness-backend.exe' : 'coreness-backend');
    return {
      cmd: backendExe,
      args: ['--port', String(port), '--project-root', resourcesPath],
      cwd: resourcesPath,
    };
  }
  const projectRoot = path.resolve(__dirname, '../..');
  const pythonScript = path.join(projectRoot, 'run_backend.py');
  return {
    cmd: process.platform === 'win32' ? 'python' : 'python3',
    args: [pythonScript, '--port', String(port)],
    cwd: projectRoot,
  };
}

function startBackend() {
  return findFreePort().then((port) => {
    backendPort = port;
    return new Promise((resolve, reject) => {
      const { cmd, args, cwd } = getBackendCommand(port);
      backendProcess = spawn(cmd, args, {
        cwd,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      });
      let resolved = false;
      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          reject(new Error('Backend timeout: порт не получен за 120 сек'));
        }
      }, 120000);
      backendProcess.stdout.on('data', (data) => {
        const line = data.toString().trim();
        if (line.startsWith('ws://') && !resolved) {
          resolved = true;
          clearTimeout(timeout);
          resolve(port);
        }
      });
      backendProcess.stderr.on('data', (d) => process.stderr.write(d));
      backendProcess.on('error', (err) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          reject(err);
        }
      });
      backendProcess.on('exit', (code) => {
        if (code !== null && code !== 0 && !resolved) {
          resolved = true;
          clearTimeout(timeout);
          reject(new Error(`Backend exited with code ${code}`));
        }
      });
    });
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

const SPLASH_PROGRESS_STEPS = [
  [5, 'Загрузка конфигурации...'],
  [15, 'Инициализация API Bus...'],
  [25, 'Обнаружение плагинов...'],
  [40, 'Загрузка плагинов...'],
  [55, 'Инициализация плагинов...'],
  [70, 'Подготовка...'],
  [85, 'Запуск сервера...'],
  [92, 'Инициализация UI...'],
  [96, 'Создание главного окна...'],
];

function createSplash() {
  const splashPreload = path.join(__dirname, 'splash-preload.cjs');
  splashWindow = new BrowserWindow({
    width: 562,
    height: 405,
    frame: false,
    transparent: false,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: splashPreload,
    },
  });
  if (isDev) {
    splashWindow.loadURL('http://localhost:29774/splash.html');
  } else {
    splashWindow.loadFile(path.join(__dirname, '../dist/splash.html'));
  }
  splashWindow.on('closed', () => { splashWindow = null; });
}

function runWithSplashProgress() {
  return new Promise((resolve, reject) => {
    let stepIndex = 0;
    const interval = setInterval(() => {
      if (splashWindow && !splashWindow.isDestroyed() && stepIndex < SPLASH_PROGRESS_STEPS.length) {
        const [value, text] = SPLASH_PROGRESS_STEPS[stepIndex];
        splashWindow.webContents.send('splash:progress', value, text);
        stepIndex++;
      }
    }, 1800);
    startBackend()
      .then(() => {
        clearInterval(interval);
        if (splashWindow && !splashWindow.isDestroyed()) {
          splashWindow.webContents.send('splash:progress', 100, 'Готово!');
        }
        setTimeout(resolve, 400);
      })
      .catch((err) => {
        clearInterval(interval);
        reject(err);
      });
  });
}

function createWindow() {
  Menu.setApplicationMenu(null);
  const preloadPath = path.join(__dirname, 'preload.cjs');
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#1e1e1e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: preloadPath,
    },
  });
  if (isDev) {
    mainWindow.loadURL('http://localhost:29774');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  mainWindow.on('maximize', () => {
    if (mainWindow?.webContents) mainWindow.webContents.send('window:maximized-change', true);
  });
  mainWindow.on('unmaximize', () => {
    if (mainWindow?.webContents) mainWindow.webContents.send('window:maximized-change', false);
  });
}

ipcMain.on('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});
ipcMain.on('window:maximize', () => {
  if (mainWindow) mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on('window:close', () => {
  if (mainWindow) mainWindow.close();
});
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);
ipcMain.handle('backend:getPort', () => backendPort);

app.whenReady().then(() => {
  createSplash();
  splashWindow.webContents.once('did-finish-load', () => {
    runWithSplashProgress()
      .then(() => {
        if (splashWindow) {
          splashWindow.close();
          splashWindow = null;
        }
        createWindow();
      })
      .catch((err) => {
        console.error('Не удалось запустить backend:', err);
        if (splashWindow) splashWindow.close();
        app.quit(1);
      });
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  app.quit();
});

app.on('before-quit', () => {
  stopBackend();
});
