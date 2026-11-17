// 建置：content/*.json（一篇作文一份）→ site/NN-slug.html（一篇一個完整的 HTML 檔，樣式與程式都包在裡面，
// 可以直接打開、傳給學生，或在 Claude Code 裡發佈成 Claude 網頁）。
//
//   node tools/build.mjs                       建工作資料夾裡全部的 content/*.json
//   node tools/build.mjs content/03-x.json     只建這幾篇
//
// 國文會檢查：眉批數量對得上標記、原文跟 drafts/ 一樣、改寫版字數不超過「原文＋20」也不超過題目上限。
// 英文會檢查：原文跟 drafts/ 一樣、挑錯數量對得上標記、改寫版字數不超過原文的 1.15 倍、精選字片語都補過資料（vocab.py fill）。
// 有問題會列出來、不產生那一篇。
import { readdirSync, readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname, resolve, basename, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { englishPage } from "./english.mjs";

const PLUGIN = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const MAX_OVER = 20; // 國文改寫版最多比學生原文多幾個字
const TOL = 1.15; // 題目的字數限制，上下約 15% 都算合理，不在頁面上評論

// 工作資料夾：ESSAY_HOME → 往上找 .essay-grader → 現在的資料夾（跟 tools/ws.py 一樣）
function home() {
  if (process.env.ESSAY_HOME) return resolve(process.env.ESSAY_HOME);
  let d = process.cwd();
  for (;;) {
    if (existsSync(join(d, ".essay-grader"))) return d;
    const up = dirname(d);
    if (up === d) return process.cwd();
    d = up;
  }
}
const ROOT = home();
const OUT = join(ROOT, "site");
const CSS = readFileSync(join(PLUGIN, "assets", "style.css"), "utf8");
const JS = readFileSync(join(PLUGIN, "assets", "app.js"), "utf8");

// ── 小工具 ──
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
const MARK = /\{\{([xslgpc]):([^}]+)\}\}/g;
const plain = (s) => s.replace(MARK, "$2");
const count = (s) => [...plain(s).replace(/\s/g, "")].length; // 含標點、不含空白
const TAG = { x: "字詞", s: "句子", l: "文意", g: "留著", p: "思想", c: "改動" };
const draft = (name) => readFileSync(join(ROOT, "drafts", name), "utf8");

let problems = [];
const report = [];

function partCount(part) { return part.paras.reduce((n, p) => n + count(p.text), 0); }

// 一個「部分」（問題一、問題二…）的段落＋眉批
function renderPart(part, ctx) {
  const n = partCount(part);
  let wc = `${n} 字`;
  let over = false;
  if (part.limit) { wc += `（題目限 ${part.limit} 字）`; over = n > part.limit * TOL; }
  if (ctx.baseCount != null) wc = `原文 ${ctx.baseCount} 字 → 這一版 ${n} 字` + (part.limit ? `（題目限 ${part.limit}）` : "");
  const head = part.label
    ? `<div class="part-h"><h2>${esc(part.label)}</h2><span class="wc${over ? " over" : ""}">${wc}${over ? "，多了不少" : ""}</span></div>`
    : `<div class="part-h"><h2>${esc(ctx.fallbackLabel || "全文")}</h2><span class="wc">${wc}</span></div>`;
  const title = part.title ? `<p class="essay-title">${esc(part.title)}</p>` : "";
  const paras = part.paras.map((p) => {
    const notes = p.notes || [];
    let i = 0;
    const keys = [];
    const tx = esc(p.text).replace(MARK, (_, t, body) => {
      const note = notes[i++];
      ctx.seq += 1;
      const key = `${ctx.prefix}${ctx.seq}`;
      keys.push({ key, n: ctx.seq, t });
      if (note && note.t && note.t !== t) problems.push(`${ctx.where}：第 ${ctx.seq} 點標記是 ${t}、眉批寫 ${note.t}`);
      return `<mark class="${t}" data-k="${key}" tabindex="0" role="button" aria-label="眉批 ${ctx.seq}">${body}</mark>&#8288;<sup class="mk ${t}" data-k="${key}" aria-hidden="true">${ctx.seq}</sup>`;
    });
    if (i !== notes.length) problems.push(`${ctx.where}：「${plain(p.text).slice(0, 12)}…」這段有 ${i} 個標記、${notes.length} 則眉批`);
    const list = notes.length
      ? `<ol class="notes">` + notes.map((nt, j) => {
          const k = keys[j] || { key: "", n: "?", t: nt.t || "l" };
          return `<li class="note ${k.t}" data-k="${k.key}"><span class="n">${k.n}</span><div><span class="tag">${esc(nt.tag || TAG[k.t])}</span>${inline(nt.body)}${nt.fix ? `<span class="fix">${inline(nt.fix)}</span>` : ""}</div></li>`;
        }).join("") + `</ol>`
      : `<div class="notes"></div>`;
    return `<div class="para${p.flat ? " flat" : ""}"><p class="tx">${tx}</p>${list}</div>`;
  }).join("");
  return `<section class="part">${head}${title}${paras}</section>`;
}

