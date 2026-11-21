#!/usr/bin/env python3
"""把子代理交的分件拼成一篇批改檔 content/NN-slug.json（格式見 skills/grade/SKILL.md）。

    python3 tools/merge.py work/<slug>     → content/<order>-<slug>.json（英文會接著跑 vocab.py fill）

work/<slug>/ 裡的分件：
  英文：intake.json（主線）、research.json（收集）、diagnosis.json（診斷）、light.json、high.json（改寫）
  國文：intake.json（主線）、basis.json（主線依收集整理）、diagnosis.json（診斷）、east.json、west.json（改寫）
英文有中譯英時：intake.json 的 translation（rawFile、max、items[{no, zh}]）、diagnosis.json 的 translation（verdict、items）、
light.json 的 translation（每題 fixed、alts、vocab）會一起拼成批改檔的 translation（見 merge_translation）。
review*.json（盲審）不拼進去，只是給改寫的子代理修稿用。
英文 research.json 有 page 欄位時，網頁的「題目與依據」只放 page 的精簡版，完整的留在 bank/。
"""
import json
import re
import subprocess
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


def load(d, name, need=True):
    p = d / name
    if not p.exists():
        if need:
            sys.exit(f"少了 {p}")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def page_basis(rs):
    """page: {"intro": 取代 criteriaIntro, "extra": 取代 extra, "sources": [要列的 sources 第幾筆，從 0 起]}"""
    b = {k: v for k, v in rs.items() if k not in ("page", "checked")}
    pg = rs.get("page")
    if pg:
        if pg.get("intro"):
            b["criteriaIntro"] = pg["intro"]
        if "extra" in pg:
            b["extra"] = pg["extra"]
        if "sources" in pg:
            src = rs.get("sources") or []
            bad = [i for i in pg["sources"] if not (isinstance(i, int) and 0 <= i < len(src))]
            if bad:
                sys.exit(f"research.json 的 page.sources 有對不上的編號：{bad}（sources 只有 {len(src)} 筆）")
            b["sources"] = [src[i] for i in pg["sources"]]
    return b


def merge_translation(it, dg, lt):
    """中譯英：intake（題目中文）＋diagnosis（原句標記、扣分）＋light（三種寫法、精選字）→ 批改檔的 translation。
    student 是學生原句（drafts/<rawFile> 的那一行，一個字都不動）；拿掉 {{e:}} 後要跟它一樣。"""
    ti, td, tl = it["translation"], dg.get("translation"), lt.get("translation")
    if not td or not tl:
        sys.exit("intake.json 有 translation，diagnosis.json 或 light.json 卻沒有 translation")
    n = len(ti["items"])
    if len(td["items"]) != n or len(tl) != n:
        sys.exit(f"中譯英題數對不上：intake {n}、diagnosis {len(td['items'])}、light {len(tl)}")
    raw_path = home() / "drafts" / ti["rawFile"]
    if not raw_path.exists():
        sys.exit(f"少了 {raw_path}（學生的翻譯，一行一題）")
    raw = [x.strip() for x in raw_path.read_text(encoding="utf-8").splitlines()]
    while raw and not raw[-1]:
        raw.pop()
    if len(raw) != n:
        sys.exit(f"drafts/{ti['rawFile']} 有 {len(raw)} 行，intake 有 {n} 題")
    mx = ti.get("max", 4)
    items = []
    for q, a, b, line in zip(ti["items"], td["items"], tl, raw):
        stripped = re.sub(r"\{\{e:([^}]+)\}\}", r"\1", a["original"]).strip()
        if stripped != line:
            sys.exit(f"中譯英第 {q['no']} 題：diagnosis 的 original 拿掉 {{{{e:}}}} 後跟原稿不一樣\n  原稿：{line}\n  診斷：{stripped}")
        items.append({"no": q["no"], "zh": q["zh"], "student": line, "score": a["score"], "max": mx,
                      "original": a["original"], "errors": a["errors"], "note": a.get("note", ""),
                      "fixed": b["fixed"], "alts": b["alts"],
                      "vocab": b.get("vocab") or {"words": [], "phrases": []}})
    return {"verdict": td["verdict"], "max": mx, "rawFile": ti["rawFile"], "items": items}


def merge_en(d, it):
    rs, dg, lt, hi = load(d, "research.json"), load(d, "diagnosis.json"), load(d, "light.json"), load(d, "high.json")
    n = len(it["suggest"]["items"])
    for name, x in (("diagnosis", dg["suggestUse"]), ("light", lt["suggestUse"]), ("high", hi["suggestUse"])):
        if len(x) != n:
            sys.exit(f"{name}.json 的 suggestUse 有 {len(x)} 個，建議用字有 {n} 個")
    sc = dg["score"]
    doc = {
        "schema": 1, "subject": "en", "tier": it.get("tier", "usual"),
        **{k: it[k] for k in ("slug", "order", "tile", "kind", "title", "origin", "reviewed", "rawFile") if k in it},
        "list": {"sub": (it.get("list") or {}).get("sub", ""), "est": str(sc["value"]), "estNote": "估分／20"},
        "prompt": it["prompt"], "suggest": it["suggest"],
        "score": {"value": sc["value"], "range": sc["range"], "max": 20, "light": lt["est"], "high": hi["est"],
                  "verdict": sc["verdict"], "parts": sc["parts"]},
        "original": dg["original"], "errors": dg["errors"],
        "suggestUse": [{"used": a["used"], "orig": a["orig"], "light": b, "high": c}
                       for a, b, c in zip(dg["suggestUse"], lt["suggestUse"], hi["suggestUse"])],
        "versionsIntro": f"左邊輕修版：{lt['summary']}右邊高分版：{hi['summary']}",
        "light": {"paras": lt["paras"], "note": lt["note"]},
        "high": {"paras": hi["paras"], "note": hi["note"]},
        "vocab": hi["vocab"], "patterns": hi["patterns"], "templates": hi["templates"],
        "basis": {"appRubric": it.get("rubric") or it.get("appRubric") or [], **page_basis(rs)},
    }
    if it.get("translation"):
        doc["translation"] = merge_translation(it, dg, lt)
    return doc


def merge_zh(d, it):
    dg, east, west, basis = load(d, "diagnosis.json"), load(d, "east.json"), load(d, "west.json"), load(d, "basis.json")
    return {
        "schema": 1, "subject": "zh", "tier": it.get("tier", "usual"),
        **{k: it[k] for k in ("slug", "order", "kind", "tile", "title", "origin", "reviewed", "rawFile") if k in it},
        **({"edition": it["edition"]} if it.get("edition") else {}),
        "list": dg["list"], "score": dg["score"], "original": dg["original"], "overall": dg["overall"],
        "versions": [east, west], "basis": basis,
    }


def main(arg):
    d = Path(arg)
    if not d.is_absolute():
        d = home() / d
    it = load(d, "intake.json")
    doc = merge_en(d, it) if it["subject"] == "en" else merge_zh(d, it)
    out = home() / "content" / f"{int(it['order']):02d}-{it['slug']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"拼好 → {out}")
    if it["subject"] == "en":
        r = subprocess.run([sys.executable, str(HERE / "vocab.py"), "fill", str(out)])
        sys.exit(r.returncode)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
