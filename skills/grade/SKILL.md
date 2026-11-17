---
name: grade
description: 學測國文、英文作文批改（gsat-essay-grader）。使用者貼作文（文字或照片）、說「改這篇」「批改作文」、或給題目加學生作文時用。英文：四項估分、逐句挑錯、輕修版／高分版改寫、學測精選字片語句型、可以套用的句子；國文：逐句眉批、總評、估分、東方思想版／西方哲學版改寫。三個等級：usual 省錢（預設）、best 最好、test 測試（全 Haiku）。成品是一篇一個 HTML 網頁，可以發佈成 Claude 網頁分享。
---

# 作文批改流程

外掛資料夾（工具、樣式、範例都在這裡）：`${CLAUDE_PLUGIN_ROOT}`。下面寫 `tools/…` 的，都是 `${CLAUDE_PLUGIN_ROOT}/tools/…`，跑的時候寫完整路徑。（如果上面沒有被換成真的路徑，外掛資料夾就是這份 SKILL.md 往上兩層的資料夾。）

工作資料夾（學生的作文、中間檔、成品）不在外掛裡：用 `python3 "${CLAUDE_PLUGIN_ROOT}/tools/ws.py" where` 看是哪裡。還沒有 `.essay-grader` 的話，問使用者要放哪（預設現在的資料夾），再 `ws.py init <資料夾>`。之後的 `drafts/`、`work/`、`content/`、`bank/`、`site/` 都在工作資料夾裡；跑腳本前先 `cd` 到工作資料夾，叫子代理時把兩個資料夾的**絕對路徑**都寫在 prompt 裡。

格式與流程都定好了，不要再問使用者格式、要不要改寫兩版。只有題目認不出來、原稿看不清楚、估分差很多拿不準時才問。

**網頁只能用 `tools/build.py` 產生**：不要自己寫 HTML、CSS，不要改版面；長相以 `examples/site/01-reunion.html`、`02-caged-bird.html` 為準，頁尾的 allinone 小廣告不要拿掉。build 報錯就改 JSON 再跑，不要繞過它。

使用者還沒給作文（例如從「開始批改」捷徑打開、只打了 `/gsat-essay-grader:grade`）：用一兩句話請他貼上題目和學生的作文（文字或照片都可以），順便說可以說「用最好的」「用測試等級」換等級，然後等他貼。

指令裡的 `python3`：Windows 上不能用就改成 `python` 或 `py -3`。

## 等級（`${CLAUDE_PLUGIN_ROOT}/tiers.json`）

| 等級 | 收集資料 | 診斷 | 改寫、修稿 | 盲審 | 一篇大約（API 牌價） |
|---|---|---|---|---|---|
| `usual` 省錢（預設） | Haiku | Sonnet | Sonnet | Haiku | 英 $2.7、國 $3.1～3.5 |
| `best` 最好 | Sonnet high | Fable high | Fable high | Opus high | 英 $9～10.5、國 $10.6～16 |
| `test` 測試 | Haiku | Haiku | Haiku | Haiku | 很便宜，品質明顯差，只拿來試流程 |

- 使用者說「最好」「best」才用 best；說「測試」「test」「全 Haiku」才用 test。等級寫進 `intake.json` 的 `tier`。
- 叫子代理時 `model`、`effort` 照 `tiers.json` 的 `tiers.<等級>.steps` 填。模型用不了（例如訂閱沒有 Fable）就用 `fallback`，並在回報裡說一聲。
- 用 Claude 訂閱（Pro／Max）跑不另外收錢，算在用量額度裡；表上的錢是用 API 金鑰時的估價。

## 子代理

四個子代理在外掛的 `agents/`：`gsat-essay-grader:essay-collector`、`gsat-essay-grader:essay-diagnoser`、`gsat-essay-grader:essay-rewriter`、`gsat-essay-grader:essay-reviewer`。叫的時候 prompt 第一行寫：外掛資料夾、工作資料夾的絕對路徑、這一篇的 `work/<slug>/`。子代理回報只要路徑和數字，不要把內容貼回主線。

