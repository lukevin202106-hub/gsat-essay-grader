#!/usr/bin/env python3
"""題目資料（bank/）：每一題找過的資料與查找結果。同一題再有學生寫，就不用重新上網收集，省時間也省額度。

    python3 tools/bank.py list                     列出存過的題目
    python3 tools/bank.py find 關鍵字               找題目（標題、題目文字）
    python3 tools/bank.py check work/<slug>        這一題要不要收集：reuse（給資料夾）或 collect（給要寫到哪）
    python3 tools/bank.py save work/<slug>         批完以後存：題目、依據、用過的思想、查找紀錄，更新 index.json

資料夾：bank/<zh|en>/<題目鍵>_<標題>/。英文的大考中心評分原則全部題目共用，放 bank/en/_shared/rubric.json。
題目鍵：intake.json 有 bankKey 就用它（例如 gsat-114-zh-1），沒有就用題目文字的雜湊（x-xxxxxxxx）。
等級：資料是哪一級收集的。這次要「最好」、存的只有「省錢／測試」收的，就重新收集（舊筆記當起點）。

國文資料夾裡：grading.md（評分與解析）、sources.md（原典）、east.md（東方思想資源）、west.md（西方哲學資源）、
basis.json（網頁「題目與依據」，拿掉「這篇在這裡」）、thinkers.json（用過的思想家與引文）、prompt.json、log.md。
"""
import datetime
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):      # Windows 的中文命令列是 Big5，印 ✗ 這類字會當掉；一律用 UTF-8
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ws import home  # noqa: E402

