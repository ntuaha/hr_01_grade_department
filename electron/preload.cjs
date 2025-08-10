const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  getConfig: () => ipcRenderer.invoke('config:get'),
  setConfig: (cfg) => ipcRenderer.invoke('config:set', cfg),
  readDiskConfig: () => ipcRenderer.invoke('config:readDisk'),
  writeDiskConfig: (partialCfg) => ipcRenderer.invoke('config:writeDisk', partialCfg),
  validate: () => ipcRenderer.invoke('files:validate'),
  preview: () => ipcRenderer.invoke('files:preview'),
  runGenerate: () => ipcRenderer.invoke('run:generate'),
  openFiles: () => ipcRenderer.invoke('dialog:openFiles'),
  setFiles: (files) => ipcRenderer.invoke('files:set', files),
  openIndexHtml: (path) => ipcRenderer.invoke('openIndexHtml', path),
})
