const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');

let mainWindow;
let javaProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Load the React app from the bundled frontend/dist or frontend
  const indexPath = path.join(__dirname, 'frontend/index.html');
  if (fs.existsSync(indexPath)) {
    mainWindow.loadFile(indexPath);
  } else {
    console.error('Frontend index.html not found at:', indexPath);
  }

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

function resolveJavaBinary() {
  // 1. Check bundled JRE
  const bundledJava = process.platform === 'win32'
    ? path.join(__dirname, 'jre/bin/java.exe')
    : path.join(__dirname, 'jre/bin/java');
  if (fs.existsSync(bundledJava)) {
    return bundledJava;
  }

  // 2. Check JAVA_HOME
  if (process.env.JAVA_HOME) {
    const envJava = process.platform === 'win32'
      ? path.join(process.env.JAVA_HOME, 'bin', 'java.exe')
      : path.join(process.env.JAVA_HOME, 'bin', 'java');
    if (fs.existsSync(envJava)) {
      return envJava;
    }
  }

  // 3. Fallback to system java on PATH
  return process.platform === 'win32' ? 'java.exe' : 'java';
}

function startBackend() {
  const jarPath = path.join(__dirname, 'backend/backend-0.0.1-SNAPSHOT.jar');
  const javaPath = resolveJavaBinary();

  if (!fs.existsSync(jarPath)) {
    console.warn(`Backend JAR not found at ${jarPath}. If running in development mode, ensure backend is running separately on port 8080.`);
    return;
  }

  console.log('Starting Java Backend:', jarPath, 'using', javaPath);
  try {
    javaProcess = spawn(javaPath, ['-jar', jarPath]);

    javaProcess.on('error', (err) => {
      console.error('Failed to spawn backend process:', err.message);
      if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showMessageBox(mainWindow, {
          type: 'warning',
          title: 'Backend Process Warning',
          message: `Could not start embedded backend: ${err.message}. EdgeGuard will attempt to connect to an external backend on port 8080.`
        });
      }
    });

    if (javaProcess.stdout) {
      javaProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
      });
    }

    if (javaProcess.stderr) {
      javaProcess.stderr.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
      });
    }

    javaProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
      javaProcess = null;
    });
  } catch (err) {
    console.error('Exception during backend spawn:', err.message);
  }
}

function cleanupBackendProcess() {
  if (!javaProcess || !javaProcess.pid) return;

  const pid = javaProcess.pid;
  console.log(`Cleaning up backend process PID ${pid}...`);

  if (process.platform === 'win32') {
    try {
      execSync(`taskkill /F /T /PID ${pid}`, { stdio: 'ignore' });
      console.log(`Backend process ${pid} terminated via taskkill.`);
    } catch (e) {
      // Process may have already exited
    }
  } else {
    try {
      javaProcess.kill('SIGTERM');
    } catch (e) {
      // Process may have already exited
    }
  }
  javaProcess = null;
}

app.on('ready', () => {
  startBackend();
  // Allow backend process initialization before opening window
  setTimeout(createWindow, 1500);
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  cleanupBackendProcess();
});

app.on('will-quit', () => {
  cleanupBackendProcess();
});
