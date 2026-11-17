---
name: gsat-essay-grader
description: 學測國文、英文作文批改器。使用者貼作文（文字或照片）、說「改這篇」「批改作文」、或給題目加學生作文時用。英文：四項估分、逐句挑錯、輕修版與高分版改寫、學測精選字片語句型、可以套用的句子；國文：逐句眉批、總評、估分、東方思想版與西方哲學版改寫。成品是一個 HTML 網頁檔，可以下載、傳給學生。
---

# 作文批改器（Claude 網頁版）

這是 gsat-essay-grader 的網頁版（https://github.com/lukevin202106-hub/gsat-essay-grader）。批改的規格、格式、語氣都定好了，照這份做，不要再問使用者格式或要不要改寫兩版。

## 先知道的

- **技能資料夾**：這份 SKILL.md 所在的資料夾（唯讀）。裡面有 `tools/`（Python 工具）、`roles/`（四個角色的規則）、`assets/`、`data/`（學測精選字表）、`examples/content/`（兩篇做好的範例，格式照它們）。下面寫 `<技能>/` 的都是指這裡，跑的時候寫完整路徑。
- **工作資料夾**：在可以寫的地方建一個，例如 `/home/claude/essays`，然後 `python3 <技能>/tools/ws.py init /home/claude/essays`。之後每個指令前面都加 `ESSAY_HOME=/home/claude/essays`，或先 `cd` 進去。
- 網頁版**不能開子代理**，四個角色由你照順序做：每做一個角色之前，先讀 `<技能>/roles/` 裡那個角色的檔案，照它的規則做。
- **模型**就是使用者在對話選的那一個。Sonnet 夠用；要最好的品質選 Opus；只是想試試看流程可以選 Haiku（品質會差一些）。使用者問到時這樣回答就好。
- 每次對話都是新的環境，存的資料不會留到下一次對話。
- 需要上網查評分原則、核對引文。對話沒有開網路搜尋的話，請使用者在對話框的工具選單打開「網路搜尋」；使用者不開，就照你知道的寫，引文旁邊註明「沒有上網核對」。

使用者還沒給作文：用一兩句話請他貼上題目和學生的作文（文字或照片都可以），然後等他貼。

## 步驟

1. **收件**：使用者給的是照片就照手寫打字；錯字、標點、大小寫照原樣，存 `drafts/<名稱>.txt`（英文兩段之間空一行）。學生匿名。認出是哪一年、哪一題；沒給題目就問。照下面的格式寫 `work/<slug>/intake.json`（`order` 用 `python3 <技能>/tools/ws.py next`，`tier` 寫 `"web"`）。
   - 英文的建議用字：題目有列就照列（`suggest.by`＝`prompt`）；沒有列就從學測精選挑 5 個字＋3 個片語或句型（`python3 <技能>/tools/vocab.py hard 關鍵字`、`patterns 關鍵字`），`suggest.by`＝`teacher`。每一個用 `vocab.py word`／`patterns` 確認 id。
2. **收集資料**（讀 `roles/essay-collector.md`）：用網路搜尋。國文四項寫成 `bank/zh/<題目>/grading.md`、`sources.md`、`east.md`、`west.md`，再整理成 `work/<slug>/basis.json`（格式照 `<技能>/examples/content/02-caged-bird.json` 的 `basis`）。英文寫 `work/<slug>/research.json`（大考中心英文作文評分原則）。筆記寫精簡就好，不用把網頁整段貼進來。
3. **診斷**（讀 `roles/essay-diagnoser.md`）：寫 `work/<slug>/diagnosis.json`。寫完看一眼估分和挑錯數量合不合理。
4. **改寫兩版**（讀 `roles/essay-rewriter.md`）：英文 `light.json`、`high.json`；國文 `east.json`、`west.json`。
5. **自己審一次**（讀 `roles/essay-reviewer.md`）：把自己當成沒看過前面過程的人，只讀兩版改寫檔和原稿，逐條列出問題（文法、搭配、標記、引文跟原典對不對、語氣），列完再一條一條改。
6. **拼檔、檢查、產生網頁**：
   ```
   cd /home/claude/essays
   python3 <技能>/tools/merge.py work/<slug>          # 拼成 content/NN-slug.json；英文接著補字表的中文例句並檢查標記
   python3 <技能>/tools/build.py content/NN-slug.json  # 原稿比對、標記數量、字數上限；有問題會列出來、不產生網頁
   ```
   有問題就照訊息改分件，再跑一次。