找不到子代理（例如沒有用外掛安裝、只複製了 skill）：用 `general-purpose`，`model` 照表填，prompt 第一句寫「你的角色是 essay-xxx。先讀 `${CLAUDE_PLUGIN_ROOT}/agents/essay-xxx.md`，照裡面的規則做」。工具不能開子代理（Codex、Gemini CLI 等）：主線照順序自己做每一個角色，讀對應的 `agents/essay-xxx.md`；盲審那一步最好開一個新的工作階段，只給改寫檔。

## 步驟

| # | 步驟 | 誰 | 產出 |
|---|---|---|---|
| 1 | 收件：辨認題目、打字原稿、定等級 | 主線 | `drafts/<名稱>.txt`、`work/<slug>/intake.json` |
| 1.5 | 查題目資料：這一題找過沒有 | `python3 tools/bank.py check work/<slug>` | reuse → 跳過第 2 步；collect → 照它給的資料夾收集 |
| 2 | 收集資料（同時開 2～4 個） | essay-collector | 國文 `bank/zh/<題目鍵>_<標題>/*.md`；英文 `work/<slug>/research.json` |
| 3 | 診斷 | essay-diagnoser | `work/<slug>/diagnosis.json` |
| 4 | 改寫兩版（同時開 2 個） | essay-rewriter | 英文 `light.json`、`high.json`；國文 `east.json`、`west.json` |
| 5 | 盲審（每版一個，沒看過前面的） | essay-reviewer | `review-<版>.json` → 交回寫那一版的 rewriter 修 |
| 6 | 拼檔、檢查 | `python3 tools/merge.py work/<slug>` → `python3 tools/build.py content/<檔>.json` | `content/NN-slug.json`、`site/NN-slug.html` |
| 6.5 | 存題目資料 | `python3 tools/bank.py save work/<slug>` | 下次同一題不用重收 |
| 7 | 讀一遍、發佈、回報 | 主線 | Claude 網頁或本機 HTML |

主線在第 3、4 步之間看一眼 diagnosis.json 的估分和挑錯數量合不合理（不用逐條改）。

### 1 收件（主線）

- 使用者給的是照片就照手寫打字；錯字、標點、大小寫照原樣，存 `drafts/<名稱>.txt`（英文兩段之間空一行）。**學生匿名**，檔名與頁面都不寫真名。
- 認出是哪一年、哪一題（學測、參考試卷、模擬考、自訂題）。使用者沒給題目就問。
- `order` 用 `python3 tools/ws.py next`，`slug` 用英文小寫短字。`reviewed` 寫今天（「2026 年 11 月 17 日」這種寫法）。
- 英文的建議用字：題目有列（「提示」「建議使用」）就照列，`suggest.by` 寫 `prompt`；沒有列就從學測精選挑 5 個字＋3 個片語或句型（`python3 tools/vocab.py hard 關鍵字`、`patterns 關鍵字` 找跟題目有關的），`suggest.by` 寫 `teacher`，學生沒看過清單，不因沒用到扣分。每一個用 `vocab.py word`／`patterns` 確認 id。

英文 `intake.json`：

```json
{"subject": "en", "slug": "reunion", "order": 1, "tile": "A", "kind": "英文作文", "title": "團圓飯",
 "origin": "某某模擬考 八、英文作文", "reviewed": "2026 年 11 月 17 日", "rawFile": "團圓飯.txt", "tier": "usual",
 "list": {"sub": "代溝"},
 "prompt": {"stem": "題目原文", "minWords": 120, "paras": 2},
 "suggest": {"by": "prompt", "items": [{"text": "reunion", "id": "core-2/reunion", "zh": "團聚、重聚"}]},
 "rubric": ["題目附的評分重點（有才寫）"]}
```

