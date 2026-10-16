/* The live scale model, for figure 1 and for the playground: a signal leaves each hub and runs round its
   ring, lighting each socket; a cut leg is fed from both ends. loopwrightModel(stage, svg, rings) wires
   one model and returns { stop }, so a page can replace it with another. */
(function () {
  "use strict";

  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function each(selector, fn, scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll(selector), fn);
  }

  window.loopwrightModel = function (stage, svg, ringData) {
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
    var selected = choices.filter(function (c) { return c.ring === main && c.leg === longest; })[0] || choices[0];
    var clock = 0, last = 0, frame = 0, visible = false, touched = -1e9, touringCut = false, pointing = null;
    var stopped = false, watcher = null;
    cutButton.disabled = !selected;

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
      if (main.cut) text = main.hub + " leg " + main.cut + " cut, " + view.lit + " of " + main.sockets.length + " sockets fed";
      else if (view.s >= main.length) text = main.hub + " ring closed, " + main.sockets.length + " sockets fed";
      else text = main.hub + " signal at " + view.s.toFixed(1) + " of " + main.length.toFixed(1) + " m";
      if (readout.textContent !== text) readout.textContent = text;
    }

    function still() {
      readout.textContent = main.cut ? main.hub + " leg " + main.cut + " cut, every socket still fed"
        : main.hub + " ring, " + main.length.toFixed(1) + " m, " + main.sockets.length + " sockets fed";
    }

    function tick(now) {
      if (stopped) return;
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
      if (announce && live) live.textContent = describe(ring);
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
      if (!choice) return;
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
    if (hits) {
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
    }

    cutButton.addEventListener("click", function () {
      var ring = rings.filter(function (r) { return r.cut; })[0];
      touch();
      if (ring) setCut(ring, 0, true);
      else toggle(selected);
    });

    stage.addEventListener("keydown", function (e) {
      if (!choices.length) return;
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

    function stop() {
      stopped = true;
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      if (watcher) watcher.disconnect();
    }

    if (reduce.matches) {
      root.dataset.model = "still";
      rings.forEach(function (r) { r.sockets.forEach(function (k) { k.el.classList.add("fed"); }); });
      still();
      return { stop: stop };
    }
    root.dataset.model = "live";
    function run() {
      if (!frame && visible && !stopped) {
        last = 0;
        frame = requestAnimationFrame(tick);
      }
    }
    if ("IntersectionObserver" in window) {
      watcher = new IntersectionObserver(function (entries) {
        visible = entries[entries.length - 1].isIntersecting;
        if (visible) run();
      }, { rootMargin: "120px 0px" });
      watcher.observe(stage);
    } else {
      visible = true;
      run();
    }
    return { stop: stop };
  };
})();
