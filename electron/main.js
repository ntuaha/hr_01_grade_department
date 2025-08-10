import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'
import { spawn } from 'child_process'
import Store from 'electron-store'

const store = new Store({ name: 'settings' })

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.join(__dirname, '..')
const configPath = path.join(projectRoot, 'config.json')

function runPython(args = []) {
  return new Promise((resolve) => {
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python')
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3'
    const argline = [`${pythonCmd} scripts/build_reports.py --config ${configPath}`, ...args].join(' ')
    const py = spawn(process.env.SHELL || '/bin/zsh', ['-lc', `${argline} | cat`], {
      cwd: projectRoot, // electron/ -> 回到專案根: 01_data
      env: process.env,
    })
    let out = ''
    let err = ''
    py.stdout.on('data', (d) => (out += d.toString()))
    py.stderr.on('data', (d) => (err += d.toString()))
    py.on('close', (code) => {
      resolve({ code, out, err })
    })
  })
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: true,
    },
  })
  // 優先使用 Vue3 版本，fallback 到舊版
  const vueDist = path.join(__dirname, 'renderer-dist', 'index.html')
  const fallback = path.join(__dirname, 'renderer', 'index.html')
  const htmlPath = fs.existsSync(vueDist) ? vueDist : fallback
  win.loadFile(htmlPath)
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.handle('config:get', async () => {
  try {
    return store.get('config') || {}
  } catch (e) {
    return {}
  }
})

ipcMain.handle('config:set', async (_evt, cfg) => {
  store.set('config', cfg)
  return true
})

function readDiskConfig() {
  try {
    const raw = fs.readFileSync(configPath, 'utf-8')
    return JSON.parse(raw)
  } catch (e) {
    return {}
  }
}

function writeDiskConfig(nextCfg) {
  try {
    console.log('寫入 config.json:', configPath, nextCfg)
    fs.writeFileSync(configPath, JSON.stringify(nextCfg, null, 2), 'utf-8')
    console.log('寫入成功')
    return true
  } catch (e) {
    console.error('寫入失敗:', e)
    return false
  }
}

ipcMain.handle('config:readDisk', async () => {
  return readDiskConfig()
})

ipcMain.handle('config:writeDisk', async (_evt, partialCfg) => {
  console.log('收到寫入請求:', partialCfg)
  const current = readDiskConfig()
  const nextCfg = { ...current, ...partialCfg }
  const success = writeDiskConfig(nextCfg)
  console.log('寫入結果:', success)
  return nextCfg
})

ipcMain.handle('files:set', async (_evt, files) => {
  const current = readDiskConfig()
  const list = Array.isArray(files) ? files : []
  const nextCfg = { ...current, data_files: list }
  // 若母體檔不在清單中，保留原設定；若未設定母體檔則預設最後一個
  if (!nextCfg.mother_file) {
    nextCfg.mother_file = nextCfg.data_files[nextCfg.data_files.length - 1] || current.mother_file || '2025.H1.xlsx'
  }
  if (!nextCfg.selected_files || nextCfg.selected_files.length === 0) {
    nextCfg.selected_files = list
  }
  writeDiskConfig(nextCfg)
  return nextCfg
})

ipcMain.handle('files:validate', async () => {
  const r = await runPython(['--validate'])
  return r.out || r.err
})

ipcMain.handle('files:preview', async () => {
  const r = await runPython(['--preview'])
  return r.out || r.err
})

ipcMain.handle('run:generate', async () => {
  const r = await runPython([])
  return r.out || r.err
})

ipcMain.handle('dialog:openFiles', async () => {
  const res = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    filters: [{ name: 'Excel', extensions: ['xlsx'] }],
  })
  if (res.canceled) return []
  return res.filePaths
})

ipcMain.handle('openIndexHtml', async (_evt, indexPath) => {
  try {
    console.log('開啟 index.html:', indexPath)
    if (fs.existsSync(indexPath)) {
      await shell.openPath(indexPath)
      console.log('已開啟 index.html')
      return true
    } else {
      console.error('index.html 不存在:', indexPath)
      return false
    }
  } catch (e) {
    console.error('開啟 index.html 失敗:', e)
    return false
  }
})