國文 `intake.json`：`{"subject": "zh", "slug", "order", "kind": "知性題｜情意題", "tile": "知｜情", "title", "origin", "reviewed", "rawFile", "tier", "prompt": {"stem": "題目全文"}}`，認得出是哪一年哪一題就加 `"bankKey": "gsat-114-zh-1"` 這類好認的鍵。

### 1.5 查題目資料

`python3 tools/bank.py check work/<slug>`：
- **reuse**：不開收集子代理。國文把 `basis.json` 複製成 `work/<slug>/basis.json`（診斷完再補「這篇在這裡」），診斷、改寫直接讀那個資料夾的筆記；`thinkers.json` 看之前用過哪些思想家，換別的，學生多看一種。英文把 `bank/en/_shared/rubric.json` 複製成 `work/<slug>/research.json`。intake 加 `"collected": false`。
- **collect**：照它給的 `folder` 叫收集子代理。舊資料等級比較低時，把舊筆記路徑一起給，叫它核對、補強、覆蓋。

### 2 收集（essay-collector）

國文四項（同時開四個）：①評分原則、佳作、閱卷說明與老師補教解析 → `grading.md` ②題目引文原典 → `sources.md` ③東方思想資源 → `east.md` ④西方哲學資源 → `west.md`。主線讀完挑思想家，整理成 `work/<slug>/basis.json`（格式照 `${CLAUDE_PLUGIN_ROOT}/examples/content/02-caged-bird.json` 的 `basis`）。
英文：大考中心英文作文評分原則全部題目共用，`bank/en/_shared/rubric.json` 有了就不用收。`research.json` 可以加 `page` 欄位控制網頁「題目與依據」放多少：`{"intro": "取代 criteriaIntro", "extra": [三節左右、每節一到三條], "sources": [要列的 sources 第幾筆]}`；`checked`（查到／沒查到）不進網頁。

### 3 診斷（essay-diagnoser）

英文 `diagnosis.json`：

```json
{"score": {"value": 14, "range": "13～15", "verdict": "兩三句：整體在哪一級、差在哪",
   "parts": [{"k": "內容", "v": 4, "good": "做得好", "lose": "扣在哪（指到第幾處）", "full": "怎麼拿滿"},
             {"k": "組織", "v": 4, "good": "", "lose": "", "full": ""},
             {"k": "文法句構", "v": 3, "good": "", "lose": "", "full": ""},
             {"k": "字彙拼字", "v": 3, "good": "", "lose": "", "full": ""}]},
 "original": {"paras": ["Last Lunar New Year, … prepared a feast {{e:for it}}, but …", "第二段…"]},
 "errors": [{"level": "small", "type": "代名詞", "was": "prepared a feast for it", "now": "prepared a feast for us", "why": "it 指什麼不清楚。…"}],
 "suggestUse": [{"used": true, "orig": "用到了：had a reunion"}, {"used": false, "orig": "沒用到"}]}
```

- `original.paras` 拿掉 `{{e:}}` 後要跟原稿逐字相同；第 n 個 `{{e:}}` 對第 n 則 `errors`。
- `level`：big 大錯／small 小改／good 加分。四項加起來＝`value`。

國文 `diagnosis.json`：`list`（`sub`、`est`、`estNote`）、`score`（`label`、`value`、`max`、`verdict`、`parts[{k, v, max, why}]`、`fine`）、`original.parts`（`label`／`title`／`limit`、`paras[{text, notes[{t, body, fix, tag}]}]`）、`overall`（`good`、`fixes[{t, d}]`、`closingTitle`、`closing`，知性題可加 `rewrite`）。格式照 `${CLAUDE_PLUGIN_ROOT}/examples/content/02-caged-bird.json`。

國文級分：情意題一整篇 25 分（A＋ 25–22、A 21–18、B＋ 17–14、B 13–10、C＋ 9–6、C 5–1）；知性題分兩小題（4＋21）。題目字數限制上下約 15% 內不提、不扣分。

