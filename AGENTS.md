# 給其他 AI 代理工具的說明（Codex、Gemini CLI、Cursor 等）

這個 repo 是學測作文批改流程。Claude Code 用外掛安裝（見 README）；其他工具照下面做。沒有實測過，遇到問題歡迎開 issue。

1. 流程在 `skills/grade/SKILL.md`。裡面的 `${CLAUDE_PLUGIN_ROOT}` 指的是這個 repo 的根目錄，`${CLAUDE_SKILL_DIR}` 指 `skills/grade/`。
2. 四個角色在 `agents/`：收集資料（essay-collector，要能上網）、診斷（essay-diagnoser）、改寫（essay-rewriter）、盲審（essay-reviewer）。
   - 能開子代理：每個角色開一個，prompt 第一句叫它先讀對應的 `agents/essay-xxx.md`。
   - 不能開子代理：照 SKILL.md 的步驟順序自己做，做每一步前先讀那個角色的檔案。盲審最好開一個新的對話，只給改寫檔和原稿，不給前面的過程。
   - 等級（`tiers.json`）是 Claude 的模型名稱；別的工具就全部用當下的模型。
3. 工具都是 Python 3.9 以上，不用安裝套件（Windows 上 `python3` 不能用就改 `python` 或 `py -3`）：
   - `python3 tools/ws.py init <資料夾>`：建工作資料夾（學生的作文放這裡，不要放進這個 repo）
   - `python3 tools/vocab.py -h`：查學測精選字表
   - `python3 tools/merge.py work/<slug>`、`python3 tools/build.py content/<檔>.json`：拼檔、檢查、產生網頁
   - `python3 tools/bank.py check|save work/<slug>`：同一題的資料存起來重複用
4. 成品是工作資料夾的 `site/NN-slug.html`，一個檔就是一整頁，直接用瀏覽器打開。

格式範例看 `examples/content/01-reunion.json`（英文）與 `examples/content/02-caged-bird.json`（國文）。