ROOT = home()
BANK = ROOT / "bank"
INDEX = BANK / "index.json"
RANK = {"test": 0, "usual": 1, "best": 2}
TODAY = datetime.date.today().isoformat()


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def dump(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def index():
    return load(INDEX, {"version": 1, "items": {}})


def work_dir(w):
    p = Path(w)
    return p if p.is_absolute() else ROOT / p


def key_of(it):
    if it.get("bankKey"):
        return it["bankKey"]
    stem = (it.get("prompt") or {}).get("stem") or it["title"]
    return "x-" + hashlib.sha1(re.sub(r"\s", "", stem).encode()).hexdigest()[:8]


def folder_of(it, key):
    safe = re.sub(r"[\\/:*?\"<>|\s]", "", it["title"])[:20]
    return BANK / it["subject"] / f"{key}_{safe}"


def rel(p):
    return str(Path(p).relative_to(ROOT))


def cmd_list():
    for k, x in sorted(index()["items"].items()):
        print(f"{x['subject']} {k}｜{x['title']}｜資料等級 {x['researchTier']}（{x['collectedAt']}）｜用過 {len(x['usedBy'])} 次｜{x['folder']}")


def cmd_find(kw):
    hit = False
    for k, x in index()["items"].items():
        stem = (load(ROOT / x["folder"] / "prompt.json", {}) or {}).get("stem", "")
        if kw in k or kw in x["title"] or kw in stem:
            print(json.dumps({"key": k, **x}, ensure_ascii=False))
            hit = True
    if not hit:
        print(f"bank/ 裡沒有「{kw}」")


def cmd_check(work):
    it = load(work_dir(work) / "intake.json")
    key, tier = key_of(it), it.get("tier", "usual")
    x = index()["items"].get(key)
    folder = rel(folder_of(it, key))
    if it["subject"] == "en":
        shared = BANK / "en" / "_shared" / "rubric.json"
        meta = load(BANK / "en" / "_shared" / "rubric.meta.json", {})
        ok = shared.exists() and RANK.get(meta.get("tier"), 0) >= RANK[tier]
        print(json.dumps({"key": key, "decision": "reuse" if ok else "collect", "rubric": rel(shared), "rubricTier": meta.get("tier"),
                          "how": "把 rubric.json 複製成 work/<slug>/research.json，不用開收集子代理" if ok else
                                 "開收集子代理寫 work/<slug>/research.json，save 時會存進共用"}, ensure_ascii=False, indent=1))
        return
    if x and RANK.get(x["researchTier"], 0) >= RANK[tier]:
        print(json.dumps({"key": key, "decision": "reuse", "folder": x["folder"], "researchTier": x["researchTier"],
                          "files": sorted(p.name for p in (ROOT / x["folder"]).iterdir()),
                          "how": "不開收集子代理。診斷與改寫直接讀這個資料夾的筆記；basis.json 複製成 work/<slug>/basis.json 再補「這篇在這裡」；thinkers.json 看之前用過誰"},
                         ensure_ascii=False, indent=1))
    else:
        print(json.dumps({"key": key, "decision": "collect", "folder": folder, "old": x["folder"] if x else None,
                          "how": "收集子代理把筆記寫到 folder（grading.md、sources.md、east.md、west.md）"
                                 + ("；舊資料等級較低，給收集子代理當起點、核對後補強" if x else "")}, ensure_ascii=False, indent=1))


def strip_here(basis):
    b = json.loads(json.dumps(basis))
    for t in b.get("tables", []):
        for r in t.get("rows", []):
            r.pop("here", None)
    return b


def cmd_save(work):
    work = work_dir(work)
    it = load(work / "intake.json")
    key, tier = key_of(it), it.get("tier", "usual")
    idx = index()
    x = idx["items"].get(key)
    folder = ROOT / x["folder"] if x else folder_of(it, key)
    folder.mkdir(parents=True, exist_ok=True)
    collected = it.get("collected", True)
    log = []
    prompt = {"key": key, "subject": it["subject"], "title": it["title"], "origin": it.get("origin", ""),
              "stem": (it.get("prompt") or {}).get("stem", "")}
    if it["subject"] == "en":
        prompt.update({"suggest": it.get("suggest"), "rubric": it.get("rubric"), "minWords": (it.get("prompt") or {}).get("minWords")})
    dump(folder / "prompt.json", prompt)

    if it["subject"] == "en":
        rs = work / "research.json"
        shared = BANK / "en" / "_shared"
        meta = load(shared / "rubric.meta.json", {})
        if collected and rs.exists() and RANK[tier] >= RANK.get(meta.get("tier"), -1):
            shared.mkdir(parents=True, exist_ok=True)
            shutil.copy(rs, shared / "rubric.json")
            dump(shared / "rubric.meta.json", {"tier": tier, "collectedAt": TODAY, "from": it["slug"]})
            log.append(f"英文共用評分原則存好（{tier}）")
    else:
        basis = load(work / "basis.json")
        if basis:
            dump(folder / "basis.json", strip_here(basis))
        used = load(folder / "thinkers.json", [])
        for v in ("east", "west"):
            d = load(work / f"{v}.json")
            if d:
                used.append({"date": TODAY, "slug": it["slug"], "tier": tier, "tab": d.get("tab"), "name": d.get("name"), "sub": d.get("sub"),
                             "quotes": [{"q": q.get("q"), "orig": q.get("orig"), "cite": q.get("cite")} for q in d.get("quotes", [])]})
        dump(folder / "thinkers.json", used)
        notes = sorted(p.name for p in folder.glob("*.md") if p.name != "log.md")
        log.append("筆記：" + "、".join(notes) if notes else "（資料夾裡沒有筆記）")

    rec = folder / "log.md"
    head = "" if rec.exists() else f"# {it['title']}：查找紀錄\n\n每次批這一題都記一筆。各筆記檔最後都有「沒查到」的清單。\n\n"
    line = f"- {TODAY}｜{it['slug']}｜{tier}｜{'重新收集' if collected else '沿用，沒有收集'}｜{'；'.join(log)}\n"
    rec.write_text((rec.read_text(encoding="utf-8") if rec.exists() else head) + line, encoding="utf-8")

    old = x["researchTier"] if x else None
    new = (old or tier) if (not collected or (old and RANK.get(old, 0) > RANK[tier])) else tier
    idx["items"][key] = {"subject": it["subject"], "title": it["title"], "folder": rel(folder), "researchTier": new,
                         "collectedAt": TODAY if collected else (x or {}).get("collectedAt", TODAY),
                         "usedBy": sorted(set((x or {}).get("usedBy", []) + [it["slug"]])), "lastUsed": TODAY}
    dump(INDEX, idx)
    print(f"存好 {key} → {rel(folder)}（{'；'.join(log)}）")


if __name__ == "__main__":
    a = sys.argv[1:]
    cmds = {"list": lambda: cmd_list(), "find": lambda: cmd_find(a[1]), "check": lambda: cmd_check(a[1]), "save": lambda: cmd_save(a[1])}
    if not a or a[0] not in cmds or (a[0] != "list" and len(a) < 2):
        print(__doc__)
        sys.exit(2)
    cmds[a[0]]()
