# gsat-essay-grader 作文批改器

用你自己的 Claude 批改學測國文、英文作文。貼上作文（文字或照片），它會估分、逐句挑錯或寫眉批、照學生的骨架改寫兩版，最後產生一頁網頁，可以直接傳給學生。

它是一個 [Claude Code](https://claude.com/claude-code) 外掛：一個流程（skill）加上四個子代理（收集資料、診斷、改寫、盲審）。用 Claude 訂閱（Pro／Max）跑不用另外申請 API 金鑰。

**範例**（學生同意公開）：

- [英文〈團圓飯〉](https://lukevin202106-hub.github.io/gsat-essay-grader/examples/site/01-reunion.html)：估分 14／20、逐句挑錯 33 處、輕修版與高分版
- [國文〈籠中鳥〉](https://lukevin202106-hub.github.io/gsat-essay-grader/examples/site/02-caged-bird.html)：情意題、眉批與總評、東方版與西方版

## 會做什麼

**英文作文**

- 估分：內容、組織、文法句構、字彙拼字，各 5 分，每一項寫做得好的、扣在哪、怎麼拿滿
- 原文照手寫稿打字，錯處畫波浪線，點一下跳到說明；逐句挑錯分成大錯、小改、加分
- 兩版改寫並排：輕修版只修錯、保留學生的內容；高分版補情節，換成學測精選的字、片語、句型
- 用到的學測精選字與片語（附中文與例句）、句型、可以直接套用的句子

**國文作文（學測國寫）**

- 逐句眉批：字詞、句子、文意與結構、可以留著的
- 總評：留著的、先動這三處、估分（對照大考中心級分）
- 兩版改寫：一篇接東方思想、一篇接西方哲學，照學生的骨架走，字數跟原文差不多；引文都核對過原典
- 題目與依據：評分原則、出處

給學生看的文字用老師在紙邊寫幾句的口氣：平、短、具體，不喊口號。

## 下載與安裝

**沒用過終端機也可以**：到下載頁照著做：**https://lukevin202106-hub.github.io/gsat-essay-grader/**

兩種用法，都要有 Claude 的付費方案（Pro 以上）：

| | 怎麼裝 | 適合 |
|---|---|---|
| Claude 網頁版或 App | 下載 [技能檔](https://github.com/lukevin202106-hub/gsat-essay-grader/releases/latest/download/gsat-essay-grader-skill.zip)，到 Claude 的「自訂 → 技能」上傳 | 最簡單，不用安裝任何東西 |
| Claude Code（完整版） | 下載 [Mac 安裝檔](https://github.com/lukevin202106-hub/gsat-essay-grader/releases/latest/download/gsat-essay-grader-mac.zip) 或 [Windows 安裝檔](https://github.com/lukevin202106-hub/gsat-essay-grader/releases/latest/download/gsat-essay-grader-windows.zip)，雙擊安裝 | 四個角色分工、三種等級、查過的資料會存下來 |

安裝檔會幫你裝好 Claude Code、Python 和作文批改器，在「文件」建一個「作文批改」資料夾，以後雙擊裡面的「開始批改」就好。

已經在用 Claude Code 的人，也可以直接裝外掛（需要 Python 3.9 以上）：

```
/plugin marketplace add lukevin202106-hub/gsat-essay-grader
/plugin install gsat-essay-grader@gsat-essay-grader
```

## 使用

1. 開一個放作文的資料夾，在那裡開 Claude Code（用安裝檔的話，雙擊「開始批改」）。
2. 說「幫我改這篇作文」，貼上題目和作文（或照片）；也可以打 `/gsat-essay-grader:grade`。
3. 第一次會問工作資料夾放哪。之後批完會產生 `site/NN-名稱.html`；如果你的 Claude Code 能發佈 Claude 網頁（Artifact），會直接發佈成一頁網頁，預設只有你看得到，要給學生看再分享連結。

學生的作文、中間檔、成品都只放在你的工作資料夾，不會進這個外掛。

## 三個等級

| 等級 | 怎麼叫 | 收集資料 | 診斷 | 改寫 | 盲審 | 一篇大約（API 牌價） |
|---|---|---|---|---|---|---|
| 省錢（預設） | 直接叫 | Haiku | Sonnet | Sonnet | Haiku | 英 US$2.7、國 US$3.1～3.5 |
| 最好 | 說「用最好的」 | Sonnet | Fable | Fable | Opus | 英 US$9～10.5、國 US$10.6～16 |
| 測試 | 說「用測試等級」 | Haiku | Haiku | Haiku | Haiku | 很便宜，拿來試流程 |

訂閱沒有 Fable 會自動改用 Opus。用訂閱跑算在用量額度裡，不另外收錢。模型可以在 `tiers.json` 自己改。

同一題已經有人寫過，國文的資料（評分原則、原典、思想資源）會存在工作資料夾的 `bank/`，下一篇不用重新上網查，省時間也省額度。

## 其他 AI 工具

Codex、Gemini CLI 這類工具沒有實測過。流程寫在 `skills/grade/SKILL.md`、各角色寫在 `agents/`，讓它讀 [AGENTS.md](AGENTS.md) 照著做，不能開子代理就照順序自己做每一個角色。

## 學測精選字表

`data/gsat-vocab.json` 是 allinone App（App Store 搜尋「Allinone 讀書計畫」）的學測精選：3,000 字（大考中心詞彙級數 L2～L5）和 1,259 條片語與句型，附中文與例句，App 裡免費的部分。英文批改用它判斷哪些是精選字、高分版要換哪些字。想用自己的字表，照同樣的格式做一份，設環境變數 `ESSAY_VOCAB` 指過去。

## 檔案

```
.claude-plugin/   外掛與市集設定
skills/grade/     批改流程（SKILL.md）
agents/           四個子代理：essay-collector、essay-diagnoser、essay-rewriter、essay-reviewer
tools/            ws.py（工作資料夾）、vocab.py（查字表）、merge.py（拼檔）、bank.py（題目資料）、build.py（產生網頁）；只需要 Python 3.9 以上
web-skill/        Claude 網頁版的技能說明（打包成技能檔）
install/          Mac、Windows 安裝程式
scripts/          package.py：打包三個下載檔（發 Release 用）
index.html        下載頁（GitHub Pages）
assets/           網頁的樣式與程式（會包進每一頁）
data/             學測精選字表
examples/         兩篇範例：drafts/ 原稿、content/ 批改檔、site/ 網頁
tiers.json        三個等級用哪個模型
```

## 授權

- 程式、流程、樣式：[MIT](LICENSE)
- `data/gsat-vocab.json`：[CC BY-NC 4.0](data/LICENSE.md)，出處 allinone 學測精選；可以改、可以分享，要註明出處，不能拿來賣或做成收費產品
- `examples/` 的學生作文：經作者同意公開，著作權屬原作者，只供示範，不在上面兩種授權裡

分數是照大考中心的評分表估的，不是正式成績。

---

## English

**gsat-essay-grader** is a Claude Code plugin that grades essays for Taiwan's GSAT (學測) — both the Chinese writing section and the English composition — using your own Claude subscription. It scores the essay against the CEEC rubric, marks every error or comments line by line, writes two rewrites that follow the student's own structure, and builds a single self-contained HTML page you can share.

```
/plugin marketplace add lukevin202106-hub/gsat-essay-grader
/plugin install gsat-essay-grader@gsat-essay-grader
```

Then paste an essay and say "grade this essay" (the output is in Traditional Chinese). No terminal experience? The download page (https://lukevin202106-hub.github.io/gsat-essay-grader/) has a skill file for claude.ai and one-click installers for macOS and Windows. Three tiers: `usual` (Haiku + Sonnet, default), `best` (Fable/Opus), `test` (all Haiku). Code is MIT; the bundled GSAT vocabulary list (`data/gsat-vocab.json`, from the allinone app) is CC BY-NC 4.0.
