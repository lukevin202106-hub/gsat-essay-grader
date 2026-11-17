#!/usr/bin/env python3
"""打包三個下載檔到 dist/（發 GitHub Release 用）：

    python3 scripts/package.py

  gsat-essay-grader-skill.zip     Claude 網頁版／App：「自訂 → 技能」上傳這個檔
  gsat-essay-grader-mac.zip       Mac：解壓縮後雙擊「安裝作文批改器.command」
  gsat-essay-grader-windows.zip   Windows：解壓縮後雙擊 install.bat
"""
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
REPO = "https://github.com/lukevin202106-hub/gsat-essay-grader"
PAGE = "https://lukevin202106-hub.github.io/gsat-essay-grader/"


def add(z, arc, data, mode=0o644):
    info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100000 | mode) << 16
    z.writestr(info, data)


def add_file(z, arc, path, mode=0o644):
    add(z, arc, Path(path).read_bytes(), mode)


def role_for_web(text):
    """子代理的規則 → 網頁版的角色說明：拿掉開頭的設定、路徑說法換成「技能資料夾」"""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = text.replace("外掛資料夾裡 `skills/grade/SKILL.md`", "技能資料夾的 `SKILL.md`")
    text = text.replace("外掛資料夾", "技能資料夾")
    text = re.sub(r"「\d [^」]+」與「語氣」兩節", "「步驟」「格式」與「語氣」三節", text)
    head = "> 網頁版：沒有主線也沒有子代理，這份規則由你自己照順序做；文中的「主線給你」「主線指定」就是你自己決定、自己準備。\n\n"
    return head + text.lstrip()


def skill_zip():
    out = DIST / "gsat-essay-grader-skill.zip"
    base = "gsat-essay-grader/"
    with zipfile.ZipFile(out, "w") as z:
        add_file(z, base + "SKILL.md", ROOT / "web-skill" / "SKILL.md")
        for p in sorted((ROOT / "agents").glob("*.md")):
            add(z, base + "roles/" + p.name, role_for_web(p.read_text(encoding="utf-8")).encode("utf-8"))
        for p in sorted((ROOT / "tools").glob("*.py")):
            add_file(z, base + "tools/" + p.name, p)
        for p in sorted((ROOT / "assets").glob("*")):
            add_file(z, base + "assets/" + p.name, p)
        add_file(z, base + "data/gsat-vocab.json", ROOT / "data" / "gsat-vocab.json")
        add_file(z, base + "data/LICENSE.md", ROOT / "data" / "LICENSE.md")
        for p in sorted((ROOT / "examples" / "content").glob("*.json")):
            add_file(z, base + "examples/content/" + p.name, p)
        for p in sorted((ROOT / "examples" / "site").glob("*.html")):
            add_file(z, base + "examples/site/" + p.name, p)      # 網頁長相的標準
        add_file(z, base + "LICENSE", ROOT / "LICENSE")
    return out


MAC_README = f"""作文批改器（Mac）{VERSION}

1. 雙擊「安裝作文批改器.command」。

   如果跳出「無法打開」「Apple 無法驗證」的視窗：
   - 按「完成」關掉視窗
   - 打開「系統設定」→「隱私權與安全性」，拉到最下面，
     看到「已阻擋使用『安裝作文批改器.command』」，按「強制打開」（或「仍要打開」），輸入密碼
   - 舊一點的 macOS：在檔案上按右鍵 →「打開」→ 再按「打開」

   不想處理這個視窗的話，也可以打開「終端機」（在「應用程式」→「工具程式」裡），貼上這一行按 Enter：
   curl -fsSL {PAGE}install/install.sh | bash

2. 照視窗裡的說明做。第一次可能會請你安裝 Apple 的「指令列工具」（裡面有 Python），
   裝好之後再雙擊一次安裝程式。

3. 裝好以後，「文件」裡會多一個「作文批改」資料夾。雙擊裡面的「開始批改」，
   第一次會請你用瀏覽器登入 Claude（要 Pro 以上的付費方案），然後貼上題目和作文就好。

說明：{PAGE}
原始碼與問題回報：{REPO}
"""

WIN_README = f"""作文批改器（Windows）{VERSION}

1. 先在這個 zip 檔上按右鍵 →「解壓縮全部」，打開解壓縮出來的資料夾。
   （直接在 zip 裡面雙擊不會動。）

2. 雙擊 install.bat。
   如果跳出藍色的「Windows 已保護您的電腦」：按「其他資訊」→「仍要執行」。

3. 照視窗裡的說明做。沒有 Python 的話會自動安裝 Python 3.12。

4. 裝好以後，「文件」裡會多一個「作文批改」資料夾。雙擊裡面的「開始批改」，
   第一次會請你用瀏覽器登入 Claude（要 Pro 以上的付費方案），然後貼上題目和作文就好。

說明：{PAGE}
原始碼與問題回報：{REPO}
"""


def mac_zip():
    out = DIST / "gsat-essay-grader-mac.zip"
    base = "作文批改器-Mac/"
    with zipfile.ZipFile(out, "w") as z:
        add_file(z, base + "安裝作文批改器.command", ROOT / "install" / "install.sh", 0o755)
        add(z, base + "讀我.txt", MAC_README.encode("utf-8"))
    return out


def windows_zip():
    out = DIST / "gsat-essay-grader-windows.zip"
    base = "gsat-essay-grader-windows/"    # Windows 內建的解壓縮對中文檔名不一定處理得好，檔名一律英文
    with zipfile.ZipFile(out, "w") as z:
        add_file(z, base + "install.bat", ROOT / "install" / "install.bat")
        ps1 = (ROOT / "install" / "install.ps1").read_bytes()
        if not ps1.startswith(b"\xef\xbb\xbf"):
            ps1 = b"\xef\xbb\xbf" + ps1
        add(z, base + "install.ps1", ps1)
        add(z, base + "README.txt", b"\xef\xbb\xbf" + WIN_README.replace("\n", "\r\n").encode("utf-8"))
    return out


if __name__ == "__main__":
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for f in (skill_zip(), mac_zip(), windows_zip()):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
