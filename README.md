# PubMed_Bot 🩺📚

*自架的 PubMed 文獻訂閱 / 追蹤機器人 — 每日自動監測新文獻、AI 摘要，是 PubMed Email Alert／RSS 的替代方案。*
*A self-hosted PubMed literature-alert / monitoring bot — daily automated monitoring with AI summaries, a free alternative to PubMed email alerts / RSS.*

---

## 1. 專案簡介 ｜ About The Project 📖

🇹🇼 這是一個「自動幫你追論文」的小幫手。它每天早上自動去 PubMed（全球最大的醫學文獻資料庫）幫你找出你關心領域的高品質新論文，用 AI 寫成好懂的中文摘要，然後寄到你的信箱，還能同步存進 Zotero 和 Obsidian 筆記。

🇬🇧 This is a little assistant that "tracks papers for you." Every morning it automatically searches PubMed (the world's biggest medical-literature database) for new, high-quality papers in the fields you care about, writes an easy-to-read summary with AI, emails it to you, and can also file it into Zotero and your Obsidian notes.

---

## 2. 最新更新 ｜ What's New 🆕

🇹🇼 最近一批更新（2026-06）：

🇬🇧 Latest updates (2026-06):

- **🔐 Google Drive 授權長效化**：修好了「筆記每 7 天就同步失敗」的問題（原因是 OAuth app 停在測試模式），並在失效時於信件最上方跳紅字提醒。
  **Long-lived Google Drive auth**: fixed the "notes stop syncing every 7 days" bug (the OAuth app was stuck in testing mode), and now the email shows a red alert at the top if the token dies.
- **✂️ 摘要不再被截斷**：修正一個會讓 AI 只讀到半篇摘要的隱形 bug，現在「一句話總結」更精準。
  **No more truncated abstracts**: fixed a hidden bug that fed AI only half the abstract; the one-line takeaways are now sharper.
- **🚬 新增「戒菸」主題線**，並讓每條主題線可各自設定期刊品質門檻。
  **Added a "smoking cessation" topic line**, and each topic line can now set its own journal-quality bar.
- **🔀 三個輸出（Email／Zotero／Obsidian）可各自開關**；🔎 強化了 GitHub 上的可搜尋度。
  **The three outputs (Email / Zotero / Obsidian) can each be switched on/off**; improved GitHub discoverability.

---

## 3. 為什麼要用這個專案？ ｜ Why Choose This? 🌟

🇹🇼 三個核心優點：

🇬🇧 Three core advantages:

- **✅ 只給你「好」論文，不被洪水淹沒**：內建期刊品質門檻（只留 SCImago SJR 高分期刊），幫你先過濾掉大量低品質內容。
  **Only good papers, no flood**: a built-in journal-quality gate (keeps only high-ranked SCImago SJR journals) filters out the noise for you.
- **🤖 讀不完？讓 AI 幫你讀**：每篇都有中文摘要，開頭還有「一句話總結」清單，通勤時滑一下就掌握重點。
  **Too much to read? Let AI read it**: every paper gets a Chinese summary, plus a one-line-takeaway list at the top — skim it on your commute.
- **🧩 完全免費、自己作主**：跑在免費的 GitHub Actions 上，所有搜尋條件、輸出去向都能自己改，不必付費訂閱。
  **Free and fully in your control**: runs on free GitHub Actions; every search rule and output destination is yours to change — no paid subscription.

---

## 4. 快速開始 ｜ Getting Started 🚀

🇹🇼 **前置需求**：Python 3.10 以上，以及幾組 API 金鑰（PubMed、Gemini，以及選用的 Zotero／Gmail／Google Drive）。

🇬🇧 **Prerequisites**: Python 3.10+, and a few API keys (PubMed, Gemini, plus optional Zotero / Gmail / Google Drive).

🇹🇼 **步驟一：下載專案、安裝套件**

🇬🇧 **Step 1: Clone and install**

```bash
git clone https://github.com/kau10082/Pubmed_Bot.git
cd Pubmed_Bot
pip install -r requirements.txt
```

🇹🇼 **步驟二：下載期刊品質資料**（一年一次）。到 [SCImago](https://www.scimagojr.com/journalrank.php) 點「Download data」，存成 `data/scimago.csv`，再壓縮：

🇬🇧 **Step 2: Get the journal-quality data** (once a year). On [SCImago](https://www.scimagojr.com/journalrank.php) click "Download data", save as `data/scimago.csv`, then compress:

```bash
gzip -9 data/scimago.csv
```

🇹🇼 **步驟三：填入金鑰**。把 `.env.template` 複製成 `.env` 填入（本機測試用）；正式排程則把同樣的值放進 GitHub → Settings → Secrets。

🇬🇧 **Step 3: Add your keys**. Copy `.env.template` to `.env` and fill it in (for local testing); for the scheduled run, put the same values into GitHub → Settings → Secrets.

🇹🇼 **步驟四（選用，Obsidian 同步才需要）：取得 Google Drive 授權**。

🇬🇧 **Step 4 (optional, only for Obsidian sync): authorize Google Drive.**

```bash
pip install google-auth-oauthlib
python get_refresh_token.py
```

> 🇹🇼 ⚠️ 記得把 Google OAuth app 設為 **Production（正式版）**，否則授權每 7 天會失效。
> 🇬🇧 ⚠️ Set your Google OAuth app to **Production**, otherwise the authorization expires every 7 days.

---

## 5. 基本使用方式 ｜ Usage ⚙️

🇹🇼 **自動執行**：設好 GitHub Secrets 後就完全不用管，每天台灣時間 **04:30** 自動寄信給你。

🇬🇧 **Automatic**: once your GitHub Secrets are set, it just runs every day at **04:30 (Taiwan time)** and emails you.

🇹🇼 **手動執行一次**：到 GitHub 的 **Actions** 分頁 → 選 **Run workflow**，還能用下拉選單臨時開關 Zotero／Email／Google Drive。

🇬🇧 **Run once manually**: go to the **Actions** tab → **Run workflow**; dropdowns let you toggle Zotero / Email / Google Drive just for that run.

🇹🇼 **在自己電腦跑**：

🇬🇧 **Run on your own computer**:

```bash
python pubmed_automation.py
# 臨時關掉某個輸出 / turn one output off for this run:
RUN_ZOTERO=off python pubmed_automation.py
```

🇹🇼 想改搜尋主題、關鍵字、品質門檻？全部都在 `config/settings.yaml`，改完存檔即可，**不用碰程式碼**。

🇬🇧 Want to change topics, keywords, or the quality bar? It's all in `config/settings.yaml` — just edit and save, **no coding required**.

---

## 6. 目錄結構 ｜ Repository Structure 🗂️

```
Pubmed_Bot/
├── pubmed_automation.py    # 主程式（搜尋→篩選→摘要→寄送）｜ main pipeline
├── sjr.py                  # 查期刊品質分級 ｜ journal-quality (SJR) lookup
├── get_refresh_token.py    # 一次性取得 Google Drive 授權 ｜ one-time Drive auth helper
├── config/
│   └── settings.yaml       # 所有設定（主題/關鍵字/門檻…）｜ all settings
├── data/
│   └── scimago.csv.gz      # 期刊品質資料表 ｜ journal-quality dataset
├── .github/workflows/
│   └── main.yml            # 每日自動排程 ｜ daily schedule
├── .env.template           # 金鑰填寫範本 ｜ secrets template
├── requirements.txt        # 需要的套件清單 ｜ dependencies
└── LICENSE                 # 授權條款 ｜ license
```

🇹🇼 一句話帶過各部分：`pubmed_automation.py` 是大腦（負責整個流程）、`sjr.py` 是品質守門員、`config/settings.yaml` 是你的「遙控器」（改這裡就能調整行為）、`data/` 放期刊評分資料、`.github/` 負責每天定時開跑。

🇬🇧 In a nutshell: `pubmed_automation.py` is the brain (runs the whole flow), `sjr.py` is the quality gatekeeper, `config/settings.yaml` is your "remote control" (change behavior here), `data/` holds the journal-ranking data, and `.github/` handles the daily schedule.

---

## 7. 貢獻指南 ｜ Contributing 🤝

🇹🇼 非常歡迎你一起讓它更好！不管是修 bug、加功能，還是只是回報問題，都很感謝 🙌

🇬🇧 Contributions are very welcome — bug fixes, new features, or just reporting an issue, all appreciated! 🙌

- **🐛 發現問題？** 到 **Issues** 開一則，描述你遇到的狀況就好。
  **Found a problem?** Open an **Issue** and describe what happened.
- **💻 想改程式？** 先 **Fork** 這個專案 → 開一個新分支 → 改完後發一個 **Pull Request**，我們會一起看。
  **Want to change the code?** **Fork** the repo → create a branch → open a **Pull Request** when you're done, and we'll review it together.

---

## 8. 授權條款 ｜ License 📜

🇹🇼 本專案**程式碼**採用 **MIT 授權**：你可以自由使用、修改、散布，商用也可以，只要保留原本的授權與版權標示即可。

🇬🇧 The **code** is under the **MIT License**: you're free to use, modify, and distribute it (commercial use included), as long as you keep the original license and copyright notice.

🇹🇼 ⚠️ 但附帶的期刊資料 `data/scimago.csv.gz` 來自 **SCImago（源自 Elsevier Scopus）**，僅供**非商業**學術／個人用途，**不在 MIT 授權範圍內**；若要再利用請標示 SCImago 出處並確認其條款。

🇬🇧 ⚠️ However, the bundled journal data `data/scimago.csv.gz` comes from **SCImago (derived from Elsevier Scopus)**, is for **non-commercial** academic/personal use only, and is **not covered by the MIT License**; if you reuse it, credit SCImago and review their terms.
