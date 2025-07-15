參考 [**DelphiAgent: Multi-agent verification framework for automated fact verification**](https://github.com/zjfgh2015/DelphiAgent) 的 Multi-agent framework

## TODO

- SERP 
  - [Serper](https://serper.dev/) 
- crawler
  - [linkup](https://www.linkup.so/)
  - [exa](https://exa.ai/)
  - [crawl4ai](https://github.com/unclecode/crawl4ai): 太多 link 雜訊
  - [~~trafilatura~~](https://trafilatura.readthedocs.io/en/latest/index.html): 太不穩定

- 怎麼辨別來源是否可信?
  - 檢查 domain

## 前置要求

- Python 3.11
- uv

## 安裝步驟

### 1. 安裝 uv

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 建立虛擬環境

```bash
uv venv
```

### 3. 安裝依賴套件

```bash
uv pip sync
```

### 4. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env` 檔案並輸入你的 API key：
```
API_KEY=your_api_key_here
```
## 資料集

見 [DelphiAgent](https://github.com/zjfgh2015/DelphiAgent)

## 執行主程式

```bash
uv run python script.py
```
