/* Loopwright product site: drawings and numbers from data.js, the hero trace, the two
   comparisons and the copy buttons. data.js is written by `loopwright site`. */
(function () {
  "use strict";

  var root = document.documentElement;
  var data = window.LOOPWRIGHT;
  if (!data) {
    root.classList.remove("js");
    root.setAttribute("data-hero", "done");
    return;
  }
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var loaded = performance.now();

  function each(selector, fn, scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll(selector), fn);
  }

  function fixed(digits) {
    return function (v) {
      return Number(v).toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    };
  }

  var whole = fixed(0);
  var tenths = fixed(1);
  var FIGURE = { plan: String, hubs: whole, lower_bound: whole, greedy: whole, length_m: tenths, overlap_m: tenths, J: tenths };

  /* Numbers over every plan */

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

  /* Drawings and charts go inline, so they can animate and keep their tooltips */

  var plans = [];
  each("[data-drawing]", function (box) {
    var d = drawings[box.dataset.drawing];
    if (!d) return;
    box.innerHTML = d.svg;
    plans.push(box.querySelector("svg"));
  });
  each("[data-chart]", function (box) {
    var svg = data.charts && data.charts[box.dataset.chart];
    if (svg) box.innerHTML = svg;
  });

  /* Markers keep a readable size however small the drawing gets */

  function fit(svg) {
    var box = svg.viewBox.baseVal;
    var width = svg.getBoundingClientRect().width;
    if (!width || !box || !box.width) return;
    var s = Math.min(2, Math.max(1, box.width / width));
    svg.style.setProperty("--s", s.toFixed(3));
  }
  function fitAll() {
    plans.forEach(fit);
  }
  fitAll();
  if ("ResizeObserver" in window) {
    var watch = new ResizeObserver(fitAll);
    plans.forEach(function (svg) { watch.observe(svg); });
  } else {
    window.addEventListener("resize", fitAll);
  }

  /* The hero: line-work, then hubs, then each ring drawn leg by leg in visiting order */

  var hero = document.querySelector('[data-drawing="hero"] svg');
  var running = [];
  var timers = [];
  var RING_MS = 2600;

  function stop() {
    running.forEach(function (a) { a.cancel(); });
    timers.forEach(clearTimeout);
    running = [];
    timers = [];
  }

  function later(fn, ms) {
    timers.push(setTimeout(fn, ms));
  }

  function settle(svg) {
    stop();
    svg.classList.remove("unbuilt", "unhubbed");
    each(".leg", function (leg) {
      leg.style.strokeDasharray = "";
      leg.style.strokeDashoffset = "";
    }, svg);
    each(".node", function (node) { node.classList.remove("unlit"); }, svg);
    root.setAttribute("data-hero", "done");
  }

  function arm(svg) {
    stop();
    each(".leg", function (leg) {
      var len = leg.getTotalLength();
      leg.style.strokeDasharray = len + " " + len;
      leg.style.strokeDashoffset = String(len);
    }, svg);
    each(".node", function (node) { node.classList.add("unlit"); }, svg);
    svg.classList.add("unbuilt", "unhubbed");
    root.setAttribute("data-hero", "armed");
  }

  function play(svg, wait) {
    root.setAttribute("data-hero", "running");
    svg.getBoundingClientRect();
    later(function () { svg.classList.remove("unbuilt"); }, wait);
    later(function () { svg.classList.remove("unhubbed"); }, wait + 500);

    var rings = {};
    each(".leg", function (leg) {
      var hub = leg.dataset.ring;
      (rings[hub] = rings[hub] || []).push({ el: leg, step: Number(leg.dataset.step), len: leg.getTotalLength() });
    }, svg);
    var hubs = Object.keys(rings);
    var longest = 1;
    hubs.forEach(function (hub) {
      rings[hub].sort(function (a, b) { return a.step - b.step; });
      longest = Math.max(longest, rings[hub].reduce(function (sum, leg) { return sum + leg.len; }, 0));
    });
    var speed = longest / RING_MS;
    var pending = 0;
    hubs.forEach(function (hub) {
      var at = wait + 850;
      rings[hub].forEach(function (leg) {
        var duration = Math.max(160, leg.len / speed);
        var a = leg.el.animate(
          [{ strokeDashoffset: String(leg.len) }, { strokeDashoffset: "0" }],
          { duration: duration, delay: at, easing: "linear", fill: "forwards" }
        );
        pending += 1;
        running.push(a);
        a.onfinish = function () {
          var node = svg.querySelector('.node[data-ring="' + hub + '"][data-step="' + leg.step + '"]');
          if (node) node.classList.remove("unlit");
          pending -= 1;
          if (pending === 0) settle(svg);
        };
        at += duration;
      });
    });
    if (pending === 0) settle(svg);
  }

  function whenVisible(el, fn) {
    if (!("IntersectionObserver" in window)) {
      fn();
      return;
    }
    var seen = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) {
        seen.disconnect();
        fn();
      }
    }, { threshold: 0.35 });
    seen.observe(el);
  }

  if (!hero) {
    root.setAttribute("data-hero", "done");
  } else if (reduce.matches || !hero.animate) {
    settle(hero);
  } else {
    arm(hero);
    whenVisible(hero, function () {
      play(hero, Math.max(0, 450 - (performance.now() - loaded)));
    });
  }

  each(".replay", function (button) {
    button.addEventListener("click", function () {
      if (!hero) return;
      if (reduce.matches || !hero.animate) {
        settle(hero);
        return;
      }
      arm(hero);
      play(hero, 0);
    });
  });

  /* The door rule: two drawings of one plan, crossfaded */

  each("[data-show]", function (button) {
    button.addEventListener("click", function () {
      var section = button.closest(".section");
      var name = button.dataset.show;
      each("[data-show]", function (b) { b.setAttribute("aria-pressed", String(b === button)); }, section);
      each(".stack > .drawing", function (d) {
        var on = d.dataset.drawing === name;
        d.classList.toggle("on", on);
        if (on) d.removeAttribute("aria-hidden");
        else d.setAttribute("aria-hidden", "true");
      }, section);
      var list = section.querySelector("[data-figures]");
      list.dataset.figures = name;
      fillFigures(list);
    });
  });
  each(".stack > .drawing:not(.on)", function (d) { d.setAttribute("aria-hidden", "true"); });

  /* Before and after: drag across the drawing, or use the arrow keys on the slider */

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