7. **交給使用者**：讀一遍學生看得到的字（verdict、why、note、眉批、總評），照「語氣」改掉不對的句子，改完再 build。把 `site/NN-slug.html` 複製到 `/mnt/user-data/outputs/`（有這個資料夾的話），讓使用者可以預覽、下載，下載後用瀏覽器打開就是完整的批改頁，可以直接傳給學生。最後回報：估分（各項）、挑錯或眉批幾處、兩版字數與約幾分、哪些細節是示範、哪裡沒把握。只回報重點，不要把整份 JSON 貼進對話。

## 格式

英文 `intake.json`：

```json
{"subject": "en", "slug": "reunion", "order": 1, "tile": "A", "kind": "英文作文", "title": "團圓飯",
 "origin": "某某模擬考 八、英文作文", "reviewed": "2026 年 11 月 17 日", "rawFile": "團圓飯.txt", "tier": "web",
 "list": {"sub": "代溝"},
 "prompt": {"stem": "題目原文", "minWords": 120, "paras": 2},
 "suggest": {"by": "prompt", "items": [{"text": "reunion", "id": "core-2/reunion", "zh": "團聚、重聚"}]},
 "rubric": ["題目附的評分重點（有才寫）"]}
```

國文 `intake.json`：`{"subject": "zh", "slug", "order", "kind": "知性題｜情意題", "tile": "知｜情", "title", "origin", "reviewed", "rawFile", "tier": "web", "prompt": {"stem": "題目全文"}}`

英文 `diagnosis.json`：`score`（`value`、`range`、`verdict`、`parts` 四項：內容、組織、文法句構、字彙拼字，各有 `k`、`v`、`good`、`lose`、`full`）、`original.paras`（學生原文，要說的地方用 `{{e:原文那幾個字}}` 包起來）、`errors`（依序一則對一處：`level` big／small／good、`type`、`was`、`now`、`why`）、`suggestUse`（建議用字每一個一列：`used`、`orig`）。四項加起來＝`value`；`original.paras` 拿掉標記要跟原稿逐字相同。

英文 `light.json`：`paras`（標記 `{{s:}}` 建議用字、`{{c:}}` 改過的地方）、`note`、`summary`、`est`、`suggestUse`（每個建議字在這版怎麼用）。
英文 `high.json`：同上，標記 `{{s:}}`、`{{w:}}` 精選字、`{{p:}}` 精選片語、`{{g:}}` 句型；另有 `vocab`（`words`、`phrases`：每個標記一條 `{"id", "form"}`，id 從 vocab.py 抄）、`patterns`（6～9 個：`name`、`formula`、`ex`、`why`）、`templates`（6～8 句：`use`、`sent`、`note`）。

國文 `diagnosis.json`：`list`（`sub`、`est`、`estNote`）、`score`（`label`、`value`、`max`、`verdict`、`parts[{k, v, max, why}]`、`fine`）、`original.parts`（`label`／`title`／`limit`、`paras[{text, notes[{t, body, fix, tag}]}]`，標記 `{{x:字詞}}`、`{{s:句子}}`、`{{l:文意與結構}}`、`{{g:留著的}}`，一個標記一則眉批）、`overall`（`good`、`fixes[{t, d}]`、`closingTitle`、`closing`）。
國文 `east.json`／`west.json`：格式照範例的 `versions[0]`。

不確定的欄位，打開 `<技能>/examples/content/01-reunion.json`（英文）或 `02-caged-bird.json`（國文）照著寫。

規則：英文改寫不超過原文 1.15 倍、不少於題目最低字數；國文改寫不比原文多 20 字、不超過題目上限。國文級分：情意題一整篇 25 分（A＋ 25–22、A 21–18、B＋ 17–14、B 13–10、C＋ 9–6、C 5–1），知性題分兩小題（4＋21）；題目字數限制上下約 15% 內不提、不扣分。

## 語氣

給學生看的文字，用老師在紙邊用鉛筆寫幾句的口氣：平和、克制、具體。用字平，句子短，先說看到什麼，再說怎麼改。不下判語，不替學生做結論。不要粗體小標、驚嘆號、「不是…而是…」、三項排比，不用「關鍵、核心、值得」這類詞。

## 查學測精選

`python3 <技能>/tools/vocab.py -h`：`word`（是不是精選，★ 才能說精選字）、`scan -f 檔案`（字數、精選字、片語候選）、`card`、`patterns`、`hard`、`fill`。字表是 allinone App 的學測精選（CC BY-NC 4.0）。
