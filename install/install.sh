#!/bin/bash
# 作文批改器（gsat-essay-grader）安裝程式：Mac
#
# 會做的事：
#   1. 裝 Claude Code（已經有就跳過）
#   2. 確認有 Python 3.9 以上（沒有的話，請你裝 Apple 的「指令列工具」）
#   3. 下載作文批改器，裝成 Claude Code 的外掛
#   4. 在「文件」建一個「作文批改」資料夾，裡面放「開始批改」捷徑
#
# 用法：雙擊「安裝作文批改器.command」，或在終端機貼上
#   curl -fsSL https://lukevin202106-hub.github.io/gsat-essay-grader/install/install.sh | bash
# 再跑一次就是更新。

set -u
ZIP_URL="${GSAT_ESSAY_ZIP:-https://github.com/lukevin202106-hub/gsat-essay-grader/archive/refs/heads/main.zip}"
APP_DIR="$HOME/.gsat-essay-grader"
WORK_DIR="${GSAT_ESSAY_HOME:-$HOME/Documents/作文批改}"
PLUGIN="gsat-essay-grader@gsat-essay-grader"

bold() { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() {
  printf '\n\033[31m%s\033[0m\n' "$1"
  printf '\n可以把這個視窗的文字截圖，到 https://github.com/lukevin202106-hub/gsat-essay-grader/issues 回報。\n'
  printf '按 Enter 關閉…'
  { read -r _ </dev/tty; } 2>/dev/null || true
  exit 1
}

bold "作文批改器安裝程式"
echo "大約需要 1～5 分鐘。過程中可能會跳出視窗請你按「安裝」或登入，照著做就好。"

# ── 1. Claude Code ──
export PATH="$HOME/.local/bin:$PATH"
if command -v claude >/dev/null 2>&1; then
  bold "1/4 Claude Code 已經裝好了"
else
  bold "1/4 安裝 Claude Code（Anthropic 官方安裝程式）…"
  curl -fsSL https://claude.ai/install.sh | bash || fail "Claude Code 安裝失敗。請檢查網路，再試一次。"
  hash -r
  command -v claude >/dev/null 2>&1 || fail "找不到 claude 指令。請關掉這個視窗，重新打開終端機再試一次。"
fi

# ── 2. Python ──
bold "2/4 確認 Python…"
PY=""
for c in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  p=$(command -v "$c" 2>/dev/null) || continue
  if [ "$p" = "/usr/bin/python3" ] && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
    continue      # 系統內建的只是空殼，要先裝「指令列工具」
  fi
  if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$p"
    break
  fi
done
if [ -z "$PY" ]; then
  bold "需要先裝 Apple 的「指令列工具」（裡面有 Python）"
  echo "等一下會跳出一個視窗，請按「安裝」，等它跑完（大約 5～15 分鐘）。"
  echo "裝好之後，再雙擊一次「安裝作文批改器」，或再貼一次剛剛那行指令。"
  /usr/bin/xcode-select --install >/dev/null 2>&1 || true
  printf '\n按 Enter 關閉…'
  { read -r _ </dev/tty; } 2>/dev/null || true
  exit 0
fi
echo "Python：$("$PY" --version 2>&1)"

# ── 3. 下載作文批改器、裝成外掛 ──
bold "3/4 下載作文批改器…"
mkdir -p "$APP_DIR"
TMP=$(mktemp -d)
curl -fsSL "$ZIP_URL" -o "$TMP/grader.zip" || fail "下載失敗。請檢查網路，再試一次。"
/usr/bin/ditto -x -k "$TMP/grader.zip" "$TMP" || fail "解壓縮失敗。"
rm -rf "$APP_DIR/gsat-essay-grader"
mv "$TMP/gsat-essay-grader-main" "$APP_DIR/gsat-essay-grader" || fail "放不進 $APP_DIR。"
rm -rf "$TMP"

if claude plugin marketplace list 2>/dev/null | grep -q "gsat-essay-grader"; then
  claude plugin marketplace update gsat-essay-grader >/dev/null 2>&1 || true
else
  claude plugin marketplace add "$APP_DIR/gsat-essay-grader" || fail "加入外掛市集失敗。"
fi
if claude plugin list 2>/dev/null | grep -q "gsat-essay-grader"; then
  claude plugin update "$PLUGIN" || fail "更新外掛失敗。"
else
  claude plugin install "$PLUGIN" || fail "安裝外掛失敗。"
fi

# ── 4. 工作資料夾 ──
bold "4/4 建立「作文批改」資料夾…"
"$PY" "$APP_DIR/gsat-essay-grader/tools/ws.py" init "$WORK_DIR" >/dev/null || fail "建不了 $WORK_DIR。"
cat > "$WORK_DIR/開始批改.command" <<'EOF'
#!/bin/bash
# 雙擊這個檔：在這個資料夾打開 Claude Code，開始批改作文
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"
exec claude "/gsat-essay-grader:grade"
EOF
chmod +x "$WORK_DIR/開始批改.command"
cat > "$WORK_DIR/讀我.txt" <<'EOF'
作文批改器 怎麼用

1. 雙擊「開始批改」。第一次會請你選配色、用瀏覽器登入 Claude（要 Pro 以上的方案），
   再問你信不信任這個資料夾，選「Yes」。
2. 把題目和學生的作文貼進去（照片可以直接拖進視窗）。
   想要最好的品質，說「用最好的」；只是試試看，說「用測試等級」。
3. 批完會在 site 資料夾產生一個網頁檔，雙擊就能看，也可以直接傳給學生。

學生的作文只存在這個資料夾，不會上傳到別的地方（Claude 批改時會讀到）。
更新：再跑一次安裝程式。說明與問題回報：https://github.com/lukevin202106-hub/gsat-essay-grader
EOF

bold "裝好了"
echo "「文件」裡多了一個「作文批改」資料夾。以後雙擊裡面的「開始批改」就能批改作文。"
[ -n "${GSAT_ESSAY_TEST:-}" ] || open "$WORK_DIR" 2>/dev/null || true
printf '\n要現在開始嗎？第一次會請你登入 Claude。（Y＝開始，其他鍵＝之後再說）'
if { read -r ans </dev/tty; } 2>/dev/null; then
  case "$ans" in
    [Yy]*|"") cd "$WORK_DIR" && exec claude "/gsat-essay-grader:grade" ;;
  esac
fi
