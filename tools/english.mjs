// 英文作文批改頁（照 2026-11-15〈團圓飯作文詳解〉的順序）：
// 估分 → 批改（題目、原文作答紙＋波浪線、逐句挑錯）→ 改寫（輕修版、高分版、建議的 N 個怎麼用）→ 字與句型（精選字、片語、句型、套用句）→ 題目與依據
// 內容格式見 skills/grade/SKILL.md「英文」。精選字、片語的中文與例句由 tools/vocab.py fill 從學測精選字表補進 vocab.*.lib。

const MARK = /\{\{([a-z]):([^}]+)\}\}/g;
const plain = (s) => s.replace(MARK, "$2");
export const wordCount = (s) => plain(s).split(/\s+/).filter((w) => /[A-Za-z0-9]/.test(w)).length; // 跟 App 的 word_count 一樣
const MAX_RATIO = 1.15; // 改寫版最多是原文的幾倍（團圓飯 228 → 256、260）
const LV = { big: "大錯", small: "小改", good: "加分" };
const VCLS = { s: "sg", c: "ch", w: "wd", p: "ph", g: "pt" };
const VLAB = { s: "建議用到", c: "改過的地方", w: "學測精選字", p: "學測精選片語", g: "句型" };
const PART_KEYS = ["內容", "組織", "文法句構", "字彙拼字"];

export function englishPage(e, { esc, inline, shell, draft, problems, report }) {
  const where = e.title;
  const need = (cond, msg) => { if (!cond) problems.push(`${where}：${msg}`); };
  const paraCount = (v) => v.paras.reduce((n, p) => n + wordCount(p), 0);
  const en = (s) => `<span class="en-text" lang="en">${esc(s)}</span>`;

  // ── 檢查 ──
  const origN = paraCount(e.original);
  const cap = Math.round(origN * MAX_RATIO);
  const min = e.prompt.minWords || 0;
  report.push([where, "原文", origN, `至少 ${min}`, "—"]);
  for (const [k, lab] of [["light", "輕修版"], ["high", "高分版"]]) {
    const n = paraCount(e[k]);
    report.push([where, lab, n, `至少 ${min}`, `原文 ${origN}，最多 ${cap}`]);
    need(n <= cap, `${lab} ${n} 字，超過原文的 ${MAX_RATIO} 倍（${cap}）`);
    need(n >= min, `${lab} ${n} 字，比題目要求的 ${min} 字少`);
  }
  if (e.rawFile) {
    const squash = (t) => t.replace(/\s/g, "");
    const raw = draft(e.rawFile);
    need(squash(raw) === squash(e.original.paras.map(plain).join("")), `批改頁的原文跟 drafts/${e.rawFile} 不一樣，學生的字被動到了`);
  }
  const nMarks = e.original.paras.reduce((n, p) => n + [...p.matchAll(MARK)].filter((m) => m[1] === "e").length, 0);
  need(nMarks === e.errors.length, `原文有 ${nMarks} 個 {{e:}} 標記，挑錯有 ${e.errors.length} 則`);
  e.errors.forEach((x, i) => need(LV[x.level], `第 ${i + 1} 則挑錯的 level 要是 big／small／good`));
  need(e.suggestUse.length === e.suggest.items.length, `建議用字 ${e.suggest.items.length} 個，對照表 ${e.suggestUse.length} 列`);
  need(e.score.parts.map((p) => p.k).join() === PART_KEYS.join(), `估分四項要照順序：${PART_KEYS.join("、")}`);
  need(e.score.parts.reduce((n, p) => n + p.v, 0) === e.score.value, `四項加起來不等於總分 ${e.score.value}`);
  const forms = { w: new Set(e.vocab.words.map((x) => x.form.toLowerCase())), p: new Set(e.vocab.phrases.map((x) => x.form.toLowerCase())) };
  for (const x of [...e.vocab.words, ...e.vocab.phrases]) need(x.lib, `${x.id} 還沒補字表的資料，先跑 python3 tools/vocab.py fill content/…json`);
  for (const k of ["light", "high"]) for (const p of e[k].paras) for (const [, t, body] of p.matchAll(MARK)) {
    if (t === "w" || t === "p") need(forms[t].has(body.toLowerCase()), `${k} 的 {{${t}:${body}}} 沒列在 vocab`);
    need(VCLS[t], `${k} 有不認得的標記 {{${t}:…}}`);
  }

  // ── 原文作答紙 ──
  let seq = 0;
  const origHtml = e.original.paras.map((p) => `<p>${esc(p).replace(/\{\{e:([^}]+)\}\}/g, (_, body) => {
    seq += 1;
    const lv = (e.errors[seq - 1] || {}).level || "small";
    return `<mark class="err lv-${lv}" data-k="e${seq}" tabindex="0" role="button" aria-label="第 ${seq} 處，${LV[lv] || ""}">${body}</mark>&#8288;<sup class="en-n lv-${lv}" data-k="e${seq}" aria-hidden="true">${seq}</sup>`;
  })}</p>`).join("");

  const tally = Object.fromEntries(Object.keys(LV).map((k) => [k, e.errors.filter((x) => x.level === k).length]));
  const errHtml = e.errors.map((x, i) => `<li class="ecard lv-${x.level}" data-k="e${i + 1}" data-lv="${x.level}">
    <div class="eh"><span class="no">${i + 1}</span><span class="lv">${LV[x.level]}</span><span class="ty">${esc(x.type)}</span></div>
    <p class="wn was"><span class="lab">原句</span>${en(x.was)}</p>
    <p class="wn now"><span class="lab">${x.level === "good" ? "可以" : "改成"}</span>${en(x.now)}</p>
    <p class="why">${inline(x.why)}</p>
  </li>`).join("");

  const used = e.suggestUse.filter((u) => u.used).length;
  const sug = e.suggest;
  const promptCard = `<article class="card prompt-card">
  <h2>題目</h2>
  <p class="q">${esc(e.prompt.stem)}</p>
  <p class="chips-lab">建議用到${sug.by === "teacher" ? "（題目沒有列，老師從學測精選挑的；寫的時候沒看到，不算分）" : ""}</p>
  <ul class="chips">${sug.items.map((s) => `<li lang="en">${esc(s.text)}</li>`).join("")}</ul>
  <div class="stats3">
    <div><b>${origN}</b><span>你的字數（至少 ${min}）</span></div>
    <div><b>${used}／${sug.items.length}</b><span>用到建議的</span></div>
    <div><b>${e.errors.length}</b><span>處要看：大錯 ${tally.big}、小改 ${tally.small}、加分 ${tally.good}</span></div>
  </div>
