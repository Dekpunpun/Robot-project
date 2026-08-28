/* ---------------------------------------------------------------------------
 * PORTRAIT
 *
 * The suspect's face, drawn procedurally on a 32x32 pixel grid. Nothing is
 * loaded from disk — every feature is a rectangle, so the expression can be
 * rebuilt each frame from the current mood.
 *
 * Colours come from CASE.suspect.sprite when a case supplies one, so swapping
 * the case swaps the character's look without touching this file.
 * ------------------------------------------------------------------------- */

const Portrait = (() => {
  const G = 32; // grid is 32x32 "pixels"

  const BASE = {
    hair: "#2b2233",
    hairLo: "#1a1422",
    skin: "#d8a077",
    skinLo: "#b07c58",
    skinHi: "#eab98f",
    eye: "#f2efe2",
    pupil: "#241c2c",
    mouth: "#6d3a34",
    coat: "#3c4570",
    coatLo: "#252b48",
    shirt: "#c9c8bd",
    tie: "#8c2f2c",
    sweat: "#7fd4ff",
    wall: "#161b30",
    wallLit: "#232a49",
    floor: "#101426",
  };

  /* The face is drawn to every mounted canvas — the title screen shows the
     same character as the interrogation room. */
  let targets = [];
  let cv, cx, scale;
  let mood = "steady";
  let blinking = false;
  let nextBlinkAt = 0;
  let shakeUntil = 0;
  let flashUntil = 0;
  let running = false;

  const pal = () => ({ ...BASE, ...(CASE.suspect.sprite || {}) });

  /* ------------------------------ primitives ----------------------------- */

  function px(x, y, w, h, c) {
    cx.fillStyle = c;
    cx.fillRect(Math.round(x * scale), Math.round(y * scale), Math.round(w * scale), Math.round(h * scale));
  }

  /* Draw once on the left, once mirrored across the vertical centre line. */
  function sym(x, y, w, h, c) {
    px(x, y, w, h, c);
    px(G - x - w, y, w, h, c);
  }

  /* -------------------------------- the face ------------------------------ */

  /* A bare room with one lamp on him — it separates the figure from the panel
     behind it, and gives the shake something to move against. */
  function drawBackdrop(p) {
    px(0, 0, G, G, p.wall);
    px(7, 0, 18, 22, p.wallLit);
    px(5, 3, 2, 16, p.wallLit);
    px(25, 3, 2, 16, p.wallLit);
    px(0, 24, G, 8, p.floor);
    px(0, 24, G, 1, p.wallLit);
  }

  function drawBody(p) {
    px(2, 26, 28, 6, p.coat);
    px(2, 26, 28, 1, p.coatLo);
    sym(2, 27, 3, 5, p.coatLo);

    // open collar with a shirt wedge and a tie down the middle
    px(11, 25, 10, 2, p.shirt);
    px(12, 27, 8, 2, p.shirt);
    px(13, 29, 6, 1, p.shirt);
    px(14, 26, 4, 2, p.tie);
    px(14, 28, 4, 4, p.tie);
  }

  function drawHead(p) {
    px(12, 22, 8, 4, p.skinLo); // neck, always in shadow

    px(9, 4, 14, 2, p.skin);
    px(8, 6, 16, 14, p.skin);
    px(9, 20, 14, 2, p.skin);
    px(11, 22, 10, 1, p.skin);

    sym(6, 12, 2, 4, p.skinLo); // ears
    px(21, 7, 2, 14, p.skinLo); // one side of the face falls away from the light
    px(9, 7, 1, 12, p.skinHi);
    px(10, 20, 12, 1, p.skinLo); // under the jaw
  }

  function drawHair(p) {
    px(9, 2, 14, 2, p.hair);
    px(8, 4, 16, 4, p.hair);
    sym(7, 6, 2, 8, p.hair); // temples
    px(11, 8, 3, 1, p.hair); // a forelock breaking the hairline
    px(18, 8, 2, 1, p.hair);
    px(9, 2, 12, 1, p.hairLo);
    px(8, 4, 1, 8, p.hairLo);
  }

  /* Brows carry most of the expression. */
  function drawBrows(p) {
    if (mood === "steady") {
      sym(10, 10, 5, 1, p.hairLo);
    } else if (mood === "rattled") {
      // inner ends lifted — the worried tell
      px(10, 10, 3, 1, p.hairLo);
      px(13, 9, 2, 1, p.hairLo);
      px(19, 10, 3, 1, p.hairLo);
      px(17, 9, 2, 1, p.hairLo);
    } else {
      // driven down and inward
      px(10, 9, 3, 1, p.hairLo);
      px(13, 10, 2, 2, p.hairLo);
      px(19, 9, 3, 1, p.hairLo);
      px(17, 10, 2, 2, p.hairLo);
    }
  }

  function drawEyes(p) {
    if (blinking) {
      sym(11, 13, 4, 1, p.skinLo);
      return;
    }

    const wide = mood === "cracking";
    sym(11, 12, 4, wide ? 4 : 3, p.eye);

    // pupils drift inward as he loses the room
    const px0 = mood === "steady" ? 12 : 13;
    sym(px0, wide ? 13 : 13, 2, 2, p.pupil);
  }

  function drawFace(p) {
    px(15, 13, 1, 4, p.skinHi); // nose: one lit edge, one shadowed
    px(16, 14, 2, 3, p.skinLo);
    px(15, 17, 3, 1, p.skinLo);

    if (mood === "steady") {
      px(13, 19, 6, 1, p.mouth);
    } else if (mood === "rattled") {
      px(14, 19, 4, 1, p.mouth); // tight, held shut
      px(13, 19, 1, 1, p.skinLo);
    } else {
      px(13, 18, 6, 3, p.mouth); // open — nothing left to say
      px(14, 19, 4, 1, "#3b1d1c");
    }

    if (mood !== "steady") {
      px(24, 8, 2, 3, p.sweat);
      px(24, 11, 2, 1, p.sweat);
    }
    if (mood === "cracking") {
      px(6, 13, 2, 3, p.sweat);
      px(6, 16, 2, 1, p.sweat);
      sym(10, 16, 3, 1, "#c98a72"); // flushed cheeks
    }
  }

  /* -------------------------------- the loop ------------------------------ */

  function render(now) {
    if (now > nextBlinkAt) {
      blinking = !blinking;
      nextBlinkAt = now + (blinking ? 110 : 1800 + Math.random() * 2600);
    }

    for (const t of targets) {
      cv = t.cv;
      cx = t.cx;
      scale = t.scale;
      drawFrame(now);
    }

    requestAnimationFrame(render);
  }

  function drawFrame(now) {
    const p = pal();
    cx.clearRect(0, 0, cv.width, cv.height);

    /* Breathing bob, plus a hard shake for a beat after taking a hit. */
    const shaking = now < shakeUntil;
    const bob = Math.floor((now / 900) % 2);
    const dx = shaking ? (Math.random() < 0.5 ? -1 : 1) * scale : 0;
    const dy = (shaking ? (Math.random() < 0.5 ? -1 : 1) * scale : 0) + bob * (scale / 2);

    /* The room stays put; only the man in it shakes. */
    drawBackdrop(p);

    cx.save();
    cx.translate(dx, dy);
    drawBody(p);
    drawHead(p);
    drawHair(p);
    drawBrows(p);
    drawEyes(p);
    drawFace(p);
    cx.restore();

    if (now < flashUntil && Math.floor(now / 60) % 2 === 0) {
      cx.globalCompositeOperation = "source-atop";
      cx.fillStyle = "rgba(255,255,255,0.75)";
      cx.fillRect(0, 0, cv.width, cv.height);
      cx.globalCompositeOperation = "source-over";
    }
  }

  /* --------------------------------- api ---------------------------------- */

  function mount(canvas) {
    if (targets.some((t) => t.cv === canvas)) return;
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    targets.push({ cv: canvas, cx: ctx, scale: canvas.width / G });

    if (!running) {
      running = true;
      requestAnimationFrame(render);
    }
  }

  const set = (next) => { mood = next; };
  const hit = () => { shakeUntil = performance.now() + 320; flashUntil = performance.now() + 220; };
  const reset = () => { mood = "steady"; shakeUntil = 0; flashUntil = 0; };

  return { mount, set, hit, reset };
})();
