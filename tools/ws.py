#!/usr/bin/env python3
"""工作資料夾：你的作文、批改中間檔、成品都放在這裡（不在外掛裡面）。

    python3 tools/ws.py init [資料夾]     建一個工作資料夾（預設是現在的資料夾）
    python3 tools/ws.py where            現在用的是哪個工作資料夾
    python3 tools/ws.py next             下一篇的編號（order）

找工作資料夾的順序：環境變數 ESSAY_HOME → 從現在的資料夾往上找有 .essay-grader 的那一層 → 現在的資料夾。

工作資料夾裡：
  drafts/    學生原稿的打字檔（一個字都不動，build 會逐字比對）
  work/      每篇的中間檔（intake、diagnosis、兩版改寫、盲審意見）
  content/   成品：一篇一份 NN-slug.json
  bank/      每一題找過的資料（同一題不重新收集）
  site/      建好的網頁（一篇一個 HTML 檔）
"""
import json
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):      # Windows 的中文命令列是 Big5，印 ✗ 這類字會當掉；一律用 UTF-8
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PLUGIN = Path(__file__).resolve().parent.parent
DIRS = ("drafts", "work", "content", "bank", "site")
MARKER = ".essay-grader"


def home():
    env = os.environ.get("ESSAY_HOME")
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / MARKER).exists():
            return p
    return cwd


def init(where=None):
    h = Path(where).expanduser().resolve() if where else Path.cwd().resolve()
    h.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (h / d).mkdir(exist_ok=True)
    m = h / MARKER
    if not m.exists():
        m.write_text(json.dumps({"tool": "gsat-essay-grader", "version": 1}) + "\n", encoding="utf-8")
    gi = h / ".gitignore"
    if not gi.exists():
        gi.write_text("# 學生的作文只留在本機\ndrafts/\nwork/\ncontent/\nsite/\n*.jpg\n*.jpeg\n*.png\n*.heic\n", encoding="utf-8")
    print(f"工作資料夾：{h}")


def next_order():
    c = home() / "content"
    nums = [int(p.name.split("-", 1)[0]) for p in c.glob("*.json") if p.name.split("-", 1)[0].isdigit()] if c.exists() else []
    return max(nums, default=0) + 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
    elif a[0] == "init":
        init(a[1] if len(a) > 1 else None)
    elif a[0] == "where":
        print(home())
    elif a[0] == "next":
        print(next_order())
    else:
        print(__doc__)
        sys.exit(2)
