import { BrowserWindow, shell } from 'electron';
import { resolve } from 'path';

const WINDOW_CONFIG = {
  width: 1400,
  height: 900,
  minWidth: 1024,
  minHeight: 600,
} as const;

export class WindowManager {
  private mainWindow: BrowserWindow | null = null;

  createWindow(): BrowserWindow {
    const preloadPath = resolve(__dirname, '../preload/index.js');

    this.mainWindow = new BrowserWindow({
      width: WINDOW_CONFIG.width,
      height: WINDOW_CONFIG.height,
      minWidth: WINDOW_CONFIG.minWidth,
      minHeight: WINDOW_CONFIG.minHeight,
      show: false,
      webPreferences: {
        preload: preloadPath,
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
      },
    });

    this.mainWindow.on('ready-to-show', () => {
      this.mainWindow?.show();
    });

    this.mainWindow.webContents.setWindowOpenHandler((details) => {
      shell.openExternal(details.url);
      return { action: 'deny' };
    });

    this.loadURL();

    return this.mainWindow;
  }

  private loadURL(): void {
    if (!this.mainWindow) return;

    if (process.env.ELECTRON_RENDERER_URL) {
      this.mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
    } else {
      const indexPath = resolve(__dirname, '../renderer/index.html');
      this.mainWindow.loadFile(indexPath);
    }
  }

  getWindow(): BrowserWindow | null {
    return this.mainWindow;
  }

  destroy(): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.close();
    }
    this.mainWindow = null;
  }
}
