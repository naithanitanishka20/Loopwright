/* Loopwright product site: drawings and numbers from data.js, the live scale model in figure 1,
   the features menu, the two comparisons and the copy buttons. data.js is written by `loopwright site`. */
(function () {
  "use strict";

  var root = document.documentElement;
  var data = window.LOOPWRIGHT;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

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

  if (!data) {
    root.classList.remove("js");
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

  /* Figure 1: a signal leaves each hub and runs round its ring; a cut leg is fed from both ends */

  var stage = document.getElementById("model");
  if (stage && drawings.hero && drawings.hero.rings && stage.querySelector("svg.live")) {
    model(stage, stage.querySelector("svg.live"), drawings.hero.rings);
  }

  function model(stage, svg, ringData) {
    var plate = stage.closest(".plate");
    var readout = plate.querySelector("[data-readout]");
    var cutButton = plate.querySelector("[data-cut]");
    var live = document.getElementById("model-live");
    var SPEED = 7.5, COMET = 2.6, HEAD = 0.7, PAUSE = 1.2, TOUR_AFTER = 4;

    var rings = ringData.map(function (r) {
      var pieces = [], legs = {};
      each('.tb.cable[data-ring="' + r.hub + '"]', function (g) {
        var p = { el: g, a: Number(g.dataset.a), b: Number(g.dataset.b), core: g.querySelector(".core"), glow: g.querySelector(".glow") };
        pieces.push(p);
        (legs[g.dataset.leg] = legs[g.dataset.leg] || []).push(p);
      }, svg);
      var ends = r.stops.map(function (s) { return s.s; }).concat([r.length]);
      return {
        hub: r.hub, length: r.length, pieces: pieces, legs: legs, cut: 0,
        spans: ends.map(function (e, i) { return [i ? ends[i - 1] : 0, e]; }),
        sockets: r.stops.map(function (s) {
          return { s: s.s, node: s.node, el: svg.querySelector('.socket[data-node="' + s.node + '"]') };
        }),
        period: Math.max(2.2, r.length / SPEED + PAUSE)
      };
    });
    var main = rings[0];
    var choices = [];  // the legs a visitor can see: each has a click target, and the keys step through the same list
    each(".hit", function (hit) {
      var ring = rings.filter(function (r) { return r.hub === hit.dataset.ring; })[0];
      if (ring) choices.push({ ring: ring, leg: Number(hit.dataset.leg) });
    }, svg);
    var longest = main.spans.reduce(function (best, span, i) {
      return span[1] - span[0] > main.spans[best][1] - main.spans[best][0] ? i : best;
    }, 0) + 1;
    var selected = choices.filter(function (c) { return c.ring === main && c.leg === longest; })[0];
    var clock = 0, last = 0, frame = 0, visible = false, touched = -1e9, touringCut = false, pointing = null;

    function legText(choice) {
      var span = choice.ring.spans[choice.leg - 1];
      return choice.ring.hub + " leg " + choice.leg + ", " + (span[1] - span[0]).toFixed(1) + " m";
    }

    function paint(el, piece, lo, hi) {
      var u0 = Math.max(lo, piece.a), u1 = Math.min(hi, piece.b);
      if (!(u1 - u0 > 0.002)) {
        if (el.style.visibility !== "hidden") el.style.visibility = "hidden";
        return;
      }
      el.style.strokeDasharray = (u1 - u0).toFixed(3) + " " + (piece.b - piece.a + 1).toFixed(3);
      el.style.strokeDashoffset = (piece.a - u0).toFixed(3);
      el.style.visibility = "visible";
    }

    function draw(ring) {
      var s = Math.min((clock % ring.period) * SPEED, ring.length);
      var c = null, ahead = s, back = null;
      if (ring.cut) {
        var span = ring.spans[ring.cut - 1];
        c = (span[0] + span[1]) / 2;
        ahead = Math.min(s, c);
        back = Math.max(ring.length - s, c);
      }
      var lit = 0;
      ring.sockets.forEach(function (k) {
        var on = k.s <= ahead + 1e-6 || (back !== null && k.s >= back - 1e-6);
        if (on) lit += 1;
        if (k.el.classList.contains("fed") !== on) k.el.classList.toggle("fed", on);
      });
      ring.pieces.forEach(function (p) {
        if (c !== null && p.b > c) {
          paint(p.glow, p, back, Math.min(back + COMET, ring.length));
          paint(p.core, p, back, Math.min(back + HEAD, ring.length));
        } else {
          paint(p.glow, p, ahead - COMET, ahead);
          paint(p.core, p, ahead - HEAD, ahead);
        }
      });
      return { s: s, lit: lit };
    }

    function say(view) {
      var text;
      if (main.cut) text = "H1 leg " + main.cut + " cut, " + view.lit + " of " + main.sockets.length + " sockets fed";
      else if (view.s >= main.length) text = "H1 ring closed, " + main.sockets.length + " sockets fed";
      else text = "H1 signal at " + view.s.toFixed(1) + " of " + main.length.toFixed(1) + " m";
      if (readout.textContent !== text) readout.textContent = text;
    }

    function still() {
      readout.textContent = main.cut ? "H1 leg " + main.cut + " cut, every socket still fed"
        : "H1 ring, " + main.length.toFixed(1) + " m, " + main.sockets.length + " sockets fed";
    }

    function tick(now) {
      var dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
      last = now;
      clock += dt;
      if (clock - touched > TOUR_AFTER) tour();
      var view = rings.map(draw)[0];
      if (!pointing) say(view);
      frame = visible ? requestAnimationFrame(tick) : 0;
    }

    function tour() {
      var lap = Math.floor(clock / main.period) % 5;
      var want = lap === 3 || lap === 4;
      if (want && !main.cut) {
        setCut(main, longest, false);
        touringCut = true;
      } else if (!want && touringCut) {
        setCut(main, 0, false);
        touringCut = false;
      }
    }

    function describe(ring) {
      if (!ring.cut) return "Every leg of ring " + ring.hub + " joined.";
      var span = ring.spans[ring.cut - 1], c = (span[0] + span[1]) / 2;
      var name = function (k) { return k.node; };
      var ahead = ring.sockets.filter(function (k) { return k.s < c; }).map(name);
      var back = ring.sockets.filter(function (k) { return k.s > c; }).map(name);
      return "Leg " + ring.cut + " of ring " + ring.hub + " cut. Every socket is still fed: " +
        (ahead.join(", ") || "none") + " one way, " + (back.join(", ") || "none") + " the other.";
    }

    function setCut(ring, leg, announce) {
      ring.cut = leg;
      each(".tb.joint", function (g) {
        var owner = rings.filter(function (r) { return r.hub === g.dataset.ring; })[0];
        g.classList.toggle("cut", !!owner && owner.cut === Number(g.dataset.leg));
      }, svg);
      var anyCut = rings.some(function (r) { return r.cut; });
      cutButton.setAttribute("aria-pressed", String(anyCut));
      cutButton.textContent = anyCut ? "Rejoin" : "Cut a leg";
      if (announce) live.textContent = describe(ring);
      if (reduce.matches) still();
    }

    function touch() {
      touched = clock;
      touringCut = false;
    }

    function highlight(choice) {
      pointing = choice;
      each(".tb.on", function (g) { g.classList.remove("on"); }, svg);
      if (!choice) {
        if (reduce.matches) still();
        return;
      }
      (choice.ring.legs[choice.leg] || []).forEach(function (p) { p.el.classList.add("on"); });
      readout.textContent = legText(choice);
    }

    function toggle(choice) {
      touch();
      setCut(choice.ring, choice.ring.cut === choice.leg ? 0 : choice.leg, true);
    }

    // Parallel lanes lie closer than a comfortable target is wide, so of the targets under the
    // pointer, the leg is the one whose cable runs nearest to it.
    function legAt(e) {
      var best = null, nearest = Infinity;
      document.elementsFromPoint(e.clientX, e.clientY).forEach(function (el) {
        if (!el.classList || !el.classList.contains("hit")) return;
        var m = el.getScreenCTM(), length = el.getTotalLength(), step = Math.max(1, length / 160);
        for (var s = 0; s <= length; s += step) {
          var q = el.getPointAtLength(s);
          var dx = m.a * q.x + m.c * q.y + m.e - e.clientX, dy = m.b * q.x + m.d * q.y + m.f - e.clientY;
          if (dx * dx + dy * dy < nearest) {
            nearest = dx * dx + dy * dy;
            best = el;
          }
        }
      });
      return best && choices.filter(function (c) { return c.ring.hub === best.dataset.ring && c.leg === Number(best.dataset.leg); })[0];
    }

    var hits = svg.querySelector(".hits");
    var clicked = null;  // after a click the readout shows the cut until the pointer moves to another leg
    hits.addEventListener("pointermove", function (e) {
      var choice = legAt(e);
      if (choice !== clicked) clicked = null;
      if (choice && choice !== pointing && !clicked) {
        touch();
        highlight(choice);
      }
    });
    hits.addEventListener("pointerleave", function () {
      clicked = null;
      highlight(null);
    });
    hits.addEventListener("click", function (e) {
      var choice = legAt(e);
      if (!choice) return;
      selected = clicked = choice;
      toggle(choice);
      highlight(null);
    });

    cutButton.addEventListener("click", function () {
      var ring = rings.filter(function (r) { return r.cut; })[0];
      touch();
      if (ring) setCut(ring, 0, true);
      else toggle(selected);
    });

    stage.addEventListener("keydown", function (e) {
      var at = choices.indexOf(selected);
      if (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "Home" || e.key === "End") {
        e.preventDefault();
        touch();
        if (e.key === "Home") selected = choices[0];
        else if (e.key === "End") selected = choices[choices.length - 1];
        else selected = choices[(at + (e.key === "ArrowRight" ? 1 : choices.length - 1)) % choices.length];
        highlight(selected);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle(selected);
      } else if (e.key === "Escape") {
        touch();
        rings.forEach(function (r) { if (r.cut) setCut(r, 0, true); });
        highlight(null);
      }
    });
    stage.addEventListener("blur", function () { highlight(null); });

    if (reduce.matches) {
      root.dataset.model = "still";
      rings.forEach(function (r) { r.sockets.forEach(function (k) { k.el.classList.add("fed"); }); });
      still();
      return;
    }
    root.dataset.model = "live";
    function run() {
      if (!frame && visible) {
        last = 0;
        frame = requestAnimationFrame(tick);
      }
    }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[entries.length - 1].isIntersecting;
        if (visible) run();
      }, { rootMargin: "120px 0px" }).observe(stage);
    } else {
      visible = true;
      run();
    }
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