const ICON = {
  sun: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/></svg>`,
  moon: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.2 8.2 0 1 0 10.2 10.2z"/></svg>`,
};

// 一頁完整的 HTML：樣式、程式都包在裡面，字型從 Google Fonts 載入（沒網路就用系統字型）
function shell({ title, desc, body, en, wide }) {
  return `<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<meta name="color-scheme" content="light dark">
<meta name="generator" content="gsat-essay-grader">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Noto+Serif+TC:wght@400;600;700${en ? "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400" : ""}&display=swap" rel="stylesheet">
<style>
${CSS}
</style>
<script>try{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.setAttribute("data-theme",t)}catch(e){}</script>
</head>
<body>
<div class="sky" aria-hidden="true"></div>
<div class="waves" aria-hidden="true"><svg viewBox="0 0 1200 300" preserveAspectRatio="none"><path class="a" d="M0 150c120-50 240-60 380-20s250 60 400 10 280-70 420-10v170H0z"/><path class="b" d="M0 215c160-40 300-30 430 0s260 40 390 0 250-40 380 0v85H0z"/></svg></div>
<header class="wrap${wide ? " wide" : ""} top">
  <span class="wordmark">作文批改</span>
  <button class="pill icon theme" type="button" aria-label="切換白天或晚上的配色"><span class="sun">${ICON.sun}</span><span class="moon">${ICON.moon}</span></button>
</header>
<main>
${body}
</main>
<script>
${JS}
</script>
</body>
</html>
`;
}

