<template>
  <div class="container">
    <h1>技術中心報表產生器</h1>
    
    <div class="grid">
      <!-- 檔案管理 -->
      <div class="card">
        <h2>讀取的檔案</h2>
        <div class="list-box">
          <div v-for="file in config.files" :key="file" class="checkbox-item">
            <input 
              type="checkbox" 
              :value="file" 
              v-model="config.selected_files"
              @change="saveConfig"
            />
            <span>{{ file }}</span>
          </div>
        </div>
        
        <div 
          class="dropzone"
          :class="{ dragover: isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
        >
          拖拉 .xlsx 到這裡，或 
          <button class="btn" @click="pickFiles">選擇檔案</button>
        </div>
        
        <div style="margin-top: 16px;">
          <button class="btn" @click="validateFiles">檢核檔案</button>
          <button class="btn" @click="refreshPreview">預覽母體/部門/名單</button>
        </div>
      </div>

      <!-- 參數設定 -->
      <div class="card">
        <h2>參數設定</h2>
        
        <div class="form-group">
          <label>母體表（母體檔）</label>
          <input v-model="config.mother_file" @input="saveConfigAndRefresh" />
        </div>
        
        <div class="form-group">
          <label>工作表名稱</label>
          <input v-model="config.sheet_name" placeholder="預設：總評分" @input="saveConfigAndRefresh" />
        </div>
        
        <div class="form-group">
          <label>處理的組別（部門）</label>
          <select v-model="config.target_department" @change="updateOutputDirAndSave">
            <option v-for="dept in preview.departments" :key="dept" :value="dept">
              {{ dept }}
            </option>
          </select>
        </div>
        
        <div class="form-group">
          <label>輸出資料夾</label>
          <input v-model="config.output_dir" @input="saveConfigAndRefresh" />
        </div>

        <!-- 部門篩選 -->
        <div class="form-group">
          <label>勾選要列入樣本過濾的部門：</label>
          <div class="list-box">
            <div v-for="dept in preview.departments" :key="dept" class="pill">
              <input 
                type="checkbox" 
                :value="dept" 
                v-model="config.selected_departments"
                @change="saveConfigAndRefresh"
              />
              {{ dept }}
            </div>
          </div>
        </div>

        <!-- 欄位選擇 -->
        <div class="form-group">
          <label>可選欄位（可勾選）：</label>
          <div class="list-box">
            <div v-for="key in preview.available_category_keys" :key="key" class="pill">
              <input 
                type="checkbox" 
                :value="key" 
                v-model="config.selected_category_keys"
                @change="saveConfigAndRefresh"
              />
              {{ key }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>已選欄位：</label>
          <div class="result-box" style="max-height: 80px;">
            {{ config.selected_category_keys?.join(', ') || '無' }}
          </div>
        </div>

        <p style="color: #666; font-size: 14px;">💡 設定變更會自動保存並更新預覽</p>
        <button class="btn" @click="testWrite" style="background: orange; color: white;">測試寫入</button>
      </div>
    </div>

    <!-- 結果與執行 -->
    <div class="card">
      <h2>預覽結果</h2>
      <div class="result-box">{{ previewText }}</div>
    </div>

    <div class="card">
      <h2>執行</h2>
      <button class="btn primary" @click="runGenerate" :disabled="isRunning">
        {{ isRunning ? '執行中...' : '產生報表' }}
      </button>
      
      <div v-if="runResult" class="result-box" style="margin-top: 12px;">
        {{ runResult }}
      </div>

      <div style="margin-top: 16px;">
        <h3>打包檔案教學</h3>
        <ol>
          <li>確認 `config.json`、`scripts/build_reports.py` 可正確執行</li>
          <li>在 `electron/` 執行：`npm run build` 產生安裝檔</li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'

const isDragOver = ref(false)
const isRunning = ref(false)
const runResult = ref('')

const config = reactive({
  mother_file: '2025.H1.xlsx',
  sheet_name: '總評分',
  target_department: '智能技術中心',
  output_dir: '2025H1_技術中心',
  files: [],
  selected_files: [],
  selected_departments: [],
  selected_category_keys: [],
})

const preview = reactive({
  departments: [],
  available_category_keys: [],
  sample_people: [],
  error: null,
})

const previewText = computed(() => {
  if (preview.error) return `錯誤: ${preview.error}`
  return JSON.stringify({
    departments: preview.departments,
    selected_departments: config.selected_departments,
    sample_people: preview.sample_people,
    available_category_keys: preview.available_category_keys,
    selected_category_keys: config.selected_category_keys,
  }, null, 2)
})

async function loadConfig() {
  try {
    const cfg = await window.api.readDiskConfig() || {}
    Object.assign(config, {
      mother_file: cfg.mother_file || '2025.H1.xlsx',
      sheet_name: cfg.sheet_name || '總評分', 
      target_department: cfg.target_department || '智能技術中心',
      output_dir: cfg.output_dir || '2025H1_技術中心',
      files: cfg.data_files || [],
      selected_files: cfg.selected_files || cfg.data_files || [],
      selected_departments: cfg.selected_departments || [],
      selected_category_keys: cfg.selected_category_keys || [],
    })
  } catch (e) {
    console.error('載入設定失敗:', e)
  }
}

async function saveConfig() {
  try {
    // 轉換為純 JavaScript 對象，避免 Vue reactive 問題
    const configToSave = JSON.parse(JSON.stringify({
      mother_file: config.mother_file,
      sheet_name: config.sheet_name,
      target_department: config.target_department,
      output_dir: config.output_dir,
      data_files: config.files,
      selected_files: config.selected_files,
      selected_departments: config.selected_departments,
      selected_category_keys: config.selected_category_keys,
      category_keys: config.selected_category_keys, // Python 讀取的欄位
    }))
    console.log('儲存設定:', configToSave)
    await window.api.writeDiskConfig(configToSave)
    console.log('設定已儲存')
  } catch (e) {
    console.error('儲存設定失敗:', e)
  }
}

async function saveConfigAndRefresh() {
  await saveConfig()
  await refreshPreview()
}

function updateOutputDirAndSave() {
  if (config.target_department) {
    // 自動生成輸出資料夾名稱，格式：2025H1_部門名稱
    const period = config.mother_file?.replace('.xlsx', '') || '2025H1'
    const deptName = config.target_department.replace('智能', '').replace('中心', '').replace('部', '')
    config.output_dir = `${period}_${deptName}`
  }
  saveConfigAndRefresh()
}

async function refreshPreview() {
  try {
    await saveConfig() // 先儲存當前設定
    const result = await window.api.preview()
    const data = JSON.parse(result)
    console.log('預覽結果:', data)
    Object.assign(preview, {
      departments: data.departments || [],
      available_category_keys: data.available_category_keys || [],
      sample_people: data.sample_people || [],
      error: data.error || null,
    })
    
    // 同步已選欄位（如果為空，預設全選）
    if (!config.selected_category_keys?.length && preview.available_category_keys.length) {
      config.selected_category_keys = [...preview.available_category_keys]
      console.log('自動設定預設欄位:', config.selected_category_keys)
      await saveConfig()
    }
  } catch (e) {
    console.error('預覽失敗:', e)
    preview.error = e.message
  }
}

async function validateFiles() {
  try {
    await saveConfig() // 先儲存當前設定
    const result = await window.api.validate()
    const data = JSON.parse(result)
    console.log('檢核結果:', data)
    // 更新預覽顯示檢核結果
    Object.assign(preview, { validation: data })
  } catch (e) {
    console.error('檢核失敗:', e)
    preview.error = e.message
  }
}

async function pickFiles() {
  try {
    const paths = await window.api.openFiles()
    if (paths?.length) {
      const next = await window.api.setFiles(paths)
      config.files = next.data_files || paths
      config.selected_files = next.selected_files || next.data_files || []
      await refreshPreview()
    }
  } catch (e) {
    console.error('選擇檔案失敗:', e)
  }
}

async function handleDrop(e) {
  isDragOver.value = false
  try {
    const files = Array.from(e.dataTransfer.files).map(f => f.path)
    const next = await window.api.setFiles(files)
    config.files = next.data_files || files
    config.selected_files = next.selected_files || next.data_files || []
    await refreshPreview()
  } catch (e) {
    console.error('拖拉檔案失敗:', e)
  }
}

async function runGenerate() {
  isRunning.value = true
  runResult.value = '執行中...'
  try {
    // 先保存最新設定
    await saveConfig()
    console.log('已保存最新設定，開始執行報表生成...')
    const result = await window.api.runGenerate()
    runResult.value = result
    
    // 檢查是否有 index.html 路徑，如果有則自動開啟
    const lines = result.split('\n')
    const indexLine = lines.find(line => line.startsWith('INDEX_HTML_PATH:'))
    if (indexLine) {
      const indexPath = indexLine.replace('INDEX_HTML_PATH:', '')
      console.log('自動開啟 index.html:', indexPath)
      await window.api.openIndexHtml(indexPath)
    }
  } catch (e) {
    runResult.value = `執行失敗: ${e.message}`
  } finally {
    isRunning.value = false
  }
}

async function testWrite() {
  try {
    console.log('測試寫入開始...')
    const testConfig = {
      target_department: "智能技術中心_測試",
      output_dir: "測試資料夾",
      test_timestamp: new Date().toISOString()
    }
    console.log('要寫入的測試設定:', testConfig)
    const result = await window.api.writeDiskConfig(testConfig)
    console.log('寫入結果:', result)
    alert('測試寫入完成，請檢查 config.json')
  } catch (e) {
    console.error('測試寫入失敗:', e)
    alert('測試寫入失敗: ' + e.message)
  }
}

onMounted(async () => {
  await loadConfig()
  await refreshPreview()
})
</script>
