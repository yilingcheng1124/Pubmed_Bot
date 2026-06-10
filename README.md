# PubMed_Bot

> **EN** — An automated daily literature-surveillance pipeline. It searches PubMed across four clinical axes, keeps only high-quality journals (SCImago SJR Q1–Q2), summarises each article with Gemini, and routes the results to three destinations: Zotero, an email digest, and an Obsidian vault on Google Drive.
>
> **中文** — 每日自動化文獻追蹤系統。依四條臨床主軸搜尋 PubMed，只保留高品質期刊（SCImago SJR Q1–Q2），用 Gemini 產生中文摘要，再平行送往三個目的地：Zotero、Email 報告、Google Drive 上的 Obsidian 知識庫。

---

## 1. Features ｜ 功能特色

| EN | 中文 |
|----|------|
| Four independent search axes, each tagged on the result | 四條獨立搜尋主軸，結果自帶軸標籤 |
| Per-axis composable negative filters | 各軸可組合的負向過濾條件 |
| SCImago SJR Q1–Q2 journal-quality gate (runs *before* the expensive steps) | SCImago SJR Q1–Q2 期刊品質門檻（在耗資源步驟前先過濾） |
| Gemini summary + evidence rating, with automatic model fallback on overload | Gemini 摘要＋證據評級，過載時自動切換備援模型 |
| Branch A → Zotero · Branch B → Email · Branch C → Obsidian/Google Drive | A 分支→Zotero · B 分支→Email · C 分支→Obsidian/Google Drive |
| Runs unattended daily via GitHub Actions | 透過 GitHub Actions 每日無人值守執行 |

---

## 2. Architecture ｜ 系統架構

```
                 ┌─────────────────────────────────────────────┐
                 │  4 axes × independent PubMed search (mhda)   │
                 │  肺部疾病 / 感控 / 重症 / 博晟產品線          │
                 └───────────────────────┬─────────────────────┘
                                         │  union + axis tags
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │  SJR quality gate (SCImago Q1–Q2)            │
                 │  期刊品質門檻：低品質直接刷掉，省下後續成本   │
                 └───────────────────────┬─────────────────────┘
                                         │  survivors
                 ┌───────────────────────┼─────────────────────┐
                 ▼                       ▼                       ▼
        ┌────────────────┐     ┌──────────────────┐    ┌──────────────────┐
        │ Branch A       │     │ Branch B         │    │ Branch C         │
        │ Zotero ingest  │     │ Gemini → Email   │    │ .md → Google     │
        │ 書目存檔        │     │ 中文摘要報告      │    │ Drive (Obsidian) │
        └────────────────┘     └──────────────────┘    └──────────────────┘
```

**EN** — Searching is by **MeSH date (`mhda`)**, not entry date (`edat`): the query filters on `[PT]`/`[MH]` tags that are only assigned at indexing time, so `edat` would return ~0 every day.

**中文** — 搜尋用 **MeSH date（`mhda`）**，不是進站日（`edat`）。因為 query 依賴 `[PT]`/`[MH]` 標籤，而這些標籤要等編目索引完成才會掛上；用 `edat` 會每天抓到 0 篇。

---

## 3. Repository structure ｜ 專案結構

```
Pubmed_Bot/
├── pubmed_automation.py     # Main pipeline ｜ 主程式
├── sjr.py                   # SCImago SJR quartile lookup ｜ SJR 期刊分級查詢
├── get_refresh_token.py     # One-time local Google OAuth helper ｜ 本機一次性取得 Drive 授權
├── config/
│   └── settings.yaml        # Axes, negatives, SJR, report config ｜ 搜尋軸/負向/SJR/報告設定
├── data/
│   └── scimago.csv.gz       # SCImago journal table (gzipped) ｜ SCImago 期刊表（壓縮）
├── .github/workflows/
│   └── main.yml             # Daily GitHub Actions schedule ｜ 每日排程
├── .env.template            # Required secrets template ｜ 必填金鑰範本
└── requirements.txt
```

---

## 4. Prerequisites ｜ 環境需求

**EN**
- Python 3.10+
- A PubMed (NCBI) API key, a Gemini API key, a Zotero API key, a Gmail account (with an App Password) for sending mail, and a Google account whose Drive holds your Obsidian vault.

**中文**
- Python 3.10 以上
- 需備：PubMed (NCBI) API key、Gemini API key、Zotero API key、寄信用的 Gmail（需「應用程式密碼」），以及放 Obsidian 知識庫的 Google 帳號。

```bash
pip install -r requirements.txt
```

---

## 5. Secrets ｜ 金鑰設定

