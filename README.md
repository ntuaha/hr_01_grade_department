# 同仁互評報表產生說明

本專案會讀取歷年 Excel（例如：`2023.H2.xlsx`, `2024.H1.xlsx`, `2024.H2.xlsx`, `2025.H1.xlsx`），
產生每位同仁的歷年成績 CSV 與 HTML（含圖表），以及首頁總覽（摘要建議）。

## 資料擺放與命名
- 將各期 Excel 檔放在本目錄下（與 `scripts/` 同一層）。
- 檔名建議「年份.期別」：`2023.H2.xlsx`、`2024.H1.xlsx`、`2024.H2.xlsx`、`2025.H1.xlsx`。
- 每份 Excel 至少需有工作表：`總評分`；建議保留 `受邀評分`、`必填評分`、`主動評分` 供校對。
- `總評分` 需要欄位（空白/全形句點會自動容錯）：
  - 基本：`受評者`、`部`、13 指標與 `平均`
  - 問卷份數（會用在 2025.H1）：`必填份數`、`邀請份數`、`主動份數`、`總份數`
  - 13 指標建議名稱：
    1. 1.分析與邏輯思考能力
    2. 2.專業知識
    3. 3.溝通
    4. 4.口頭溝通
    5. 5.團隊合作
    6. 6.合作意願
    7. 7.持續、努力不懈
    8. 8.個人紀律
    9. 9.主動、積極進取
    10. 10.成熟度
    11. 11.領導能力、潛力
    12. 12.說到做到
    13. 13.綜合表現

## 環境需求
- Python 3.9+（macOS / Linux / Windows）
- 會安裝：pandas、openpyxl、numpy、jinja2

## 快速開始
1) 進到資料夾
```bash
cd "/Volumes/ahaSSD/Dropbox/ESB/02_智金處/00_組織/06_同仁互評/01_data"
```
2) 建立虛擬環境並安裝套件
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install pandas openpyxl numpy jinja2
```
3)（可選）調整參數：`config.json`
```json
{
  "data_files": ["2023.H2.xlsx", "2024.H1.xlsx", "2024.H2.xlsx", "2025.H1.xlsx"],
  "mother_file": "2025.H1.xlsx",
  "sheet_name": "總評分",
  "target_department": "智能技術中心",
  "output_dir": "2025H1_技術中心",
  "category_keys": ["1.分析與邏輯思考能力", "2.專業知識", "3.溝通", "4.口頭溝通", "5.團隊合作", "6.合作意願", "7.持續、努力不懈", "8.個人紀律", "9.主動、積極進取", "10.成熟度", "11.領導能力、潛力", "12.說到做到", "13.綜合表現"]
}
```
4) 先檢核與預覽（選用）
```bash
python scripts/build_reports.py --validate | jq .
python scripts/build_reports.py --preview | jq .
```
5) 產生報表
```bash
python scripts/build_reports.py
```

## 輸出位置與內容
- 目錄：`2025H1_技術中心/`
  - 首頁：`index.html`（每人 2025.H1 平均、與上一期差值、相對全體/部門差值、前 3 項優勢/弱項建議）
  - 個人頁：`姓名.html`（問卷回收份數、歷年排名百分比、雷達圖重疊 + ALL/部門平均、各部門對照 13 項水平條、詳細表格）
  - 個人歷年 CSV：`姓名.csv`

## 可調整設定（`scripts/build_reports.py`）
- 目標部門（預設 `智能技術中心`）
```python
TARGET_DEPARTMENT = "智能技術中心"
```
- 歷年資料清單（新增/移除期別）
```python
DATA_FILES = [
    "2023.H2.xlsx",
    "2024.H1.xlsx",
    "2024.H2.xlsx",
    "2025.H1.xlsx",
]
```

## 常見問題
- 欄位名有空白或全形句點？會自動標準化比對。
- 新增期別後首頁或個人頁沒有資料？確認 `DATA_FILES` 已包含，且 `總評分` 的 `受評者`、`部`、`平均` 欄位完整。
- 要分析其他部門？修改 `TARGET_DEPARTMENT` 後重跑腳本。
- 版本控管：建議把 `.venv/` 與輸出資料夾（如 `2025H1_技術中心/`）加入 `.gitignore`。

---
若需調整圖表樣式、優勢/弱項判定規則或部門/期別設定，請更新設定後重跑指令；也可在此 README 補充內部流程與口徑。

## Electron 介面（選用）
提供更友善的操作流程（拖拉檔案、檢核、選擇母體與部門、立即預覽、送出執行）。

### 功能
- 顯示目前讀取的檔案（來自 `config.json` 或拖拉加入）
- 拖拉加入更多檔案，並即時檢核可處理性
- 勾選母體表（母體檔）與處理的組別（部門）
- 選擇產出報表欄位（預設採用母體表）
- 送出執行，並顯示執行狀態

### 建置與啟動
（首次）
```bash
cd electron
npm install
npm run start
```

### 打包教學
```bash
cd electron
npm run build   # 產生安裝包（依 OS 不同而產生對應檔）
```

介面會呼叫後端 Python 指令：
- `python scripts/build_reports.py --validate` 檢核
- `python scripts/build_reports.py --preview` 預覽
- `python scripts/build_reports.py` 送出執行

若需讓介面將拖拉的檔案同步到設定，可手動更新根目錄的 `config.json` 之 `data_files` 與 `mother_file` 後再執行。