</article>`;

  const review = `${promptCard}
<article class="card read">
  <div class="card-h"><h2>你的原文</h2><span class="count">${origN} 字</span></div>
  <div class="sheet orig"><div class="label"><span>照手寫稿打字，錯字照原樣</span><span>點波浪線看說明</span></div>${origHtml}</div>
</article>
<article class="card">
  <div class="card-h"><h2>逐句挑錯</h2><span class="count">${e.errors.length} 處</span></div>
  <div class="filters" role="group" aria-label="篩選">
    <button type="button" data-f="all" aria-pressed="true">全部</button>
    <button type="button" data-f="big" aria-pressed="false">大錯 ${tally.big}</button>
    <button type="button" data-f="small" aria-pressed="false">小改 ${tally.small}</button>
    <button type="button" data-f="good" aria-pressed="false">加分 ${tally.good}</button>
  </div>
  <ol class="ecards">${errHtml}</ol>
</article>`;

  // ── 兩版改寫 ──
  const vpara = (p) => `<p>${esc(p).replace(MARK, (_, t, body) => `<mark class="${VCLS[t] || ""}" title="${VLAB[t] || ""}">${body}</mark>`)}</p>`;
  const vcol = (k, name, labelNote) => `<div class="vcol">
    <div class="vhead"><h3>${name}</h3><span>${paraCount(e[k])} 字・約 ${esc(e.score[k])} 分</span></div>
    <div class="sheet"><div class="label"><span>${labelNote}</span></div>${e[k].paras.map(vpara).join("")}</div>
    <p class="vnote">${inline(e[k].note)}</p>
  </div>`;
  const toggles = `<div class="toggles" role="group" aria-label="標記開關">${["s", "c", "w", "p", "g"].map((t) =>
    `<label><input type="checkbox" id="t-${VCLS[t]}" checked><mark class="${VCLS[t]}">${VLAB[t]}</mark></label>`).join("")}</div>`;
  const sugTable = `<article class="card">
  <h2 class="h2">建議的 ${sug.items.length} 個怎麼用</h2>
  <div class="tablewrap"><table class="tbl">
    <thead><tr><th scope="col">建議</th><th scope="col">你的原文</th><th scope="col">輕修版</th><th scope="col">高分版</th></tr></thead>
    <tbody>${sug.items.map((s, i) => { const u = e.suggestUse[i] || {}; return `<tr><th scope="row">${en(s.text)}<small>${esc(s.zh || "")}</small></th>
      <td class="${u.used ? "" : "miss"}">${inline(u.orig || (u.used ? "用到了" : "沒用到"))}</td><td class="mix">${esc(u.light || "")}</td><td class="mix">${esc(u.high || "")}</td></tr>`; }).join("")}</tbody>
  </table></div>