**EN** — Copy `.env.template` to `.env` for local runs, or add the same keys as **GitHub repository Secrets** for the scheduled run (Settings → Secrets and variables → Actions).

**中文** — 本機執行：把 `.env.template` 複製成 `.env` 填入；排程執行：到 **GitHub Repo → Settings → Secrets and variables → Actions** 加入同名 Secrets。

| Key ｜ 金鑰 | Purpose ｜ 用途 |
|------------|----------------|
| `PUBMED_API_KEY` | NCBI E-utilities key ｜ PubMed 搜尋 |
| `GEMINI_API_KEY` | Gemini summarisation ｜ Gemini 摘要 |
| `ZOTERO_API_KEY` / `ZOTERO_USER_ID` / `ZOTERO_COLLECTION_ID` | Branch A target ｜ Zotero 書目存檔目標 |
| `SENDER_EMAIL` / `SENDER_PASSWORD` / `RECEIVER_EMAIL` | Branch B email (Gmail App Password) ｜ Email 報告（Gmail 應用程式密碼） |
| `GDRIVE_CLIENT_ID` / `GDRIVE_CLIENT_SECRET` / `GDRIVE_REFRESH_TOKEN` / `GDRIVE_FOLDER_ID` | Branch C Google Drive (OAuth) ｜ Branch C Google Drive（OAuth） |

> **Note ｜ 注意** — Branch C uses **OAuth user credentials**, *not* a service account: a service account has no Drive storage quota on a personal Gmail and cannot upload. ｜ Branch C 用 **OAuth 個人帳號授權**，不是服務帳戶：服務帳戶在個人 Gmail 沒有 Drive 配額、無法上傳。

### 5.1 Google Drive OAuth (one-time) ｜ 取得 Drive 授權（一次性）

**EN**
1. Google Cloud Console → enable **Google Drive API**.
2. OAuth consent screen → **External**, add your own Gmail under **Test users**.
3. Credentials → **OAuth client ID** → type **Desktop app** → download the JSON as `credentials.json` into this folder.
4. Run the helper locally (it opens a browser):
   ```bash
   pip install google-auth-oauthlib
   python get_refresh_token.py
   ```
5. Copy the printed `GDRIVE_*` values into your Secrets. Get `GDRIVE_FOLDER_ID` from your vault folder's URL (`.../folders/THIS_PART`).

**中文**
1. Google Cloud Console → 啟用 **Google Drive API**。
2. OAuth 同意畫面 → 選 **External**，把自己的 Gmail 加進 **測試使用者**。
3. 憑證 → **OAuth 用戶端 ID** → 類型選 **桌面應用程式** → 下載 JSON 存成 `credentials.json` 放本資料夾。
4. 本機執行小工具（會跳出瀏覽器登入授權）：
   ```bash
   pip install google-auth-oauthlib
   python get_refresh_token.py
   ```
5. 把印出的 `GDRIVE_*` 值填進 Secrets。`GDRIVE_FOLDER_ID` 取自知識庫資料夾網址（`.../folders/這一串`）。

### 5.2 SCImago SJR data ｜ SJR 期刊資料

**EN** — The SJR gate needs the SCImago journal table. Download it once a year (it cannot be auto-downloaded — Cloudflare blocks bots):
1. Open <https://www.scimagojr.com/journalrank.php> → click **Download data**.
2. Save it as `data/scimago.csv`, then compress: `gzip -9 data/scimago.csv` → produces `data/scimago.csv.gz` (committed; the raw `.csv` is gitignored).

**中文** — SJR 門檻需要 SCImago 期刊表。一年下載一次（無法自動下載，Cloudflare 會擋機器人）：
1. 開 <https://www.scimagojr.com/journalrank.php> → 點 **Download data**。
2. 存成 `data/scimago.csv`，再壓縮：`gzip -9 data/scimago.csv` → 產生 `data/scimago.csv.gz`（進版控；原始 `.csv` 已 gitignore）。

---

## 6. Running ｜ 執行方式

**EN**
- **Locally**: `python pubmed_automation.py`
- **Scheduled**: GitHub Actions runs daily at **04:30 Taipei (UTC 20:30)**; you can also trigger it manually from the **Actions** tab (`workflow_dispatch`). GitHub schedules may run a few minutes late under load.

**中文**
- **本機**：`python pubmed_automation.py`
- **排程**：GitHub Actions 每天 **台北時間 04:30（UTC 20:30）** 自動跑；也可在 **Actions** 分頁手動觸發（`workflow_dispatch`）。GitHub 排程在高峰可能延遲幾分鐘。

---

## 7. How filtering works ｜ 篩選邏輯