function essayPage(e) {
  const tabs = [["review", "批改"], ...e.versions.map((v) => [v.id, v.tab]), ["basis", "題目與依據"]];

  // 批改
  const ctx = { seq: 0, prefix: "o", where: `${e.title}・批改` };
  const origCounts = e.original.parts.map(partCount);
  e.original.parts.forEach((p, i) => report.push([e.title, `原文 ${p.label || ""}`, origCounts[i], p.limit || "—", "—"]));
  let rewrite = "";
  if (e.overall.rewrite) {
    const rw = e.overall.rewrite;
    const n = count(rw.text);
    const cap = Math.min((rw.limit || Infinity) * TOL, origCounts[rw.base] + MAX_OVER);
    report.push([e.title, rw.title, n, rw.limit || "—", `原文 ${origCounts[rw.base]}，最多 ${cap}`]);
    if (n > cap) problems.push(`${e.title}・${rw.title}：${n} 字，超過上限 ${cap} 字`);
    rewrite = `<h3>${esc(rw.title)}</h3><p class="rw">${esc(rw.text)}</p><p class="rw-n">${n} 字（含標點）。${inline(rw.note)}</p>`;
  }
  if (e.rawFile) {
    const squash = (t) => t.replace(/\s/g, "");
    let raw = draft(e.rawFile).replace(/^\((一|二)\)$/gm, "");
    if (e.original.parts.some((p) => p.title)) raw = raw.replace(/^.+\n/, "");
    const mine = e.original.parts.map((p) => p.paras.map((x) => plain(x.text)).join("")).join("");
    if (squash(raw) !== squash(mine)) problems.push(`${e.title}：批改頁的原文跟 drafts/${e.rawFile} 不一樣，學生的字被動到了`);
  }
  const review = `
<div class="legend" aria-label="標記的意思">
  <span class="x"><i></i>字詞</span><span class="s"><i></i>句子</span><span class="l"><i></i>文意與結構</span><span class="g"><i></i>留著的</span>
</div>
<article class="card read essay-cols">
  ${e.original.parts.map((p) => renderPart(p, ctx)).join("")}
</article>
<article class="card overall">
  <h2>總評</h2>
  <h3>留著的</h3>
  <ul class="good">${e.overall.good.map((g) => `<li>${inline(g)}</li>`).join("")}</ul>
  <h3>先動這三處</h3>
  <ol class="fixes">${e.overall.fixes.map((f) => `<li><div><b>${inline(f.t)}</b>${inline(f.d)}</div></li>`).join("")}</ol>
  ${e.overall.closing ? `<h3>${esc(e.overall.closingTitle || "下一步")}</h3><p>${inline(e.overall.closing)}</p>` : ""}
  ${rewrite}
</article>`;

  // 東方版、西方版
  const versions = e.versions.map((v) => {
    const vctx = { seq: 0, prefix: v.id[0], where: `${e.title}・${v.tab}` };
    const parts = v.parts.map((p, i) => {
      const src = v.basePart != null ? v.basePart + i : i;
      const baseCount = origCounts[src];
      const n = partCount(p);
      const cap = Math.min((p.limit || Infinity) * TOL, baseCount + MAX_OVER);
      report.push([e.title, `${v.tab} ${p.label || ""}`, n, p.limit || "—", `原文 ${baseCount}，最多 ${cap}`]);
      if (n > cap) problems.push(`${e.title}・${v.tab}${p.label || ""}：${n} 字，超過上限 ${cap} 字`);
      return renderPart(p, { ...vctx, baseCount, get seq() { return vctx.seq; }, set seq(x) { vctx.seq = x; } });
    }).join("");
    return `<section class="panel" id="panel-${v.id}" data-name="${esc(v.tab)}" role="tabpanel" hidden>
<article class="card thinker">
  <div class="who"><span class="tile read">${esc(v.tile)}</span><div><h2>${esc(v.name)}</h2><p>${esc(v.sub)}</p></div></div>
  <p class="idea">${inline(v.idea)}</p>
  <div>${v.quotes.map((q) => `<blockquote class="quote"><q>${esc(q.q)}</q>${q.orig ? `<span class="orig" lang="${q.lang || "en"}">${esc(q.orig)}</span>` : ""}<cite>${esc(q.cite)}</cite>${q.plain ? `<span class="plain">${inline(q.plain)}</span>` : ""}</blockquote>`).join("")}</div>
  <p class="bridge">${inline(v.bridge)}</p>
  ${v.warn ? `<p class="warn"><b>引的時候　</b>${inline(v.warn)}</p>` : ""}
</article>
<div class="legend" style="padding-top:16px" aria-label="標記的意思">
  <span class="p"><i></i>引了思想的地方</span><span class="c"><i></i>改過的地方</span>
</div>
<article class="card read essay-cols">${parts}</article>
</section>`;
  }).join("\n");

  // 題目與依據
  const b = e.basis;
  const basis = `<section class="panel basis" id="panel-basis" data-name="題目與依據" role="tabpanel" hidden>
<article class="card read">
  <h2>題目</h2>
  <p>${esc(b.origin)}</p>
  <div class="material">${(b.material || []).map((m) => m.type === "lab" ? `<p class="lab">${esc(m.text)}</p>` : m.type === "from" ? `<p class="from">${esc(m.text)}</p>` : `<p${m.type === "poem" ? ` class="poem"` : ""}>${esc(m.text)}</p>`).join("")}</div>
  <ul class="tasks">${(b.tasks || []).map((t) => `<li>${esc(t.q)}<span class="pt">${esc(t.pt)}</span>${t.note ? `<span class="pt">${inline(t.note)}</span>` : ""}</li>`).join("")}</ul>
</article>
<article class="card">
  <h2>${esc(b.criteriaTitle)}</h2>
  <p>${inline(b.criteriaIntro)}</p>
  ${(b.tables || []).map((t) => `<h3>${esc(t.h)}</h3><div class="tablewrap"><table><tbody>${t.rows.map((r) => `<tr${r.here ? ` class="here"` : ""}><th>${esc(r.g)}</th><td class="pts">${esc(r.pts)}</td><td>${inline(r.d)}${r.here ? `　<b>← ${r.here === true ? "這篇在這裡" : esc(r.here)}</b>` : ""}</td></tr>`).join("")}</tbody></table></div>`).join("")}
  ${(b.extra || []).map((x) => `<h3>${esc(x.h)}</h3><ul class="dots">${x.items.map((i) => `<li>${inline(i)}</li>`).join("")}</ul>`).join("")}
</article>
<article class="card">
  <h2>出處</h2>
  <ul class="srcs">${(b.sources || []).map((s) => `<li>${s.u ? `<a href="${esc(s.u)}" target="_blank" rel="noopener noreferrer">${esc(s.t)}</a>` : esc(s.t)}${s.note ? `<small>${esc(s.note)}</small>` : ""}</li>`).join("")}</ul>
</article>
</section>`;

  const sc = e.score;
  const body = `<div class="wrap wide">
<div class="essay-head">
  <p class="src">${esc(e.kind)}　${esc(e.origin)}</p>
  <h1>${esc(e.title)}${e.edition ? `<small class="ed">${esc(e.edition)}</small>` : ""}</h1>
</div>
<article class="card score">
  <div>
    <div class="big"><span class="lab">${esc(sc.label)}</span><span class="gold-num">${esc(sc.value)}</span><span class="of">／${sc.max}</span></div>
    <p class="verdict">${inline(sc.verdict)}</p>
  </div>
  <div>
    <ul class="parts">${sc.parts.map((p) => `<li><span class="k">${esc(p.k)}</span><span class="v">${esc(p.v)}${p.max ? `<small>／${p.max}</small>` : ""}</span><span class="why">${inline(p.why)}</span></li>`).join("")}</ul>
    <p class="fine">${inline(sc.fine)}</p>
  </div>
</article>
<div class="seg-wrap"><div class="seg" role="tablist" aria-label="這篇作文的內容">
  ${tabs.map(([id, label], i) => `<button type="button" role="tab" data-tab="${id}" aria-selected="${i === 0}" aria-controls="panel-${id}">${esc(label)}</button>`).join("")}
</div></div>
<section class="panel" id="panel-review" data-name="批改" role="tabpanel">${review}</section>
${versions}
${basis}
<footer class="foot">${esc(e.reviewed)}改。分數是照大考中心的評分表抓的，不是正式成績。<br>用 gsat-essay-grader 批改。</footer>
</div>`;

  return shell({
    title: `${e.title}｜作文批改`,
    desc: `${e.origin}「${e.title}」的眉批、估分，和${e.versions.map((v) => v.tab).join("、")}兩篇改寫。`,
    body, wide: true,
  });
}

