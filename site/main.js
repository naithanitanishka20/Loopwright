/* Loopwright product site: drawings and numbers from data.js, the live scale model in figure 1,
   the features menu, the How it works answers, the two comparisons and the copy buttons. data.js is
   written by `loopwright site`. */
(function () {
  "use strict";

  var root = document.documentElement;
  var data = window.LOOPWRIGHT;

  function each(selector, fn, scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll(selector), fn);
  }

  /* The features menu, on every page */

  each(".menu", function (menu) {
    var button = menu.querySelector(".menu-button");
    var list = menu.querySelector(".menu-list");
    function set(open) {
      button.setAttribute("aria-expanded", String(open));
      list.hidden = !open;
    }
    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") !== "true";
      set(open);
      if (open) list.querySelector("a").focus();
    });
    list.addEventListener("click", function (e) {
      if (e.target.closest("a")) set(false);
    });
    menu.addEventListener("keydown", function (e) {
      var links = Array.prototype.slice.call(list.querySelectorAll("a"));
      var at = links.indexOf(document.activeElement);
      if (e.key === "Escape" && !list.hidden) {
        set(false);
        button.focus();
      } else if (!list.hidden && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        e.preventDefault();
        links[(at + (e.key === "ArrowDown" ? 1 : links.length - 1)) % links.length].focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (!menu.contains(e.target)) set(false);
    });
  });

  /* How it works: an answer opens while the pointer is over its question or the question has the
     focus; where there is no pointer, a tap opens it and closes the others */

  var noHover = window.matchMedia("(hover: none)");
  var asks = Array.prototype.slice.call(document.querySelectorAll(".ask"));
  asks.forEach(function (ask) {
    var question = ask.querySelector(".ask-q");
    function sync() {
      var open = noHover.matches ? ask.classList.contains("open") : ask.matches(":hover, :focus-within");
      question.setAttribute("aria-expanded", String(open));
    }
    ["mouseenter", "mouseleave", "focusin", "focusout"].forEach(function (type) {
      ask.addEventListener(type, function () { setTimeout(sync); });
    });
    question.addEventListener("click", function () {
      if (!noHover.matches) return;
      var open = !ask.classList.contains("open");
      asks.forEach(function (other) {
        other.classList.toggle("open", other === ask && open);
        other.querySelector(".ask-q").setAttribute("aria-expanded", String(other === ask && open));
      });
    });
  });

  /* Served with a hosted app, the feature buttons open that app instead of one on this machine, and the
     playground links show */

  var hosted = document.querySelector('meta[name="loopwright:app"]');
  if (hosted) {
    each('.feature a[href^="http://127.0.0.1:8000/"]', function (a) {
      a.href = hosted.content + a.hash;
    });
    each("[data-local]", function (el) { el.hidden = true; });
    each("[data-hosted]", function (el) { el.hidden = false; });
  }

  if (!data) {
    if (document.querySelector("[data-drawing]")) root.classList.remove("js");  // the figures fall back to their images
    return;
  }

  function fixed(digits) {
    return function (v) {
      return Number(v).toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    };
  }

  var whole = fixed(0);
  var tenths = fixed(1);
  var FIGURE = { plan: String, hubs: whole, lower_bound: whole, greedy: whole, length_m: tenths, overlap_m: tenths, J: tenths };

  /* Numbers over every plan, and the solver's settings */

  var n = data.numbers;
  var numbers = {
    plans: whole(n.plans), feasible: whole(n.feasible), valid: whole(n.valid), infeasible: whole(n.plans - n.feasible),
    hubs: whole(n.hubs), lower_bound: whole(n.lower_bound), greedy: whole(n.greedy), at_bound: whole(n.at_bound),
    length_m: whole(n.length_m), J: whole(n.J), J_per_plan: tenths(n.J / n.valid),
    p50_s: fixed(2)(n.p50_s), p95_s: fixed(2)(n.p95_s), version: data.version
  };
  each("[data-num]", function (el) {
    if (numbers[el.dataset.num] !== undefined) el.textContent = numbers[el.dataset.num];
  });
  each("[data-setting]", function (el) {
    var v = data.settings && data.settings[el.dataset.setting];
    if (v !== undefined) el.textContent = Array.isArray(v) ? v.join(", ") : String(v);
  });

  /* Figures for each drawing */

  var drawings = data.drawings;

  function figure(name, key) {
    var d = drawings[name];
    return d && d[key] !== undefined ? (FIGURE[key] || String)(d[key]) : null;
  }

  each("[data-fig]", function (el) {
    var v = figure.apply(null, el.dataset.fig.split("."));
    if (v !== null) el.textContent = v;
  });

  function fillFigures(list) {
    each("[data-key]", function (el) {
      var v = figure(list.dataset.figures, el.dataset.key);
      if (v !== null) el.textContent = v;
    }, list);
  }
  each("[data-figures]", fillFigures);

  function ruleReadout(el, name) {
    el.dataset.figuresReadout = name;
    el.textContent = figure(name, "hubs") + " hubs, " + figure(name, "length_m") + " m";
  }
  each("[data-figures-readout]", function (el) { ruleReadout(el, el.dataset.figuresReadout); });

  /* Drawings and charts go inline, so they can move and keep their tooltips */

  each("[data-drawing]", function (box) {
    var d = drawings[box.dataset.drawing];
    if (d) box.innerHTML = d.svg;
  });
  each("[data-chart]", function (box) {
    var svg = data.charts && data.charts[box.dataset.chart];
    if (svg) box.innerHTML = svg;
  });

  /* Figure 1: the live scale model, wired by model.js */

  var stage = document.getElementById("model");
  if (stage && window.loopwrightModel && drawings.hero && drawings.hero.rings && stage.querySelector("svg.live")) {
    window.loopwrightModel(stage, stage.querySelector("svg.live"), drawings.hero.rings);
  }

  /* Figure 2: the door rule, two models of one plan crossfaded */

  each("[data-show]", function (button) {
    button.addEventListener("click", function () {
      var plate = button.closest(".plate-figure");
      var name = button.dataset.show;
      each("[data-show]", function (b) { b.setAttribute("aria-pressed", String(b === button)); }, plate);
      each(".stack > .drawing", function (d) {
        var on = d.dataset.drawing === name;
        d.classList.toggle("on", on);
        if (on) d.removeAttribute("aria-hidden");
        else d.setAttribute("aria-hidden", "true");
      }, plate);
      var list = plate.querySelector("[data-figures]");
      list.dataset.figures = name;
      fillFigures(list);
      each("[data-figures-readout]", function (el) { ruleReadout(el, name); }, plate);
    });
  });
  each(".stack > .drawing:not(.on)", function (d) { d.setAttribute("aria-hidden", "true"); });

  /* Figure 3: before and after, wiped by the pointer or the arrow keys on the slider */

  each(".wipe", function (wipe) {
    var range = wipe.querySelector("input");
    var dragging = false;
    function show() {
      wipe.style.setProperty("--pos", range.value + "%");
      range.setAttribute("aria-valuetext", range.value + "% before");
    }
    function follow(e) {
      var r = wipe.getBoundingClientRect();
      range.value = String(Math.round(Math.min(100, Math.max(0, ((e.clientX - r.left) / r.width) * 100))));
      show();
    }
    range.addEventListener("input", show);
    wipe.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      dragging = true;
      wipe.setPointerCapture(e.pointerId);
      follow(e);
    });
    wipe.addEventListener("pointermove", function (e) {
      if (dragging) follow(e);
    });
    ["pointerup", "pointercancel"].forEach(function (type) {
      wipe.addEventListener(type, function () { dragging = false; });
    });
    show();
  });

  /* Commands: pick the operating system, copy a block */

  var status = document.getElementById("status");

  each("[data-os-current]", function (section) {
    function pick(os) {
      section.setAttribute("data-os-current", os);
      each("[data-os-pick]", function (b) { b.setAttribute("aria-pressed", String(b.dataset.osPick === os)); }, section);
    }
    var platform = navigator.platform || "";
    pick(/Win/.test(platform) || !/Mac|Linux|X11|CrOS|iPhone|iPad/.test(platform) ? "windows" : "unix");
    each("[data-os-pick]", function (b) {
      b.addEventListener("click", function () { pick(b.dataset.osPick); });
    }, section);
  });

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return fallbackCopy(text); });
    }
    return fallbackCopy(text);
  }

  function fallbackCopy(text) {
    return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (e) {
        ok = false;
      }
      area.remove();
      if (ok) resolve();
      else reject(new Error("copy refused"));
    });
  }

  each(".copy", function (button) {
    button.addEventListener("click", function () {
      var block = button.closest(".code");
      var section = button.closest("[data-os-current]");
      var os = section ? section.getAttribute("data-os-current") : "windows";
      var code = block.querySelector('[data-os="' + os + '"]') || block.querySelector("code");
      copyText(code.textContent).then(function () {
        button.textContent = "Copied";
        button.classList.add("done");
        if (status) status.textContent = "Copied to the clipboard";
      }, function () {
        button.textContent = "Select and copy";
        var range = document.createRange();
        range.selectNodeContents(code);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      });
      clearTimeout(button.reset);
      button.reset = setTimeout(function () {
        button.textContent = "Copy";
        button.classList.remove("done");
        if (status) status.textContent = "";
      }, 1800);
    });
  });
})();