**EN**
- **Axes** — `pulmonary / infection_control / critical_care / biosheng`. Each is searched independently; a PMID hit by several axes keeps all its tags.
- **Negatives** — composable subgroups (`nonhuman / pediatric / surgical / tcm / oncology`). The first three axes apply the full set; **biosheng omits `surgical`** (so implant/device topics aren't excluded).
- **SJR gate** — resolve the journal by ISSN against SCImago, take the best quartile across the matched-axis categories (with a **best-Q fallback** to the journal's overall best quartile), and keep **Q1–Q2** only.
- **Unindexed journals** — journals absent from SCImago pass through, flagged **`SJR：未收錄`** (no free/legal Impact-Factor source to fall back on).

**中文**
- **軸** — `肺部 / 感控 / 重症 / 博晟`。各自獨立搜尋；一篇被多軸命中會保留多個標籤。
- **負向** — 可組合子群（`nonhuman / pediatric / surgical / tcm / oncology`）。前三軸套完整負向；**博晟豁免 `surgical`**（避免擋掉植入物/器材主題）。
- **SJR 門檻** — 以 ISSN 對 SCImago 查期刊，取「該軸對應分類」的最佳分級（查不到時 **best-Q fallback** 用期刊整體最佳分級），只留 **Q1–Q2**。
- **未收錄期刊** — 不在 SCImago 的期刊照樣放行，標記 **`SJR：未收錄`**（IF 無免費合法來源可補）。

Each report (email + Obsidian note) shows the **journal, axis, and SJR grade**, and a `[Filter] N fetched → M passed` log distinguishes a genuinely empty day from a bug. ｜ 每份報告（Email＋Obsidian 筆記）都顯示 **期刊、領域軸、SJR 分級**；`[Filter] N fetched → M passed` 的 log 用來區分「合理的 0 篇」與「程式出錯的 0 篇」。

---

## 8. Configuration reference — `config/settings.yaml` ｜ 設定參考

**EN** — Everything tunable lives in `config/settings.yaml`; no code edits needed. The file has four top-level blocks:

**中文** — 所有可調項都在 `config/settings.yaml`，不必改程式。檔案分四個頂層區塊：

```yaml
query:     # what to search for (axes, keywords, negative filters) ｜ 搜尋什麼（軸、關鍵字、負向）
search:    # date window & pacing ｜ 日期窗與節流
sjr:       # journal-quality gate ｜ 期刊品質門檻
report:    # Gemini model, email, SMTP ｜ Gemini 模型、email、SMTP
```

### 8.1 Adding / editing a search axis ｜ 新增或修改搜尋軸

**EN** — Each entry under `query.axes` is one independent search. To add an axis, append a block with four fields:

**中文** — `query.axes` 底下每一筆就是一條獨立搜尋。新增一條軸，就附加一個含四個欄位的區塊：

```yaml
query:
  axes:
    - key: cardiology              # internal id (unique) ｜ 內部代號（唯一）
      name: '心臟科'                # display name in reports ｜ 報告顯示名稱
      core: '("heart failure" OR arrhythmia OR "myocardial infarction")'   # PubMed OR-query ｜ PubMed OR 查詢
      negatives: [nonhuman, pediatric]        # which negative subgroups to apply ｜ 套用哪些負向子群
      sjr_categories: ['Cardiology and Cardiovascular Medicine']   # SCImago category names (exact!) ｜ SCImago 分類名（須精確！）
```

> ⚠️ **`sjr_categories` must match the SCImago CSV exactly** — open `data/scimago.csv.gz`, look at the `Categories` column for the real spelling (e.g. there is **no** "Tissue Engineering and Biomaterials"). A wrong name silently falls back to the journal's overall best quartile. ｜ **`sjr_categories` 名稱必須與 SCImago CSV 完全一致** —— 打開 `data/scimago.csv.gz` 看 `Categories` 欄的實際拼法（例如**並沒有**「Tissue Engineering and Biomaterials」）。寫錯會無聲地退回用期刊整體最佳分級。

### 8.2 Negative subgroups ｜ 負向子群

**EN** — `query.negatives` defines reusable exclusion groups; each axis picks which to apply via its `negatives:` list. The shared `query.study_type_filter` (RCT / Meta-Analysis / Systematic Review + humans) is appended to every axis automatically.

**中文** — `query.negatives` 定義可重用的排除組；每條軸用自己的 `negatives:` 清單挑要套哪些。共用的 `query.study_type_filter`（RCT / 統合分析 / 系統性回顧 + 人類）會自動接到每條軸。

| Subgroup ｜ 子群 | Excludes ｜ 排除 |
|---|---|
| `nonhuman` | animal / rat / mouse / in vitro / cell line … |
| `pediatric` | pediatric / child / infant / neonatal |
| `surgical` | thoracotomy / perioperative / anaesthesia … (博晟 omits this ｜ 博晟不套) |
| `tcm` | traditional Chinese medicine / acupuncture … |
| `oncology` | `"Lung Neoplasms"[MH]` |

### 8.3 Key reference ｜ 參數對照

**`search:`**

| Key | Default | Meaning ｜ 作用 |
|---|---|---|
| `datetype` | `[mhda]` | Date axis. Keep `mhda` (MeSH date) — `edat` returns ~0/day. ｜ 日期軸，維持 `mhda`；用 `edat` 會每天 0 篇 |
| `lookback_days` | `1` | Window size. `1` = yesterday only. `>1` needs dedup first (else duplicates). ｜ 搜尋窗；1＝只昨天，>1 需先有去重 |
| `retmax` | `100` | Max results per axis ｜ 每軸最大回傳數 |
| `per_article_delay_seconds` | `13` | Pause after each passing article. Lower it on a paid API tier. ｜ 每篇通過後延遲；付費層可調小 |
| `inter_axis_delay_seconds` | `0.5` | Pause between axis searches ｜ 軸間延遲 |

**`sjr:`**

| Key | Default | Meaning ｜ 作用 |
|---|---|---|
| `enabled` | `true` | Turn the quality gate on/off. `false` = let everything through. ｜ 品質門檻開關；false＝全放行 |
| `csv_path` | `data/scimago.csv.gz` | SCImago table (`.gz` read transparently) ｜ SCImago 表（`.gz` 自動讀） |
| `allowed_quartiles` | `[Q1, Q2]` | Quartiles that pass ｜ 放行的分級 |
| `include_unindexed` | `true` | Journals absent from SCImago pass (flagged 未收錄) ｜ 未收錄期刊放行（標未收錄） |

**`report:`**

| Key | Default | Meaning ｜ 作用 |
|---|---|---|
| `gemini_model` | `gemini-2.5-flash` | Primary summarisation model ｜ 主摘要模型 |
| `gemini_fallback_models` | `[2.5-flash-lite, 2.0-flash]` | Tried in order on 503/overload ｜ 過載時依序切換 |
| `gemini_max_retries` | `4` | Attempts per model before fallback ｜ 每模型重試次數 |
| `gemini_backoff_base_seconds` | `15` | Exponential backoff base (15→30→60…) ｜ 退避基數 |
| `language` | `zh-TW` | Summary language ｜ 摘要語言 |
| `email_subject_prefix` | `[Future Lab]` | Subject line prefix ｜ 信件主旨前綴 |
| `smtp_host` / `smtp_port` | `smtp.gmail.com` / `587` | Mail server — change for non-Gmail ｜ 寄信伺服器，非 Gmail 可改 |

### 8.4 Maintenance ｜ 維護

- Refresh `data/scimago.csv.gz` once a year (see §5.2). ｜ `data/scimago.csv.gz` 一年更新一次（見 §5.2）。
- Re-run `get_refresh_token.py` if the Drive token is ever revoked. ｜ Drive token 若失效就重跑 `get_refresh_token.py`。

---

## Data source & attribution ｜ 資料來源與標註

**EN** — `data/scimago.csv.gz` is the **2025 edition** of the [SCImago Journal & Country Rank](https://www.scimagojr.com/) (SJR) dataset, derived from Elsevier's Scopus database. It is © SCImago / Scopus and is bundled here **for non-commercial, academic/personal use only**. SJR data is not covered by this project's MIT license; if you reuse it, credit SCImago and review their terms. Refresh it yearly per §5.2.

**中文** — `data/scimago.csv.gz` 為 [SCImago Journal & Country Rank](https://www.scimagojr.com/)（SJR）**2025 年版**資料，源自 Elsevier 的 Scopus 資料庫。著作權屬 SCImago / Scopus，於此**僅供非商業之學術／個人用途**打包附帶。SJR 資料不受本專案 MIT 授權涵蓋；如需再利用，請標註 SCImago 並自行確認其條款。每年依 §5.2 更新。

> SCImago, (n.d.). *SJR — SCImago Journal & Country Rank* [Portal]. Retrieved from https://www.scimagojr.com/

## License ｜ 授權

MIT License — see [LICENSE](LICENSE). The license covers the **code only**; bundled SCImago data is excluded (see above). ｜ MIT 授權**僅涵蓋程式碼**；附帶的 SCImago 資料不在此列（見上）。