</article>`;
  const versions = `<article class="card read">
  <p class="lede">${inline(e.versionsIntro || "")}</p>
  ${toggles}
  <div class="versions">${vcol("light", "輕修版", "綠底＝改過的地方，金底＝建議用到")}${vcol("high", "高分版", "底線＝精選字，紫底＝精選片語，紫字＝句型")}</div>
</article>
${sugTable}`;

  // ── 字與句型 ──
  const wcard = (x) => { const c = x.lib; const head = c.word || c.phrase;
    return `<li><div class="wtop"><span class="wword" lang="en">${esc(head)}</span>${c.pos ? `<span class="pos">${esc(c.pos)}</span>` : ""}${c.gsat ? `<span class="star" title="學測精選">★${c.level ? ` L${c.level}` : ""}</span>` : `<span class="nostar">${esc(x.note || "不在精選")}</span>`}</div>
    <div class="wzh">${esc(c.zh)}</div>${c.ex ? `<div class="wex" lang="en">${esc(c.ex)}</div><div class="wexzh">${esc(c.exZh)}</div>` : ""}</li>`; };
  const nStar = (xs) => xs.filter((x) => x.lib && x.lib.gsat).length;
  const words = `<article class="card read">
  <div class="card-h"><h2>用到的學測精選字、片語</h2></div>
  <p class="fine">★＝學測精選，L 是大考中心詞彙級數。中文與例句取自 allinone App 的學測精選。</p>
  <details class="box" open><summary>精選字<span>${nStar(e.vocab.words)} 個</span></summary><ul class="wlist">${e.vocab.words.filter((x) => x.lib).map(wcard).join("")}</ul></details>
  <details class="box" open><summary>精選片語<span>${nStar(e.vocab.phrases)} 條</span></summary><ul class="wlist">${e.vocab.phrases.filter((x) => x.lib).map(wcard).join("")}</ul></details>
</article>
<article class="card">
  <div class="card-h"><h2>句型</h2><span class="count">高分版用到的 ${e.patterns.length} 個</span></div>
  <ol class="pats">${e.patterns.map((p) => `<li><h3>${esc(p.name)}</h3><p class="formula" lang="en">${esc(p.formula)}</p><p class="ex" lang="en">${esc(p.ex)}</p><p class="why">${inline(p.why)}</p></li>`).join("")}</ol>
</article>
<article class="card">
  <div class="card-h"><h2>可以直接套用的句子</h2></div>
  <p class="fine">底線處換成自己的內容。</p>
  <ul class="tpl">${e.templates.map((t) => `<li><p class="tuse">${esc(t.use)}</p><p class="tsent"><span lang="en">${esc(t.sent)}</span><button type="button" class="copy" data-t="${esc(t.sent)}">複製</button></p><p class="tnote">${inline(t.note)}</p></li>`).join("")}</ul>