### 4 改寫（essay-rewriter，兩版同時開）

英文 `light.json`：`{"paras": [...], "note": "", "summary": "", "est": "17～18", "suggestUse": ["had a reunion（照你的）", …]}`，標記 `{{s:}}` 建議用字、`{{c:}}` 改過的地方。
英文 `high.json`：同上，標記 `{{s:}}` 建議用字、`{{w:}}` 精選字、`{{p:}}` 精選片語、`{{g:}}` 句型，另有：

```json
{"vocab": {"words": [{"id": "core-2/feast", "form": "feast"}], "phrases": [{"id": "phrases-writing/only-when", "form": "Only when"}]},
 "patterns": [{"name": "so … that", "formula": "so + much/many + N + that + 子句", "ex": "高分版原句", "why": "說明"}],
 "templates": [{"use": "第一段開頭：交代時間地點", "sent": "Last ___, my whole family gathered at ___ for a long-awaited ___.", "note": "可以換成什麼"}]}
```

國文 `east.json`／`west.json`：一個版本物件，格式照範例的 `versions[0]`。

字數：英文不超過原文 1.15 倍、不少於題目最低字數；國文不比原文多 20 字、不超過題目上限。

### 5 盲審（essay-reviewer）

每版開一個新的 reviewer，只給那一版的檔案、原稿路徑和核對引文用的筆記。意見寫 `review-<版>.json`，主線用 SendMessage 把路徑交回寫那一版的 rewriter 修（沒有 SendMessage 就開一個新的 rewriter，給它原檔＋意見）。只審一輪。交回修稿時提醒：標記包太長就縮小到真正改的字，不要為了拆標記多出一堆眉批；引文意思要整段一致。

### 6 拼檔與檢查

```
cd <工作資料夾>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/merge.py" work/<slug>          # 拼成 content/NN-slug.json；英文接著補字表的中文例句並檢查標記
python3 "${CLAUDE_PLUGIN_ROOT}/tools/build.py" content/NN-slug.json  # 原稿比對、標記數量、字數上限；有問題會列出來、不產生網頁
```

### 7 讀一遍、發佈、回報（主線）

- 讀一遍學生看得到的字（verdict、why、note、眉批、總評），照「語氣」改掉不對的句子；直接改 content JSON，改完再 build。只印說明文字和兩版正文，不要把整份 content JSON 印出來（字卡、出處很長，白花額度）。
- 發佈：有 Artifact 工具（Claude 網頁）就把 `site/NN-slug.html` 發佈成 Claude 網頁（預設只有自己看得到，要給學生看再在網頁上分享）；沒有就給使用者本機檔案的完整路徑，並用系統的方式幫他打開（Mac `open`、Windows `start`），也可以直接傳給學生。
- 回報：等級、有沒有沿用題目資料、估分（各項）、挑錯或眉批幾處、兩版字數與約幾分、哪些細節是示範、盲審抓到什麼、哪裡沒把握。

## 語氣

給學生看的文字，用老師在紙邊用鉛筆寫幾句的口氣：平和、克制、具體。用字平，句子短，先說看到什麼，再說怎麼改。不下判語，不替學生做結論。不要粗體小標、驚嘆號、「不是…而是…」、三項排比，不用「關鍵、核心、值得」這類詞（英文句型 It is worth V-ing 的中文解釋可以寫「值得」）。

## 查學測精選（tools/vocab.py）

字表是 `${CLAUDE_PLUGIN_ROOT}/data/gsat-vocab.json`（allinone App 的學測精選 3,000 字＋片語句型，CC BY-NC 4.0）。指令見 `python3 tools/vocab.py -h`：`word`（是不是精選）、`scan`（一段英文的字數、精選字、片語候選）、`card`、`patterns`、`hard`、`fill`。★ 才能說「精選字」。想用自己的字表，照同一個格式做一份，設 `ESSAY_VOCAB` 指過去。