// ── 讀內容、寫出 ──
const args = process.argv.slice(2);
const files = args.length
  ? args.map((a) => (isAbsolute(a) ? a : resolve(ROOT, a)))
  : existsSync(join(ROOT, "content")) ? readdirSync(join(ROOT, "content")).filter((f) => f.endsWith(".json")).sort().map((f) => join(ROOT, "content", f)) : [];
if (!files.length) {
  console.error(`${ROOT}/content/ 裡沒有批改檔。先跑 python3 tools/ws.py init 建工作資料夾。`);
  process.exit(1);
}
mkdirSync(OUT, { recursive: true });
const built = [];
const failed = [];
const ctxEn = { esc, inline, shell, draft, get problems() { return problems; }, report };
for (const f of files) {
  const e = JSON.parse(readFileSync(f, "utf8"));
  problems = [];
  const html = e.subject === "en" ? englishPage(e, ctxEn) : essayPage(e);
  if (problems.length) { failed.push([basename(f), problems]); continue; }
  const out = join(OUT, basename(f).replace(/\.json$/, ".html"));
  writeFileSync(out, html);
  built.push(out);
}

console.log("字數（含標點）");
for (const r of report) console.log("  " + r.join("｜"));
if (built.length) console.log("\n建好：\n  " + built.join("\n  "));
if (failed.length) {
  console.error("\n有問題要修（這幾篇沒有產生網頁）：");
  for (const [f, ps] of failed) console.error(`  ${f}\n    ` + ps.join("\n    "));
  process.exit(1);
}