</article>`;

  // ── 題目與依據 ──
  const b = e.basis;
  const basis = `<article class="card read">
  <h2>題目</h2>
  <p>${esc(e.origin)}</p>
  <p class="material-en">${esc(e.prompt.stem)}</p>
  ${b.appRubric && b.appRubric.length ? `<h3>這一題的評分重點</h3><ul class="dots">${b.appRubric.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
</article>
<article class="card">
  <h2>${esc(b.criteriaTitle || "大考中心怎麼給分")}</h2>
  <p>${inline(b.criteriaIntro || "")}</p>
  ${(b.criteria || []).map((c) => `<h3>${esc(c.k)}<small>${esc(c.max ? `${c.max} 分` : "")}</small></h3>${c.d ? `<p>${inline(c.d)}</p>` : ""}${c.levels && c.levels.length ? `<div class="tablewrap"><table><tbody>${c.levels.map((l) => `<tr><td class="pts">${esc(l.pts)}</td><td>${inline(l.d)}</td></tr>`).join("")}</tbody></table></div>` : ""}`).join("")}
  ${(b.extra || []).map((x) => `<h3>${esc(x.h)}</h3><ul class="dots">${x.items.map((i) => `<li>${inline(i)}</li>`).join("")}</ul>`).join("")}
</article>
<article class="card">
  <h2>出處</h2>
  <ul class="srcs">${(b.sources || []).map((s) => `<li>${s.u ? `<a href="${esc(s.u)}" target="_blank" rel="noopener noreferrer">${esc(s.t)}</a>` : esc(s.t)}${s.note ? `<small>${esc(s.note)}</small>` : ""}</li>`).join("")}</ul>
</article>`;

  // ── 估分 ──
  const sc = e.score;
  const parts = sc.parts.map((p) => `<li>
    <div class="ph"><span class="k">${esc(p.k)}</span><span class="v">${p.v}<small>／5</small></span></div>
    <div class="bar" role="img" aria-label="${esc(p.k)} ${p.v} 分，滿分 5 分"><span style="width:${p.v * 20}%"></span></div>
    <dl><div><dt>做得好</dt><dd>${inline(p.good)}</dd></div><div><dt>扣在哪</dt><dd>${inline(p.lose)}</dd></div><div><dt>怎麼拿滿</dt><dd>${inline(p.full)}</dd></div></dl>
  </li>`).join("");

  const tabs = [["review", "批改"], ["versions", "改寫"], ["words", "字與句型"], ["basis", "題目與依據"]];
  const panel = (id, html, first) => `<section class="panel${id === "basis" ? " basis" : ""}" id="panel-${id}" data-name="${tabs.find((t) => t[0] === id)[1]}" role="tabpanel"${first ? "" : " hidden"}>${html}</section>`;
  const body = `<div class="wrap wide en-page">
<div class="essay-head">
  <p class="src">${esc(e.kind)}　${esc(e.origin)}</p>
  <h1>${esc(e.title)}</h1>
</div>
<article class="card score en-score">
  <div>
    <div class="big"><span class="lab">估分</span><span class="gold-num">${sc.value}</span><span class="of">／${sc.max}</span></div>
    <p class="verdict">${inline(sc.verdict)}</p>
    <p class="after">範圍約 ${esc(sc.range)}。輕修版約 ${esc(sc.light)}，高分版約 ${esc(sc.high)}。</p>
  </div>
  <ul class="parts4">${parts}</ul>
</article>
<div class="seg-wrap"><div class="seg" role="tablist" aria-label="這篇作文的內容">
  ${tabs.map(([id, label], i) => `<button type="button" role="tab" data-tab="${id}" aria-selected="${i === 0}" aria-controls="panel-${id}">${label}</button>`).join("")}
</div></div>
${panel("review", review, true)}
${panel("versions", versions)}
${panel("words", words)}
${panel("basis", basis)}
<footer class="foot">${esc(e.reviewed)}改。估分照大考中心英文作文的四項（內容、組織、文法句構、字彙拼字，各 5 分）抓的，不是正式成績，實際閱卷會差 1～2 分。<br>精選字、片語的中文與例句取自 allinone 學測精選（CC BY-NC 4.0）。用 gsat-essay-grader 批改。</footer>
</div>`;

  return shell({
    title: `${e.title}｜作文批改`,
    desc: `${e.origin}「${e.title}」的估分、逐句挑錯，和輕修版、高分版兩篇改寫。`,
    body, en: true, wide: true,
  });
}
