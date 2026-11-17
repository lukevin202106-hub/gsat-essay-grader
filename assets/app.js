// 作文批改網頁的前端：晝夜切換、學測倒數、分段切換、眉批（英文是挑錯卡）與原文互相標示、挑錯篩選、複製套用句。
(function () {
  "use strict";
  var root = document.documentElement;

  // ── 晝夜：預設跟系統，按一下記住選擇 ──
  function saved() { try { return localStorage.getItem("theme"); } catch (e) { return null; } }
  function isDark() {
    var t = root.getAttribute("data-theme");
    if (t) return t === "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  var s = saved();
  if (s === "dark" || s === "light") root.setAttribute("data-theme", s);
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".theme");
    if (!b) return;
    var next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (err) { /* 存不了就只管這一次 */ }
  });

  // ── 學測倒數（臺北時間）──
  var dd = document.querySelector("[data-dday]");
  if (dd) {
    var parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()).split("-");
    var today = Date.UTC(+parts[0], +parts[1] - 1, +parts[2]);
    var t = dd.getAttribute("data-dday").split("-");
    var exam = Date.UTC(+t[0], +t[1] - 1, +t[2]);
    var n = Math.round((exam - today) / 86400000);
    var num = dd.querySelector(".dday");
    if (num) num.textContent = n > 0 ? "D-" + n : n === 0 ? "D-Day" : "D+" + (-n);
    var when = document.querySelector("[data-today]");
    if (when) {
      var wd = "日一二三四五六".charAt(new Date(today).getUTCDay());
      when.innerHTML = "<b>" + (+parts[1]) + "月" + (+parts[2]) + "日</b>星期" + wd;
    }
  }

  // ── 分段切換：批改／東方版／西方版／題目與依據 ──
  var seg = document.querySelector(".seg");
  if (seg) {
    var tabs = [].slice.call(seg.querySelectorAll("button"));
    var show = function (id, push) {
      var hit = false;
      tabs.forEach(function (b) {
        var on = b.getAttribute("data-tab") === id;
        if (on) hit = true;
        b.setAttribute("aria-selected", on ? "true" : "false");
        b.tabIndex = on ? 0 : -1;
        var p = document.getElementById("panel-" + b.getAttribute("data-tab"));
        if (p) p.hidden = !on;
      });
      if (!hit) return show(tabs[0].getAttribute("data-tab"), false);
      if (push) {
        try { history.replaceState(null, "", "#" + id); } catch (e) { /* 預覽環境不給改網址就算了 */ }
        var top = document.querySelector(".seg-wrap").getBoundingClientRect().top + window.scrollY - 8;
        if (window.scrollY > top) window.scrollTo(0, top);
      }
    };
    seg.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (b) show(b.getAttribute("data-tab"), true);
    });
    seg.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      var j = (i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
      tabs[j].focus();
      show(tabs[j].getAttribute("data-tab"), true);
    });
    show((location.hash || "").slice(1) || tabs[0].getAttribute("data-tab"), false);
  }

  // ── 眉批 ↔ 原文 ──
  function light(key, on) {
    [].forEach.call(document.querySelectorAll('mark[data-k="' + key + '"], .note[data-k="' + key + '"], .ecard[data-k="' + key + '"]'), function (el) { el.classList.toggle("on", on); });
  }
  var pinned = null;
  document.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest("[data-k]");
    if (pinned) { light(pinned, false); }
    if (!el) { pinned = null; return; }
    var key = el.getAttribute("data-k");
    if (pinned === key) { pinned = null; return; }
    pinned = key;
    light(key, true);
    var listSide = el.classList.contains("note") || el.classList.contains("ecard");
    var other = listSide ? document.querySelector('mark[data-k="' + key + '"]') : document.querySelector('.note[data-k="' + key + '"], .ecard[data-k="' + key + '"]');
    if (other && other.hidden) filterTo("all");
    if (other) {
      var r = other.getBoundingClientRect();
      if (r.top < 70 || r.bottom > window.innerHeight - 90) {
        var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        other.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" });
      }
    }
  });
  // ── 英文：挑錯篩選 ──
  function filterTo(f) {
    [].forEach.call(document.querySelectorAll(".filters button"), function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-f") === f ? "true" : "false"); });
    [].forEach.call(document.querySelectorAll(".ecard"), function (c) { c.hidden = !(f === "all" || c.getAttribute("data-lv") === f); });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".filters button");
    if (b) filterTo(b.getAttribute("data-f"));
    var c = e.target.closest && e.target.closest(".copy");
    if (!c) return;
    var t = c.getAttribute("data-t");
    var done = function () { c.textContent = "已複製"; setTimeout(function () { c.textContent = "複製"; }, 1500); };
    var fallback = function () { var r = document.createRange(); r.selectNodeContents(c.previousElementSibling); var sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); c.textContent = "已選取"; };
    try { navigator.clipboard.writeText(t).then(done, fallback); } catch (err) { fallback(); }
  });

  document.addEventListener("keydown", function (e) {
    if ((e.key === "Enter" || e.key === " ") && document.activeElement && document.activeElement.matches("mark[data-k]")) {
      e.preventDefault();
      document.activeElement.click();
    }
  });
})();
