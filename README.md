參考 [**DelphiAgent: Multi-agent verification framework for automated fact verification**](https://github.com/zjfgh2015/DelphiAgent) 架構實作的 Multi-agent framework

作者沒去實作 web search，找到的資料其實就決定了有沒有可能回答 claim，感覺加個 reasoning model 做 plan 要去甚麼網站找甚麼資料

## 實作

- MCP: 以 web search + web fetch MCP 讓 LLM 到 planner agent 的網站中自己找證據 (不用自己寫爬蟲)
    > [官方 MCP-server-fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch)
- Crawler: 以 SERP 找出 url，用 trafilatura 去爬蟲，影片用 youtube-transcript-api，PDF 用 PyMuPDF
    > [AVERITEC Shared Task](https://aclanthology.org/2024.fever-1.1.pdf)

    > [Dunamu-ml’s Submissions on AVERITEC Shared Task](https://aclanthology.org/2024.fever-1.7.pdf)

## TODO

- SERP 
  - [Serper](https://serper.dev/)
    - 社群媒體的資訊不可靠
- crawler
  - [linkup](https://www.linkup.so/): 要錢
  - [exa](https://exa.ai/): 要錢
- 開源套件
  - [crawl4ai](https://github.com/unclecode/crawl4ai): 多 link 雜訊
  - [trafilatura](https://trafilatura.readthedocs.io/en/latest/index.html): 不穩定
  - [crawl4ai + mistune](https://github.com/lepture/mistune): 搭 crawl4ai 沒啥用
  - readability-lxml + bs4: 似乎可用，但有以下問題
      - header, footer 雜訊

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
