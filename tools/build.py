#!/usr/bin/env python3
"""建置：content/*.json（一篇作文一份）→ site/NN-slug.html（一篇一個完整的 HTML 檔，樣式與程式都包在裡面，
可以直接打開、傳給學生，或發佈成 Claude 網頁）。只需要 Python 3.9 以上，不用裝別的東西。

    python3 tools/build.py                       建工作資料夾裡全部的 content/*.json
    python3 tools/build.py content/03-x.json     只建這幾篇

國文會檢查：眉批數量對得上標記、原文跟 drafts/ 一樣、改寫版字數不超過「原文＋20」也不超過題目上限。
英文會檢查：原文跟 drafts/ 一樣、挑錯數量對得上標記、改寫版字數不超過原文的 1.15 倍、精選字片語都補過資料（vocab.py fill）。
有 translation（學測中譯英）時，「批改」前面多一個分頁「中譯英」，另外檢查：每題的原句拿掉 {{e:}} 後跟 drafts/ 的翻譯檔那一行一樣、
挑錯數量對得上標記、分數＝滿分−扣分、fixed 只用 {{c:}}、alts 剛好 2 個、alts 用到的精選字片語列在該題 vocab。格式見 skills/grade/SKILL.md。
有問題會列出來、不產生那一篇。
"""
import json
import math
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):      # Windows 的中文命令列是 Big5，印 ✗ 這類字會當掉；一律用 UTF-8
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ws import home  # noqa: E402

PLUGIN = HERE.parent
MAX_OVER = 20      # 國文改寫版最多比學生原文多幾個字
TOL = 1.15         # 題目的字數限制，上下約 15% 都算合理，不在頁面上評論
MAX_RATIO = 1.15   # 英文改寫版最多是原文的幾倍

ROOT = home()
OUT = ROOT / "site"
CSS = (PLUGIN / "assets" / "style.css").read_text(encoding="utf-8")
JS = (PLUGIN / "assets" / "app.js").read_text(encoding="utf-8")
TR_CSS = (PLUGIN / "assets" / "translation.css").read_text(encoding="utf-8")     # 只有有中譯英的頁面才包進去


# ── 小工具 ──
def esc(s):
    if s is None:
        s = ""
    elif isinstance(s, bool):
        s = "true" if s else "false"
    elif isinstance(s, (int, float)):
        s = num(s)
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))


def num(x):
    """數字照 JavaScript 的寫法印（14、714、460.00000000000006）"""
    if isinstance(x, float):
        if math.isinf(x):
            return "Infinity"
        if x == int(x):
            return str(int(x))
        return repr(x)
    return str(x)


def js_round(x):
    return math.floor(x + 0.5)


ZH_MARK = re.compile(r"\{\{([xslgpc]):([^}]+)\}\}")
EN_MARK = re.compile(r"\{\{([a-z]):([^}]+)\}\}")


def zh_plain(s):
    return ZH_MARK.sub(r"\2", s)


def en_plain(s):
    return EN_MARK.sub(r"\2", s)


def count(s):
    """國文字數：含標點、不含空白"""
    return len(re.sub(r"\s", "", zh_plain(s)))


def word_count(s):
    """英文字數：空白分開、有英數字的才算"""
    return len([w for w in re.split(r"\s+", en_plain(s)) if re.search(r"[A-Za-z0-9]", w)])


def draft(name):
    return (ROOT / "drafts" / name).read_text(encoding="utf-8")


def squash(t):
    return re.sub(r"\s", "", t)


TAG = {"x": "字詞", "s": "句子", "l": "文意", "g": "留著", "p": "思想", "c": "改動"}
problems = []
report = []

ICON_SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/></svg>'
ICON_MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.2 8.2 0 1 0 10.2 10.2z"/></svg>'


