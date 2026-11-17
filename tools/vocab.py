#!/usr/bin/env python3
"""查學測精選字、片語句型（data/gsat-vocab.json，來自 allinone App，CC BY-NC 4.0）。
批改流程的子代理都用這支查，不要自己猜是不是精選字。

    python3 tools/vocab.py word reunion offended      是不是學測精選、id、級別、中文
    python3 tools/vocab.py scan -f 檔案 | "英文"      字數、精選字、字族、精選片語候選（-f 可以給 light.json 這類分件；--json 給程式用）
    python3 tools/vocab.py card core-2/reunion …      字或片語的中文、例句
    python3 tools/vocab.py patterns [關鍵字]          精選片語與句型（★＝複雜易錯）
    python3 tools/vocab.py hard [關鍵字]              L4、L5 的精選字
    python3 tools/vocab.py fill content/NN-x.json     把批改檔裡標的精選字、片語補上中文與例句，並檢查標記

想換成自己的字表：照 data/gsat-vocab.json 的格式做一份，設環境變數 ESSAY_VOCAB 指到那個檔。
"""
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

DATA = Path(os.environ.get("ESSAY_VOCAB") or Path(__file__).resolve().parent.parent / "data" / "gsat-vocab.json")
VOWELS = "aeiou"
TOKEN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?(?:-[A-Za-z]+(?:['’][A-Za-z]+)?)*")
MARK = re.compile(r"\{\{([a-z]):([^}]+)\}\}")


# ───────────────────────── 字庫 ─────────────────────────

@lru_cache(None)
def db():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    d["byId"] = {w["id"]: w for w in d["words"]}
    d["phById"] = {p["id"]: p for p in d["phrases"]}
    return d


def irregular_of(w):
    """原形 → 不規則變化形（go → went、gone；undergo → underwent）"""
    irr = db()["irregular"]
    out = {k for k, v in irr.items() if v == w}
    out |= {w[:-len(v)] + k for k, v in irr.items() if len(w) - len(v) >= 3 and w.endswith(v) and v != w}
    return out


@lru_cache(None)
def forms(w):
    """一個字可能出現的字形（小寫）：規則變化＋不規則變化。寧可多給，不要漏；
    多給到別的字（sum → summer）由字表每個字的 drop 拿掉，規則給不到的由 add 補上（匯出時跟 allinone 逐字對過）。"""
    w = w.lower()
    out = {w, w + "s", w + "es", w + "ed", w + "d", w + "ing", w + "er", w + "ers", w + "est", w + "ly"}
    if w.endswith("e"):
        b = w[:-1]
        out |= {b + "ing", b + "ed", b + "er", b + "ers", b + "est", b + "y" if w.endswith("le") else b + "ly"}
        if w.endswith("ie"):
            out.add(w[:-2] + "ying")
    if w.endswith("y") and len(w) > 2 and w[-2] not in VOWELS:
        b = w[:-1]
        out |= {b + "ies", b + "ied", b + "ier", b + "iers", b + "iest", b + "ily"}
    if re.search(r"(?:^|[^aeiou]|qu)[aeiou][bdgklmnprtvz]$", w) and not w.endswith(("w", "x", "y")):
        out |= {w + w[-1] + s for s in ("ed", "ing", "er", "ers", "est")}       # stop → stopped、equip → equipped
    if w.endswith("c"):
        out |= {w + "ked", w + "king", w + "ally"}                              # panic → panicked、basic → basically
    if w.endswith("f"):
        out.add(w[:-1] + "ves")
    if w.endswith("fe"):
        out.add(w[:-2] + "ves")
    if w.endswith("is"):
        out.add(w[:-2] + "es")                                                  # analysis → analyses
    return frozenset(out | irregular_of(w))


@lru_cache(None)
def index():
    """字形 → 精選字 id（本字）；字形 → 精選字 id（字族，例如 development → develop）"""
    own, fam, head = {}, {}, {}
    for w in db()["words"]:
        base = w["word"].lower()
        head.setdefault(base, set()).add(w["id"])
        for f in (forms(base) - set(w.get("drop", ()))) | set(w.get("add", ())):
            own.setdefault(f, set()).add(w["id"])
        for m in w.get("family", []):
            for f in forms(m):
                fam.setdefault(f, set()).add(w["id"])
    return own, fam, head


def tokens(text):
    """(原字, 小寫)；縮寫 don't → do、I'm → i"""
    out = []
    for m in TOKEN.finditer(text.replace("’", "'")):
        tok = m.group(0)
        tl = tok.lower()
        if tl.endswith("n't"):
            tl = {"ca": "can", "wo": "will", "sha": "shall", "ai": "be"}.get(tl[:-3], tl[:-3])
        elif "'" in tl:
            tl = tl.split("'")[0]
        out.append((tok, tl))
    return out


def word_count(s):
    """跟一般文書軟體一樣：空白分開、有英數字的才算一個字（don't、fifteen-minute、60% 各算 1 個）"""
    return sum(1 for w in s.split() if re.search(r"[A-Za-z0-9]", w))


# ───────────────────────── 片語比對 ─────────────────────────

CONTRACTIONS = [(r"\bwon't\b", "will not"), (r"\bcan't\b", "can not"), (r"\bcannot\b", "can not"), (r"\bshan't\b", "shall not"),
                (r"n't\b", " not"), (r"'m\b", " am"), (r"'re\b", " are"), (r"'ve\b", " have"), (r"'ll\b", " will"), (r"'d\b", " would"),
                (r"\blet's\b", "let us"), (r"\b(it|that|there|here|what|who|he|she|where|how)'s\b", r"\1 is")]
SLOTS = {"sb", "sth", "one's", "ones", "oneself", "v-ing", "ving", "v", "adj", "n", "s", "p", "a", "b", "o", "+",
         "superlative", "comparative", "that"}
AUX = {"be": {"is", "are", "was", "were", "am", "been", "being", "'s", "'re"}, "is": {"was", "'s"},
       "have": {"has", "had", "having"}, "cannot": {"can't", "could not", "couldn't", "can not"},
       "can't": {"cannot", "could not", "couldn't", "can not"}, "can": {"could"}, "will": {"would"}, "do": {"does", "did"}}


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    for a, b in CONTRACTIONS:
        s = re.sub(a, b, s)
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return " ".join(s.split())


def _skip(w):
    return not w or w.startswith("-") or w in SLOTS or bool(re.fullmatch(r"adj-?er|adj-?est|n-?s|pl|n", w))


@lru_cache(None)
def _rx(formula):
    """片語的寫法 → regex。每個字接受各種字形；sb./sth.、V-ing 這類代號可有可無；a/b 是同一格的幾種說法；
    字與字之間可以隔幾個字（受詞），「…」分開的兩段之間可以隔比較多字"""
    parts = []
    for seg in formula.split("…"):
        seg = re.sub(r"\s*/\s*", "/", re.sub(r"[.(),]", " ", seg))
        alts = []
        for tok in seg.split():
            opts = [w for w in tok.split("/") if w]
            if not opts or any(_skip(w) for w in opts):
                continue
            fs = set()
            for w in opts:
                fs |= set(forms(w)) | AUX.get(w, set())
            alts.append("(?:" + "|".join(sorted(map(re.escape, fs), key=len, reverse=True)) + ")")
        if alts:
            parts.append(r"(?: [a-z0-9']+){0,6} ".join(alts))
    return re.compile(r"(?:^| )" + r"(?: [a-z0-9']+){0,15} ".join(parts) + r"(?= |$)") if parts else None


def _alts(phrase):
    raw = re.sub(r"\([^)]*\)", " ", phrase.lower().replace("’", "'").replace("...", "…"))
    return re.split(r"\s+/\s+", raw)       # 「 / 」前後有空白：整段的不同寫法


def phrase_used(text, phrase):
    t = norm(text)
    return any((rx := _rx(a)) and rx.search(t) for a in _alts(phrase))


def single_word(ph):
    """只有一個字的「片語」（however、although）當連接詞教，掃描時不算精選片語"""
    raw = re.sub(r"\([^)]*\)", " ", ph["phrase"]).replace("...", " ").replace("…", " ")
    return len(raw.split()) <= 1


def has_form(text, form):
    return re.search(r"(?<![A-Za-z'’-])" + re.escape(form) + r"(?![A-Za-z'’-])", text.replace("’", "'")) is not None


def _base(w):
    """片語書寫成過去式的（it occurred to sb. that）→ 可能的原形"""
    if not w.endswith("ed"):
        return [w]
    c = [w[:-2], w[:-1], w[:-3] + "y" if w.endswith("ied") else None, w[:-3] if len(w) > 4 and w[-3] == w[-4] else None]
    return [x for x in c if x]


def phrase_fits(form, para, ph):
    """form 跟片語對得起來：form 本身、或含 form 的那一句比對得到（主詞 it、be 動詞可以不在 form 裡）"""
    if phrase_used(form, ph["phrase"]):
        return True
    for sent in re.split(r"(?<=[.!?])\s+", para):
        if has_form(sent, form) and phrase_used(sent, ph["phrase"]):
            return True
    bare = re.sub(r"^(?:it|be)\s+", "", ph["phrase"], flags=re.I)
    if phrase_used(form, bare):
        return True
    words = bare.split()
    for i, w in enumerate(words):
        for b in _base(w.lower())[1:]:
            if phrase_used(form, " ".join(words[:i] + [b] + words[i + 1:])):
                return True
    return False


# ───────────────────────── 指令 ─────────────────────────

def word_card(wid):
    w = db()["byId"].get(wid) or {}
    return {"id": wid, "kind": "word", "word": w.get("word", ""), "pos": w.get("pos", ""), "level": w.get("level"),
            "gsat": bool(w), "zh": w.get("zh", ""), "ex": w.get("ex", ""), "exZh": w.get("exZh", "")}


def phrase_card(pid):
    p = db()["phById"].get(pid) or {}
    return {"id": pid, "kind": "phrase", "phrase": p.get("phrase", ""), "gsat": bool(p), "hard": bool(p.get("hard")),
            "zh": p.get("zh", ""), "ex": p.get("ex", ""), "exZh": p.get("exZh", ""), "note": p.get("note", ""), "trap": p.get("trap", "")}


def card(i):
    return word_card(i) if i in db()["byId"] or i.startswith("core-") else phrase_card(i)


def read_arg(args):
    """-f 檔案：純文字照讀；.json（light／high／east／west 分件或批改檔）只取段落、拿掉 {{x:…}} 標記"""
    if args and args[0] == "-f":
        p = Path(args[1])
        t = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            d = json.loads(t)
            d = d.get("original", d)
            paras = d.get("paras") or [x["text"] for part in d.get("parts", []) for x in part.get("paras", [])]
            paras = [x if isinstance(x, str) else x.get("text", "") for x in paras]
            t = "\n\n".join(MARK.sub(r"\2", x) for x in paras)
        return t
    return " ".join(args)


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def cmd_word(ws, as_json=False):
    own, fam, head = index()
    res = []
    for w in ws:
        tl = w.lower()
        o, f = sorted(own.get(tl, ())), sorted(fam.get(tl, ()))
        res.append({"form": w, "gsat": o, "family": [] if o else f})
        if as_json:
            continue
        if o:
            print(f"★ {w}：" + "；".join(f"{c['id']}（{c['word']} {c['pos']} L{c['level']} {c['zh']}）" for c in map(word_card, o)))
        elif f:
            print(f"△ {w}：不是精選本字，是精選字的字族 " + "；".join(f"{c['id']}（{c['word']} {c['zh']}）" for c in map(word_card, f)))
        else:
            print(f"✗ {w}：不是學測精選")
    if as_json:
        out(res)


def cmd_scan(text, as_json=False):
    own, fam, _ = index()
    words, family = {}, {}
    for tok, tl in tokens(text):
        for wid in sorted(own.get(tl, ())):
            words.setdefault(wid, tok)
        for wid in sorted(fam.get(tl, ())):
            if wid not in words:
                family.setdefault(wid, tok)
    family = {k: v for k, v in family.items() if k not in words}
    lv = {w["id"]: w["level"] for w in db()["words"]}
    phrases = [p for p in db()["phrases"] if not single_word(p) and phrase_used(text, p["phrase"])]
    n = word_count(text)
    if as_json:
        return out({"wordCount": n, "words": [{"id": k, "form": v, "level": lv.get(k)} for k, v in words.items()],
                    "family": [{"id": k, "form": v} for k, v in family.items()],
                    "phrases": [{"id": p["id"], "phrase": p["phrase"]} for p in phrases]})
    print(f"{n} 字")
    print(f"精選字 {len(words)}：" + "、".join(f"{v}（{k} L{lv.get(k)}）" for k, v in words.items()))
    if family:
        print("字族（不是精選本字）：" + "、".join(f"{v}（{k}）" for k, v in family.items()))
    print(f"精選片語候選 {len(phrases)}（要自己確認意思對得上）：" + "、".join(f"{p['phrase']}（{p['id']}）" for p in phrases))


def cmd_patterns(kw=None):
    for p in db()["phrases"]:
        line = f"{'★' if p.get('hard') else ' '} {p['id']} | {p['phrase']} | {p['zh']} | 常見錯法：{p.get('trap', '')}"
        if not kw or kw.lower() in line.lower():
            print(line)


def cmd_hard(kw=None):
    rows = sorted((w for w in db()["words"] if (w.get("level") or 0) >= 4), key=lambda w: (-w["level"], w["word"]))
    for w in rows:
        line = f"L{w['level']} {w['word']} {w['pos']} {w['zh']}〔{w['id']}〕"
        if not kw or kw.lower() in line.lower():
            print(line)


def cmd_fill(path):
    """批改檔（英文）：light／high 段落裡的 {{w:字}} 要對得到 vocab.words 的 form、{{p:片語}} 要對得到 vocab.phrases 的 form；
    補上字表的中文、例句、級別，寫回 vocab.*[].lib。"""
    own, fam, _ = index()
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    vw, vp = d["vocab"]["words"], d["vocab"]["phrases"]
    errs = []
    for x in vw:
        c = word_card(x["id"])
        if c["gsat"] or not x.get("lib"):          # 不在字表、已經自己寫過 lib 的（例如課本字）留著
            x["lib"] = c
        if not c["gsat"] and not x.get("note"):
            errs.append(f"vocab.words：{x['id']}（{x['form']}）不在學測精選，要寫 note 說明為什麼列")
    for x in vp:
        c = phrase_card(x["id"])
        if c["gsat"] or not x.get("lib"):
            x["lib"] = c
        if not c["gsat"] and not x.get("note"):
            errs.append(f"vocab.phrases：{x['id']} 不在精選片語，要寫 note 說明為什麼列")
    forms_w = {x["form"].lower(): x for x in vw}
    forms_p = {x["form"].lower(): x for x in vp}
    for ver in ("light", "high"):
        for pi, para in enumerate(d[ver]["paras"]):
            plain = MARK.sub(lambda m: m.group(2), para)
            for t, body in MARK.findall(para):
                if t == "w":
                    x = forms_w.get(body.lower())
                    ids = {i for _, tl in tokens(body) for i in set(own.get(tl, ())) | set(fam.get(tl, ()))}
                    if not x:
                        errs.append(f"{ver} 第 {pi + 1} 段 {{{{w:{body}}}}} 沒列在 vocab.words")
                    elif x["id"] not in ids and not x.get("note"):
                        errs.append(f"{ver} 第 {pi + 1} 段 {{{{w:{body}}}}} 的字形對不上 {x['id']}")
                elif t == "p":
                    x = forms_p.get(body.lower())
                    if not x:
                        errs.append(f"{ver} 第 {pi + 1} 段 {{{{p:{body}}}}} 沒列在 vocab.phrases")
                    elif x["lib"]["gsat"] and not phrase_fits(body, plain, db()["phById"][x["id"]]) and not x.get("note"):
                        errs.append(f"{ver} 第 {pi + 1} 段 {{{{p:{body}}}}} 比對不到片語「{x['lib']['phrase']}」（{x['id']}）")
    high = " ".join(MARK.sub(lambda m: m.group(2), p) for p in d["high"]["paras"])
    marked = {x["id"] for x in vw}
    unmarked = [f"{tok}（{wid}）" for tok, tl in tokens(high) for wid in sorted(own.get(tl, ())) if wid not in marked]
    Path(path).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"補好 {len(vw)} 個字、{len(vp)} 條片語 → {path}")
    if unmarked:
        print("高分版裡還有沒標的精選字（不一定要標，基本字可以不標）：" + "、".join(dict.fromkeys(unmarked)))
    if errs:
        print("要修：\n  " + "\n  ".join(errs))
        sys.exit(1)


def main(a):
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = a[0], a[1:]
    table = {"word": lambda: cmd_word(rest, as_json), "scan": lambda: cmd_scan(read_arg(rest), as_json),
             "card": lambda: out([card(i) for i in rest]), "patterns": lambda: cmd_patterns(rest[0] if rest else None),
             "hard": lambda: cmd_hard(rest[0] if rest else None), "fill": lambda: cmd_fill(rest[0])}
    if cmd not in table:
        print(__doc__)
        sys.exit(2)
    table[cmd]()


if __name__ == "__main__":
    main(sys.argv[1:])
