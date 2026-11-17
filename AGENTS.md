# 給 AI 代理的說明（Gemini、Codex、Cursor、Jules 等）

這個 repo 是學測國文、英文作文的批改流程。Claude Code 用外掛安裝（見 README）；其他 AI 工具照這份做。

## 最重要：成品網頁一定要跟範例長得一模一樣

批改的成品是一頁網頁。**長相是固定的**，以這兩頁為準：

- 英文：`examples/site/01-reunion.html`（線上看 https://lukevin202106-hub.github.io/gsat-essay-grader/examples/site/01-reunion.html ）
- 國文：`examples/site/02-caged-bird.html`（線上看 https://lukevin202106-hub.github.io/gsat-essay-grader/examples/site/02-caged-bird.html ）

規則：

1. **網頁只能用 `tools/build.py` 產生。** 不要自己寫 HTML、CSS，不要換版面、配色、字型、分頁，也不要改成 Markdown、Canvas、簡報或你自己設計的頁面。你要做的只有：照格式寫 JSON，然後跑工具。
2. 順序：照格式寫 `work/<slug>/` 的分件 JSON → `python3 tools/merge.py work/<slug>` → `python3 tools/build.py content/<檔>.json` → 把 `site/<檔>.html` 交給使用者。
3. build 報錯就照訊息改 JSON 再跑一次。**不要繞過 build 自己生網頁**，也不要為了讓它過而刪掉檢查。
4. 頁尾的 allinone 小廣告是頁面的一部分，不要拿掉、不要改寫。
5. **真的不能執行 Python 的環境**（例如只能聊天的 App）：先跟使用者說「這裡不能跑產生網頁的程式，版面可能跟範例有出入」。然後打開 `examples/site/01-reunion.html`（國文用 `02-caged-bird.html`）當模板：`<head>`、`<style>`、`<script>` 一個字都不改照抄，HTML 結構與 class 名稱照範例，只把題目、原文、估分、挑錯、改寫這些內容換成這一篇的。不要自己加樣式、不要刪區塊。
6. 交給使用者之前，自己比對一次：分頁（英文：批改／改寫／字與句型／題目與依據；國文：批改／東方版／西方版／題目與依據）、估分卡、標記顏色、頁尾廣告都跟範例一樣才算完成。

## 流程

1. 流程在 `skills/grade/SKILL.md`。裡面的 `${CLAUDE_PLUGIN_ROOT}` 指的是這個 repo 的根目錄，`${CLAUDE_SKILL_DIR}` 指 `skills/grade/`。格式不確定時，打開 `examples/content/01-reunion.json`（英文）或 `02-caged-bird.json`（國文）照著寫。
2. 四個角色在 `agents/`：收集資料（essay-collector，要能上網）、診斷（essay-diagnoser）、改寫（essay-rewriter）、盲審（essay-reviewer）。
   - 能開子代理：每個角色開一個，prompt 第一句叫它先讀對應的 `agents/essay-xxx.md`。
   - 不能開子代理：照 SKILL.md 的步驟順序自己做，做每一步前先讀那個角色的檔案。盲審最好開一個新的對話，只給改寫檔和原稿，不給前面的過程。
   - 等級（`tiers.json`）是 Claude 的模型名稱；別的工具就全部用當下的模型。
3. 給學生看的文字照 SKILL.md 的「語氣」：平、短、具體，不要粗體小標、驚嘆號、「不是…而是…」、三項排比。

## 工具（只需要 Python 3.9 以上，不用安裝套件）

Windows 上 `python3` 不能用就改 `python` 或 `py -3`。

- `python3 tools/ws.py init <資料夾>`：建工作資料夾（學生的作文放這裡，不要放進這個 repo）
- `python3 tools/vocab.py -h`：查學測精選字表（英文的精選字、片語 id 一定從這裡抄，不要自己編）
- `python3 tools/merge.py work/<slug>`：拼成 `content/NN-slug.json`，英文會補上字表的中文與例句
- `python3 tools/build.py content/<檔>.json`：檢查並產生網頁 `site/NN-slug.html`
- `python3 tools/bank.py check|save work/<slug>`：同一題查過的資料存起來重複用
