import { app, BrowserWindow } from "electron";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const distIndex = path.join(projectRoot, "dist", "index.html");
const devServerUrl = process.env.MWE_ELECTRON_DEV_URL || "http://127.0.0.1:5173";

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 760,
    center: true,
    resizable: true,
    autoHideMenuBar: true,
    title: "MWE Command Center",
    backgroundColor: "#151714",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  if (process.env.MWE_ELECTRON_MODE === "dev") {
    void win.loadURL(devServerUrl);
    if (process.env.MWE_ELECTRON_DEVTOOLS === "1") {
      win.webContents.openDevTools({ mode: "detach" });
    }
  } else {
    void win.loadURL(pathToFileURL(distIndex).toString());
  }
}

app.whenReady().then(() => {
  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