def shell(title, desc, body, en=False, wide=False, tr=False):
    """一頁完整的 HTML：樣式、程式都包在裡面，字型從 Google Fonts 載入（沒網路就用系統字型）"""
    en_font = "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400" if en else ""
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="color-scheme" content="light dark">
<meta name="generator" content="gsat-essay-grader">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Noto+Serif+TC:wght@400;600;700{en_font}&display=swap" rel="stylesheet">
<style>
{CSS}{chr(10) + TR_CSS.rstrip() if tr else ""}
</style>
<script>try{{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
</head>
<body>
<div class="sky" aria-hidden="true"></div>
<div class="waves" aria-hidden="true"><svg viewBox="0 0 1200 300" preserveAspectRatio="none"><path class="a" d="M0 150c120-50 240-60 380-20s250 60 400 10 280-70 420-10v170H0z"/><path class="b" d="M0 215c160-40 300-30 430 0s260 40 390 0 250-40 380 0v85H0z"/></svg></div>
<header class="wrap{" wide" if wide else ""} top">
  <span class="wordmark">作文批改</span>
  <button class="pill icon theme" type="button" aria-label="切換白天或晚上的配色"><span class="sun">{ICON_SUN}</span><span class="moon">{ICON_MOON}</span></button>
</header>
<main>
{body}
</main>
<script>
{JS}
</script>
</body>
</html>
"""


APP_URL = "https://allinone-ai.lukevin202106.workers.dev/"


def promo(subject):
    """頁尾的 allinone 小廣告（作者要的，不要拿掉）"""
    line = "學測英文要背的字、國文閱讀、數學動畫筆記，每天要做多少 App 幫你排好。學測精選 3,000 字免費"
    line += "，這頁標 ★ 的字都在裡面。" if subject == "en" else "。"
    return (f'<aside class="promo" aria-label="廣告"><span class="promo-tag">廣告</span>'
            f'<p><b>allinone 讀書計畫</b>{line}</p>'
            f'<a href="{APP_URL}" target="_blank" rel="noopener">看 allinone 官網</a></aside>')


# ───────────────────────── 國文 ─────────────────────────

def part_count(part):
    return sum(count(p["text"]) for p in part["paras"])


def render_part(part, ctx):
    n = part_count(part)
    wc = f"{n} 字"
    over = False
    if part.get("limit"):
        wc += f"（題目限 {num(part['limit'])} 字）"
        over = n > part["limit"] * TOL
    if ctx.get("baseCount") is not None:
        wc = f"原文 {ctx['baseCount']} 字 → 這一版 {n} 字" + (f"（題目限 {num(part['limit'])}）" if part.get("limit") else "")
    if part.get("label"):
        head = f'<div class="part-h"><h2>{esc(part["label"])}</h2><span class="wc{" over" if over else ""}">{wc}{"，多了不少" if over else ""}</span></div>'
    else:
        head = f'<div class="part-h"><h2>{esc(ctx.get("fallbackLabel") or "全文")}</h2><span class="wc">{wc}</span></div>'
    title = f'<p class="essay-title">{esc(part["title"])}</p>' if part.get("title") else ""
    paras = []
    for p in part["paras"]:
        notes = p.get("notes") or []
        state = {"i": 0}
        keys = []

        def mark(m):
            t, body = m.group(1), m.group(2)
            note = notes[state["i"]] if state["i"] < len(notes) else None
            state["i"] += 1
            ctx["seq"] += 1
            key = f"{ctx['prefix']}{ctx['seq']}"
            keys.append({"key": key, "n": ctx["seq"], "t": t})
            if note and note.get("t") and note["t"] != t:
                problems.append(f"{ctx['where']}：第 {ctx['seq']} 點標記是 {t}、眉批寫 {note['t']}")
            return f'<mark class="{t}" data-k="{key}" tabindex="0" role="button" aria-label="眉批 {ctx["seq"]}">{body}</mark>&#8288;<sup class="mk {t}" data-k="{key}" aria-hidden="true">{ctx["seq"]}</sup>'

        tx = ZH_MARK.sub(mark, esc(p["text"]))
        if state["i"] != len(notes):
            problems.append(f"{ctx['where']}：「{zh_plain(p['text'])[:12]}…」這段有 {state['i']} 個標記、{len(notes)} 則眉批")
        if notes:
            items = []
            for j, nt in enumerate(notes):
                k = keys[j] if j < len(keys) else {"key": "", "n": "?", "t": nt.get("t") or "l"}
                fix = f'<span class="fix">{inline(nt["fix"])}</span>' if nt.get("fix") else ""
                items.append(f'<li class="note {k["t"]}" data-k="{k["key"]}"><span class="n">{k["n"]}</span><div><span class="tag">{esc(nt.get("tag") or TAG.get(k["t"]))}</span>{inline(nt.get("body"))}{fix}</div></li>')
            lst = '<ol class="notes">' + "".join(items) + "</ol>"
        else:
            lst = '<div class="notes"></div>'
        paras.append(f'<div class="para{" flat" if p.get("flat") else ""}"><p class="tx">{tx}</p>{lst}</div>')
    return f'<section class="part">{head}{title}{"".join(paras)}</section>'


def cap_of(limit, base):
    return min((limit or math.inf) * TOL, base + MAX_OVER)


def essay_page(e):
    tabs = [("review", "批改")] + [(v["id"], v["tab"]) for v in e["versions"]] + [("basis", "題目與依據")]
    ctx = {"seq": 0, "prefix": "o", "where": f"{e['title']}・批改"}
    orig_counts = [part_count(p) for p in e["original"]["parts"]]
    for i, p in enumerate(e["original"]["parts"]):
        report.append([e["title"], f"原文 {p.get('label') or ''}", orig_counts[i], p.get("limit") or "—", "—"])
    rewrite = ""
    ov = e["overall"]
    if ov.get("rewrite"):
        rw = ov["rewrite"]
        n = count(rw["text"])
        cap = cap_of(rw.get("limit"), orig_counts[rw["base"]])
        report.append([e["title"], rw["title"], n, rw.get("limit") or "—", f"原文 {orig_counts[rw['base']]}，最多 {num(cap)}"])
        if n > cap:
            problems.append(f"{e['title']}・{rw['title']}：{n} 字，超過上限 {num(cap)} 字")
        rewrite = f'<h3>{esc(rw["title"])}</h3><p class="rw">{esc(rw["text"])}</p><p class="rw-n">{n} 字（含標點）。{inline(rw.get("note"))}</p>'
    if e.get("rawFile"):
        raw = re.sub(r"^\((一|二)\)$", "", draft(e["rawFile"]), flags=re.M)
        if any(p.get("title") for p in e["original"]["parts"]):
            raw = re.sub(r"^.+\n", "", raw, count=1)
        mine = "".join("".join(zh_plain(x["text"]) for x in p["paras"]) for p in e["original"]["parts"])
        if squash(raw) != squash(mine):
            problems.append(f"{e['title']}：批改頁的原文跟 drafts/{e['rawFile']} 不一樣，學生的字被動到了")

    good = "".join(f"<li>{inline(g)}</li>" for g in ov["good"])
    fixes = "".join(f'<li><div><b>{inline(f["t"])}</b>{inline(f["d"])}</div></li>' for f in ov["fixes"])
    closing = f'<h3>{esc(ov.get("closingTitle") or "下一步")}</h3><p>{inline(ov["closing"])}</p>' if ov.get("closing") else ""
    review = f"""
<div class="legend" aria-label="標記的意思">
  <span class="x"><i></i>字詞</span><span class="s"><i></i>句子</span><span class="l"><i></i>文意與結構</span><span class="g"><i></i>留著的</span>
</div>
<article class="card read essay-cols">
  {"".join(render_part(p, ctx) for p in e["original"]["parts"])}
</article>
<article class="card overall">
  <h2>總評</h2>
  <h3>留著的</h3>
  <ul class="good">{good}</ul>
  <h3>先動這三處</h3>
  <ol class="fixes">{fixes}</ol>
  {closing}
  {rewrite}
</article>"""

    versions = []
    for v in e["versions"]:
        vctx = {"seq": 0, "prefix": v["id"][0], "where": f"{e['title']}・{v['tab']}"}
        parts = []
        for i, p in enumerate(v["parts"]):
            src = v["basePart"] + i if v.get("basePart") is not None else i
            base = orig_counts[src]
            n = part_count(p)
            cap = cap_of(p.get("limit"), base)
            report.append([e["title"], f"{v['tab']} {p.get('label') or ''}", n, p.get("limit") or "—", f"原文 {base}，最多 {num(cap)}"])
            if n > cap:
                problems.append(f"{e['title']}・{v['tab']}{p.get('label') or ''}：{n} 字，超過上限 {num(cap)} 字")
            vctx["baseCount"] = base
            parts.append(render_part(p, vctx))
        quotes = "".join(
            f'<blockquote class="quote"><q>{esc(q["q"])}</q>'
            + (f'<span class="orig" lang="{q.get("lang") or "en"}">{esc(q["orig"])}</span>' if q.get("orig") else "")
            + f'<cite>{esc(q.get("cite"))}</cite>'
            + (f'<span class="plain">{inline(q["plain"])}</span>' if q.get("plain") else "")
            + "</blockquote>" for q in v["quotes"])
        warn = f'<p class="warn"><b>引的時候　</b>{inline(v["warn"])}</p>' if v.get("warn") else ""
        versions.append(f"""<section class="panel" id="panel-{v['id']}" data-name="{esc(v['tab'])}" role="tabpanel" hidden>
<article class="card thinker">
  <div class="who"><span class="tile read">{esc(v['tile'])}</span><div><h2>{esc(v['name'])}</h2><p>{esc(v['sub'])}</p></div></div>
  <p class="idea">{inline(v['idea'])}</p>
  <div>{quotes}</div>
  <p class="bridge">{inline(v['bridge'])}</p>
  {warn}
</article>
<div class="legend" style="padding-top:16px" aria-label="標記的意思">
  <span class="p"><i></i>引了思想的地方</span><span class="c"><i></i>改過的地方</span>
</div>
<article class="card read essay-cols">{"".join(parts)}</article>
</section>""")

    b = e["basis"]

    def material(m):
        if m.get("type") == "lab":
            return f'<p class="lab">{esc(m["text"])}</p>'
        if m.get("type") == "from":
            return f'<p class="from">{esc(m["text"])}</p>'
        cls = ' class="poem"' if m.get("type") == "poem" else ""
        return f'<p{cls}>{esc(m["text"])}</p>'

    def row(r):
        here = ""
        if r.get("here"):
            here = f'　<b>← {"這篇在這裡" if r["here"] is True else esc(r["here"])}</b>'
        cls = ' class="here"' if r.get("here") else ""
        return f'<tr{cls}><th>{esc(r["g"])}</th><td class="pts">{esc(r["pts"])}</td><td>{inline(r["d"])}{here}</td></tr>'

    tasks = "".join(f'<li>{esc(t["q"])}<span class="pt">{esc(t["pt"])}</span>' + (f'<span class="pt">{inline(t["note"])}</span>' if t.get("note") else "") + "</li>" for t in b.get("tasks") or [])
    tables = "".join(f'<h3>{esc(t["h"])}</h3><div class="tablewrap"><table><tbody>{"".join(row(r) for r in t["rows"])}</tbody></table></div>' for t in b.get("tables") or [])
    basis = f"""<section class="panel basis" id="panel-basis" data-name="題目與依據" role="tabpanel" hidden>
<article class="card read">
  <h2>題目</h2>
  <p>{esc(b.get('origin'))}</p>
  <div class="material">{"".join(material(m) for m in b.get("material") or [])}</div>
  <ul class="tasks">{tasks}</ul>
</article>
<article class="card">
  <h2>{esc(b.get('criteriaTitle'))}</h2>
  <p>{inline(b.get('criteriaIntro'))}</p>
  {tables}
  {extra_html(b)}
</article>
<article class="card">
  <h2>出處</h2>
  <ul class="srcs">{sources_html(b)}</ul>
</article>
</section>"""

    sc = e["score"]
    parts_html = "".join(f'<li><span class="k">{esc(p["k"])}</span><span class="v">{esc(p["v"])}' + (f'<small>／{num(p["max"])}</small>' if p.get("max") else "") + f'</span><span class="why">{inline(p.get("why"))}</span></li>' for p in sc["parts"])
    seg = "".join(f'<button type="button" role="tab" data-tab="{tid}" aria-selected="{"true" if i == 0 else "false"}" aria-controls="panel-{tid}">{esc(label)}</button>' for i, (tid, label) in enumerate(tabs))
    edition = f'<small class="ed">{esc(e["edition"])}</small>' if e.get("edition") else ""
    vjoin = "\n".join(versions)
    body = f"""<div class="wrap wide">
<div class="essay-head">
  <p class="src">{esc(e['kind'])}　{esc(e['origin'])}</p>
  <h1>{esc(e['title'])}{edition}</h1>
</div>
<article class="card score">
  <div>
    <div class="big"><span class="lab">{esc(sc['label'])}</span><span class="gold-num">{esc(sc['value'])}</span><span class="of">／{num(sc['max'])}</span></div>
    <p class="verdict">{inline(sc['verdict'])}</p>
  </div>
  <div>
    <ul class="parts">{parts_html}</ul>
    <p class="fine">{inline(sc.get('fine'))}</p>
  </div>
</article>
<div class="seg-wrap"><div class="seg" role="tablist" aria-label="這篇作文的內容">
  {seg}
</div></div>
<section class="panel" id="panel-review" data-name="批改" role="tabpanel">{review}</section>
{vjoin}
{basis}
<footer class="foot">{esc(e['reviewed'])}改。分數是照大考中心的評分表抓的，不是正式成績。<br>用 gsat-essay-grader 批改。</footer>
{promo('zh')}
</div>"""
    tabs_zh = "、".join(v["tab"] for v in e["versions"])
    return shell(f"{e['title']}｜作文批改", f"{e['origin']}「{e['title']}」的眉批、估分，和{tabs_zh}兩篇改寫。", body, wide=True)


def extra_html(b):
    out = []
    for x in b.get("extra") or []:
        lis = "".join("<li>" + inline(i) + "</li>" for i in x["items"])
        out.append(f'<h3>{esc(x["h"])}</h3><ul class="dots">{lis}</ul>')
    return "".join(out)


def sources_html(b):
    out = []
    for s in b.get("sources") or []:
        head = f'<a href="{esc(s["u"])}" target="_blank" rel="noopener noreferrer">{esc(s["t"])}</a>' if s.get("u") else esc(s["t"])
        out.append(f'<li>{head}' + (f'<small>{esc(s["note"])}</small>' if s.get("note") else "") + "</li>")
    return "".join(out)


# ───────────────────────── 英文 ─────────────────────────
LV = {"big": "大錯", "small": "小改", "good": "加分"}
VCLS = {"s": "sg", "c": "ch", "w": "wd", "p": "ph", "g": "pt"}
VLAB = {"s": "建議用到", "c": "改過的地方", "w": "學測精選字", "p": "學測精選片語", "g": "句型"}
PART_KEYS = ["內容", "組織", "文法句構", "字彙拼字"]
# 學測第二大題中譯英：每題 4 分，原則上每個錯誤扣 0.5 分，同樣的錯誤只扣一次
TR_SRC = {"t": "113 學測英文科閱卷說明（聯合新聞網）", "u": "https://udn.com/news/story/6925/7755668"}
TR_BASIS = "中譯英每題 4 分，原則上每個錯誤扣 0.5 分，同樣的錯誤只扣一次（107、110、113 學測閱卷說明）。"


def english_page(e):
    where = e["title"]
    E_MARK = re.compile(r"\{\{e:([^}]+)\}\}")

    def tr_where(i):
        return f"中譯英第 {i + 1} 題"

    def tr_fmt(n):
        return num(js_round(n * 100) / 100)

    def need(cond, msg):
        if not cond:
            problems.append(f"{where}：{msg}")

    def para_count(v):
        return sum(word_count(p) for p in v["paras"])

    def en(s):
        return f'<span class="en-text" lang="en">{esc(s)}</span>'

    # ── 檢查 ──
    orig_n = para_count(e["original"])
    cap = js_round(orig_n * MAX_RATIO)
    mn = e["prompt"].get("minWords") or 0
    report.append([where, "原文", orig_n, f"至少 {mn}", "—"])
    for k, lab in (("light", "輕修版"), ("high", "高分版")):
        n = para_count(e[k])
        report.append([where, lab, n, f"至少 {mn}", f"原文 {orig_n}，最多 {cap}"])
        need(n <= cap, f"{lab} {n} 字，超過原文的 {MAX_RATIO} 倍（{cap}）")
        need(n >= mn, f"{lab} {n} 字，比題目要求的 {mn} 字少")
    if e.get("rawFile"):
        need(squash(draft(e["rawFile"])) == squash("".join(en_plain(p) for p in e["original"]["paras"])),
             f"批改頁的原文跟 drafts/{e['rawFile']} 不一樣，學生的字被動到了")
    n_marks = sum(1 for p in e["original"]["paras"] for m in EN_MARK.finditer(p) if m.group(1) == "e")
    need(n_marks == len(e["errors"]), f"原文有 {n_marks} 個 {{{{e:}}}} 標記，挑錯有 {len(e['errors'])} 則")
    for i, x in enumerate(e["errors"]):
        need(x.get("level") in LV, f"第 {i + 1} 則挑錯的 level 要是 big／small／good")
    need(len(e["suggestUse"]) == len(e["suggest"]["items"]), f"建議用字 {len(e['suggest']['items'])} 個，對照表 {len(e['suggestUse'])} 列")
    need([p["k"] for p in e["score"]["parts"]] == PART_KEYS, f"估分四項要照順序：{'、'.join(PART_KEYS)}")
    need(sum(p["v"] for p in e["score"]["parts"]) == e["score"]["value"], f"四項加起來不等於總分 {num(e['score']['value'])}")
    forms = {"w": {x["form"].lower() for x in e["vocab"]["words"]}, "p": {x["form"].lower() for x in e["vocab"]["phrases"]}}
    for x in e["vocab"]["words"] + e["vocab"]["phrases"]:
        need(x.get("lib"), f"{x['id']} 還沒補字表的資料，先跑 python3 tools/vocab.py fill content/…json")
    for k in ("light", "high"):
        for p in e[k]["paras"]:
            for m in EN_MARK.finditer(p):
                t, body = m.group(1), m.group(2)
                if t in ("w", "p"):
                    need(body.lower() in forms[t], f"{k} 的 {{{{{t}:{body}}}}} 沒列在 vocab")
                need(t in VCLS, f"{k} 有不認得的標記 {{{{{t}:…}}}}")

    # ── 中譯英檢查（有 translation 才跑）──
    tr = e.get("translation")
    if tr:
        items = tr.get("items") or []
        need(len(items) > 0, "translation.items 是空的")
        need(isinstance(tr.get("verdict"), str) and tr.get("verdict"), "translation 缺 verdict")
        if tr.get("rawFile"):
            lines = [l.strip() for l in draft(tr["rawFile"]).splitlines()]
            while lines and not lines[-1]:
                lines.pop()
            need(len(lines) == len(items), f"drafts/{tr['rawFile']} 有 {len(lines)} 行，translation 有 {len(items)} 題")
            for i, it in enumerate(items):
                need(isinstance(it.get("original"), str) and E_MARK.sub(r"\1", it["original"]).strip() == (lines[i] if i < len(lines) else None),
                     f"{tr_where(i)}的 original 拿掉 {{{{e:}}}} 後跟「drafts/{tr['rawFile']}」第 {i + 1} 行不一樣，學生的字被動到了")
        for i, it in enumerate(items):
            w = tr_where(i)
            errs = it.get("errors") or []
            need(it.get("zh") and it.get("original"), f"{w}缺 zh 或 original")
            marks = E_MARK.findall(it.get("original") or "")
            need(len(marks) == len(errs), f"{w}原句有 {len(marks)} 個 {{{{e:}}}} 標記，挑錯有 {len(errs)} 則")
            for j, x in enumerate(errs):
                need(x.get("level") in LV, f"{w}第 {j + 1} 則挑錯的 level 要是 big／small／good")
                d = x.get("deduct")
                need(isinstance(d, (int, float)) and not isinstance(d, bool) and d >= 0, f"{w}第 {j + 1} 則挑錯的 deduct 要是 0 以上的數字")
                if x.get("level") != "big":
                    need(d == 0, f"{w}第 {j + 1} 則是{LV.get(x.get('level'), '?')}，deduct 要是 0")
            mx = it["max"] if it.get("max") is not None else tr.get("max")
            cut = sum(x["deduct"] for x in errs if isinstance(x.get("deduct"), (int, float)) and not isinstance(x.get("deduct"), bool))
            sc_ = it.get("score")
            need(isinstance(sc_, (int, float)) and isinstance(mx, (int, float)) and abs(sc_ - max(0, mx - cut)) < 1e-9,
                 f"{w}score {num(sc_) if isinstance(sc_, (int, float)) else sc_} 不等於 {num(mx)} − 扣分 {tr_fmt(cut)}")
            need(it.get("fixed") and not re.search(r"\{\{[abd-z]:", it["fixed"]), f"{w}缺 fixed，或 fixed 用了 {{{{c:}}}} 以外的標記")
            alts = it.get("alts")
            need(isinstance(alts, list) and len(alts) == 2 and all(a.get("text") and a.get("note") for a in alts), f"{w}要有剛好 2 個 alts，每個有 text 和 note")
            v = it.get("vocab") or {"words": [], "phrases": []}
            tf = {"w": {x["form"].lower() for x in v.get("words", [])}, "p": {x["form"].lower() for x in v.get("phrases", [])}}
            for x in v.get("words", []) + v.get("phrases", []):
                need(x.get("lib"), f"{w}的 {x['id']} 還沒補字表的資料，先跑 python3 tools/vocab.py fill content/…json")
            for t in [it.get("fixed") or ""] + [a.get("text") or "" for a in (alts if isinstance(alts, list) else [])]:
                for m in EN_MARK.finditer(t):
                    k, body = m.group(1), m.group(2)
                    need(k in VCLS, f"{w}有不認得的標記 {{{{{k}:…}}}}")
                    if k in ("w", "p"):
                        need(body.lower() in tf[k], f"{w}的 {{{{{k}:{body}}}}} 沒列在這題的 vocab")

    # ── 原文作答紙 ──
    seq = {"n": 0}

    def emark(m):
        seq["n"] += 1
        s = seq["n"]
        lv = (e["errors"][s - 1] if s - 1 < len(e["errors"]) else {}).get("level") or "small"
        return f'<mark class="err lv-{lv}" data-k="e{s}" tabindex="0" role="button" aria-label="第 {s} 處，{LV.get(lv, "")}">{m.group(1)}</mark>&#8288;<sup class="en-n lv-{lv}" data-k="e{s}" aria-hidden="true">{s}</sup>'

    orig_html = "".join("<p>" + E_MARK.sub(emark, esc(p)) + "</p>" for p in e["original"]["paras"])
    tally = {k: sum(1 for x in e["errors"] if x.get("level") == k) for k in LV}
    err_html = "".join(f"""<li class="ecard lv-{x['level']}" data-k="e{i + 1}" data-lv="{x['level']}">
    <div class="eh"><span class="no">{i + 1}</span><span class="lv">{LV[x['level']]}</span><span class="ty">{esc(x['type'])}</span></div>
    <p class="wn was"><span class="lab">原句</span>{en(x['was'])}</p>
    <p class="wn now"><span class="lab">{"可以" if x['level'] == "good" else "改成"}</span>{en(x['now'])}</p>
    <p class="why">{inline(x['why'])}</p>
  </li>""" for i, x in enumerate(e["errors"]))

    used = sum(1 for u in e["suggestUse"] if u.get("used"))
    sug = e["suggest"]
    by_teacher = "（題目沒有列，老師從學測精選挑的；寫的時候沒看到，不算分）" if sug.get("by") == "teacher" else ""
    chips = "".join(f'<li lang="en">{esc(s["text"])}</li>' for s in sug["items"])
    prompt_card = f"""<article class="card prompt-card">
  <h2>題目</h2>
  <p class="q">{esc(e['prompt']['stem'])}</p>
  <p class="chips-lab">建議用到{by_teacher}</p>
  <ul class="chips">{chips}</ul>
  <div class="stats3">
    <div><b>{orig_n}</b><span>你的字數（至少 {mn}）</span></div>
    <div><b>{used}／{len(sug['items'])}</b><span>用到建議的</span></div>
    <div><b>{len(e['errors'])}</b><span>處要看：大錯 {tally['big']}、小改 {tally['small']}、加分 {tally['good']}</span></div>
  </div>
</article>"""

    review = f"""{prompt_card}
<article class="card read">
  <div class="card-h"><h2>你的原文</h2><span class="count">{orig_n} 字</span></div>
  <div class="sheet orig"><div class="label"><span>照手寫稿打字，錯字照原樣</span><span>點波浪線看說明</span></div>{orig_html}</div>
</article>
<article class="card">
  <div class="card-h"><h2>逐句挑錯</h2><span class="count">{len(e['errors'])} 處</span></div>
  <div class="filters" role="group" aria-label="篩選">
    <button type="button" data-f="all" aria-pressed="true">全部</button>
    <button type="button" data-f="big" aria-pressed="false">大錯 {tally['big']}</button>
    <button type="button" data-f="small" aria-pressed="false">小改 {tally['small']}</button>
    <button type="button" data-f="good" aria-pressed="false">加分 {tally['good']}</button>
  </div>
  <ol class="ecards">{err_html}</ol>
</article>"""

    # ── 兩版改寫 ──
    def vpara(p):
        return "<p>" + EN_MARK.sub(lambda m: f'<mark class="{VCLS.get(m.group(1), "")}" title="{VLAB.get(m.group(1), "")}">{m.group(2)}</mark>', esc(p)) + "</p>"

    def vcol(k, name, label_note):
        return f"""<div class="vcol">
    <div class="vhead"><h3>{name}</h3><span>{para_count(e[k])} 字・約 {esc(e['score'][k])} 分</span></div>
    <div class="sheet"><div class="label"><span>{label_note}</span></div>{"".join(vpara(p) for p in e[k]['paras'])}</div>
    <p class="vnote">{inline(e[k]['note'])}</p>
  </div>"""

    toggles = '<div class="toggles" role="group" aria-label="標記開關">' + "".join(
        f'<label><input type="checkbox" id="t-{VCLS[t]}" checked><mark class="{VCLS[t]}">{VLAB[t]}</mark></label>' for t in ("s", "c", "w", "p", "g")) + "</div>"
    rows = []
    for i, s in enumerate(sug["items"]):
        u = e["suggestUse"][i] if i < len(e["suggestUse"]) else {}
        orig = inline(u.get("orig") or ("用到了" if u.get("used") else "沒用到"))
        rows.append(f"""<tr><th scope="row">{en(s['text'])}<small>{esc(s.get('zh') or '')}</small></th>
      <td class="{"" if u.get("used") else "miss"}">{orig}</td><td class="mix">{esc(u.get('light') or '')}</td><td class="mix">{esc(u.get('high') or '')}</td></tr>""")
    sug_table = f"""<article class="card">
  <h2 class="h2">建議的 {len(sug['items'])} 個怎麼用</h2>
  <div class="tablewrap"><table class="tbl">
    <thead><tr><th scope="col">建議</th><th scope="col">你的原文</th><th scope="col">輕修版</th><th scope="col">高分版</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</article>"""
    versions = f"""<article class="card read">
  <p class="lede">{inline(e.get('versionsIntro') or '')}</p>
  {toggles}
  <div class="versions">{vcol("light", "輕修版", "綠底＝改過的地方，金底＝建議用到")}{vcol("high", "高分版", "底線＝精選字，紫底＝精選片語，紫字＝句型")}</div>
</article>
{sug_table}"""

    # ── 字與句型 ──
    def wcard(x):
        c = x["lib"]
        head = c.get("word") or c.get("phrase")
        pos = f'<span class="pos">{esc(c["pos"])}</span>' if c.get("pos") else ""
        if c.get("gsat"):
            lvl = (" L" + num(c["level"])) if c.get("level") else ""
            star = f'<span class="star" title="學測精選">★{lvl}</span>'
        else:
            star = f'<span class="nostar">{esc(x.get("note") or "不在精選")}</span>'
        ex = f'<div class="wex" lang="en">{esc(c["ex"])}</div><div class="wexzh">{esc(c.get("exZh"))}</div>' if c.get("ex") else ""
        return f"""<li><div class="wtop"><span class="wword" lang="en">{esc(head)}</span>{pos}{star}</div>
    <div class="wzh">{esc(c.get('zh'))}</div>{ex}</li>"""

    def n_star(xs):
        return sum(1 for x in xs if x.get("lib") and x["lib"].get("gsat"))

    pats = "".join(f'<li><h3>{esc(p["name"])}</h3><p class="formula" lang="en">{esc(p["formula"])}</p><p class="ex" lang="en">{esc(p["ex"])}</p><p class="why">{inline(p["why"])}</p></li>' for p in e["patterns"])
    tpl = "".join(f'<li><p class="tuse">{esc(t["use"])}</p><p class="tsent"><span lang="en">{esc(t["sent"])}</span><button type="button" class="copy" data-t="{esc(t["sent"])}">複製</button></p><p class="tnote">{inline(t["note"])}</p></li>' for t in e["templates"])
    vw, vp = e["vocab"]["words"], e["vocab"]["phrases"]
    words = f"""<article class="card read">
  <div class="card-h"><h2>用到的學測精選字、片語</h2></div>
  <p class="fine">★＝學測精選，L 是大考中心詞彙級數。中文與例句取自 allinone App 的學測精選。</p>
  <details class="box" open><summary>精選字<span>{n_star(vw)} 個</span></summary><ul class="wlist">{"".join(wcard(x) for x in vw if x.get("lib"))}</ul></details>
  <details class="box" open><summary>精選片語<span>{n_star(vp)} 條</span></summary><ul class="wlist">{"".join(wcard(x) for x in vp if x.get("lib"))}</ul></details>
</article>
<article class="card">
  <div class="card-h"><h2>句型</h2><span class="count">高分版用到的 {len(e['patterns'])} 個</span></div>
  <ol class="pats">{pats}</ol>
</article>
<article class="card">
  <div class="card-h"><h2>可以直接套用的句子</h2></div>
  <p class="fine">底線處換成自己的內容。</p>
  <ul class="tpl">{tpl}</ul>
</article>"""

    # ── 中譯英（學測第二大題：每題 4 分，原則上每個錯誤扣 0.5 分，同樣的錯誤只扣一次）──
    tr_html = ""
    if tr:
        def tvers(t):
            return "<p>" + EN_MARK.sub(lambda m: f'<mark class="{VCLS.get(m.group(1), "")}" title="{VLAB.get(m.group(1), "")}">{m.group(2)}</mark>', esc(t)) + "</p>"

        def tver(name, text, note):
            lab = "綠底＝改過的地方" if name == "照你的改" else "另一個滿分寫法"
            nt = f'<p class="vnote">{inline(note)}</p>' if note else ""
            return f"""<div class="tr-ver"><div class="vhead"><h3>{name}</h3><span>{word_count(text)} 字</span></div>
      <div class="sheet tr-v"><div class="label"><span>{lab}</span></div>{tvers(text)}</div>{nt}</div>"""

        tr_total, tr_max, item_html = 0, 0, []
        for it in tr["items"]:
            mx = it["max"] if it.get("max") is not None else tr["max"]
            tr_total += it["score"]
            tr_max += mx
            sq = {"n": 0}

            def tmark(m, it=it, sq=sq):
                sq["n"] += 1
                s_ = sq["n"]
                lv = (it["errors"][s_ - 1] if s_ - 1 < len(it["errors"]) else {}).get("level") or "small"
                return f'<mark class="err lv-{lv}" data-k="t{it["no"]}e{s_}" tabindex="0" role="button" aria-label="第 {it["no"]} 題第 {s_} 處，{LV.get(lv, "")}">{m.group(1)}</mark>&#8288;<sup class="en-n lv-{lv}" data-k="t{it["no"]}e{s_}" aria-hidden="true">{s_}</sup>'

            sent = E_MARK.sub(tmark, esc(it["original"]))
            cards = "".join(f"""<li class="ecard lv-{x['level']}" data-k="t{it['no']}e{j + 1}" data-lv="{x['level']}">
        <div class="eh"><span class="no">{j + 1}</span><span class="lv">{LV[x['level']]}</span><span class="ty">{esc(x['type'])}</span>{f'<span class="ded">−{tr_fmt(x["deduct"])}</span>' if x['deduct'] > 0 else ""}</div>
        <p class="wn was"><span class="lab">原句</span>{en(x['was'])}</p>
        <p class="wn now"><span class="lab">{"可以" if x['level'] == "good" else "改成"}</span>{en(x['now'])}</p>
        <p class="why">{inline(x['why'])}</p>
      </li>""" for j, x in enumerate(it["errors"]))
            v = it.get("vocab") or {"words": [], "phrases": []}
            vv = [x for x in v.get("words", []) + v.get("phrases", []) if x.get("lib")]
            note = f'<p class="vnote">{inline(it["note"])}</p>' if it.get("note") else ""
            body_cards = f'<ol class="ecards tr-ecards">{cards}</ol>' if cards else '<p class="fine">這一題沒有要扣的地方。</p>'
            vers = tver("照你的改", it["fixed"], "") + "".join(tver("另一種寫法", a["text"], a["note"]) for a in it["alts"])
            vbox = f'<details class="box"><summary>這一題用到的精選字、片語<span>{len(vv)} 個</span></summary><ul class="wlist">{"".join(wcard(x) for x in vv)}</ul></details>' if vv else ""
            item_html.append(f"""<article class="card tr-item" id="tr-{it['no']}">
  <div class="card-h"><h2>第 {it['no']} 題</h2><span class="count tr-score"><b>{tr_fmt(it['score'])}</b>／{num(mx)}</span></div>
  <p class="tr-zh">{esc(it['zh'])}</p>
  <div class="sheet tr-s"><div class="label"><span>你寫的</span><span>點波浪線看說明</span></div><p>{sent}</p></div>
  {note}
  {body_cards}
  <div class="tr-vers">{vers}</div>
  {vbox}
</article>""")
        tr_html = f"""<article class="card score tr-head">
  <div>
    <div class="big"><span class="lab">中譯英</span><span class="gold-num">{tr_fmt(tr_total)}</span><span class="of">／{num(tr_max)}</span></div>
    <p class="verdict">{inline(tr['verdict'])}</p>
    <p class="fine">{esc(TR_BASIS)}</p>
  </div>
</article>
{chr(10).join(item_html)}"""

    # ── 題目與依據 ──
    b = e["basis"]
    if tr and not any(x.get("u") == TR_SRC["u"] for x in b.get("sources") or []):
        b = dict(b, sources=list(b.get("sources") or []) + [TR_SRC])
    tr_basis = f"<p>{esc(TR_BASIS)}</p>\n  " if tr else ""
    rub = b.get("appRubric") or []
    rub_li = "".join("<li>" + esc(r) + "</li>" for r in rub)
    rubric = f'<h3>這一題的評分重點</h3><ul class="dots">{rub_li}</ul>' if rub else ""

    def crit(c):
        mx = (num(c["max"]) + " 分") if c.get("max") else ""
        h = f'<h3>{esc(c["k"])}<small>{esc(mx)}</small></h3>'
        d = f'<p>{inline(c["d"])}</p>' if c.get("d") else ""
        lv = ""
        if c.get("levels"):
            trs = "".join('<tr><td class="pts">' + esc(x["pts"]) + "</td><td>" + inline(x["d"]) + "</td></tr>" for x in c["levels"])
            lv = f'<div class="tablewrap"><table><tbody>{trs}</tbody></table></div>'
        return h + d + lv

    basis = f"""<article class="card read">
  <h2>題目</h2>
  <p>{esc(e['origin'])}</p>
  <p class="material-en">{esc(e['prompt']['stem'])}</p>
  {rubric}
</article>
<article class="card">
  <h2>{esc(b.get('criteriaTitle') or '大考中心怎麼給分')}</h2>
  <p>{inline(b.get('criteriaIntro') or '')}</p>
  {tr_basis}{"".join(crit(c) for c in b.get("criteria") or [])}
  {extra_html(b)}
</article>
<article class="card">
  <h2>出處</h2>
  <ul class="srcs">{sources_html(b)}</ul>
</article>"""

    # ── 估分 ──
    sc = e["score"]
    parts = "".join(f"""<li>
    <div class="ph"><span class="k">{esc(p['k'])}</span><span class="v">{num(p['v'])}<small>／5</small></span></div>
    <div class="bar" role="img" aria-label="{esc(p['k'])} {num(p['v'])} 分，滿分 5 分"><span style="width:{num(p['v'] * 20)}%"></span></div>
    <dl><div><dt>做得好</dt><dd>{inline(p['good'])}</dd></div><div><dt>扣在哪</dt><dd>{inline(p['lose'])}</dd></div><div><dt>怎麼拿滿</dt><dd>{inline(p['full'])}</dd></div></dl>
  </li>""" for p in sc["parts"])

    tabs = ([("trans", "中譯英")] if tr else []) + [("review", "批改"), ("versions", "改寫"), ("words", "字與句型"), ("basis", "題目與依據")]
    names = dict(tabs)

    def panel(pid, html, first=False):
        return f'<section class="panel{" basis" if pid == "basis" else ""}" id="panel-{pid}" data-name="{names[pid]}" role="tabpanel"{"" if first else " hidden"}>{html}</section>'

    seg = "".join(f'<button type="button" role="tab" data-tab="{tid}" aria-selected="{"true" if i == 0 else "false"}" aria-controls="panel-{tid}">{label}</button>' for i, (tid, label) in enumerate(tabs))
    body = f"""<div class="wrap wide en-page">
<div class="essay-head">
  <p class="src">{esc(e['kind'])}　{esc(e['origin'])}</p>
  <h1>{esc(e['title'])}</h1>
</div>
<article class="card score en-score">
  <div>
    <div class="big"><span class="lab">估分</span><span class="gold-num">{num(sc['value'])}</span><span class="of">／{num(sc['max'])}</span></div>
    <p class="verdict">{inline(sc['verdict'])}</p>
    <p class="after">範圍約 {esc(sc['range'])}。輕修版約 {esc(sc['light'])}，高分版約 {esc(sc['high'])}。</p>
  </div>
  <ul class="parts4">{parts}</ul>
</article>
<div class="seg-wrap"><div class="seg" role="tablist" aria-label="這篇作文的內容">
  {seg}
</div></div>
{panel("trans", tr_html, True) + chr(10) if tr else ""}{panel("review", review, not tr)}
{panel("versions", versions)}
{panel("words", words)}
{panel("basis", basis)}
<footer class="foot">{esc(e['reviewed'])}改。估分照大考中心英文作文的四項（內容、組織、文法句構、字彙拼字，各 5 分）抓的，不是正式成績，實際閱卷會差 1～2 分。<br>精選字、片語的中文與例句取自 allinone 學測精選（CC BY-NC 4.0）。用 gsat-essay-grader 批改。</footer>
{promo('en')}
</div>"""
    tr_desc = "中譯英、" if tr else ""
    return shell(f"{e['title']}｜作文批改", f"{e['origin']}「{e['title']}」的{tr_desc}估分、逐句挑錯，和輕修版、高分版兩篇改寫。", body, en=True, wide=True, tr=bool(tr))


# ───────────────────────── 主程式 ─────────────────────────

def main(args):
    global problems
    if args:
        files = [Path(a) if Path(a).is_absolute() else ROOT / a for a in args]
    else:
        c = ROOT / "content"
        files = sorted(c.glob("*.json")) if c.exists() else []
    if not files:
        sys.exit(f"{ROOT}/content/ 裡沒有批改檔。先跑 python3 tools/ws.py init 建工作資料夾。")
    OUT.mkdir(parents=True, exist_ok=True)
    built, failed = [], []
    for f in files:
        e = json.loads(f.read_text(encoding="utf-8"))
        problems = []
        html = english_page(e) if e["subject"] == "en" else essay_page(e)
        if problems:
            failed.append((f.name, problems))
            continue
        out = OUT / (f.stem + ".html")
        out.write_text(html, encoding="utf-8")
        built.append(out)
    print("字數（含標點）")
    for r in report:
        print("  " + "｜".join(num(x) if isinstance(x, (int, float)) else str(x) for x in r))
    if built:
        print("\n建好：\n  " + "\n  ".join(str(b) for b in built))
    if failed:
        print("\n有問題要修（這幾篇沒有產生網頁）：", file=sys.stderr)
        for name, ps in failed:
            print(f"  {name}\n    " + "\n    ".join(ps), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
