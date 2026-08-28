/* ---------------------------------------------------------------------------
 * SOUND
 *
 * Chiptune blips synthesised with WebAudio — square and triangle waves only,
 * no samples, no files. The context can't start until the player interacts,
 * so it is created lazily on the first sound after the title screen.
 * ------------------------------------------------------------------------- */

const SFX = (() => {
  let ctx = null;
  let muted = false;

  function unlock() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
  }

  /* One note. Frequency slides linearly to `to` if given, which is most of
     what makes a beep read as "coin" versus "error". */
  function tone({ freq, to, dur = 0.08, type = "square", gain = 0.05, delay = 0 }) {
    if (muted || !ctx) return;
    const t0 = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (to) osc.frequency.linearRampToValueAtTime(to, t0 + dur);

    /* Hard attack, quick decay — no analogue softness. */
    amp.gain.setValueAtTime(gain, t0);
    amp.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);

    osc.connect(amp).connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  const seq = (notes) => notes.forEach((n) => tone(n));

  const api = {
    unlock,
    toggle() {
      muted = !muted;
      if (!muted) api.select();
      return muted;
    },
    isMuted: () => muted,

    /* One character of dialogue. Kept quiet and short — it fires a lot. */
    speak: () => tone({ freq: 420 + Math.random() * 90, dur: 0.025, gain: 0.022, type: "square" }),
    type: () => tone({ freq: 900, dur: 0.02, gain: 0.015, type: "square" }),

    select: () => tone({ freq: 660, to: 880, dur: 0.07, gain: 0.05 }),
    ask: () => seq([{ freq: 520, dur: 0.05 }, { freq: 700, dur: 0.06, delay: 0.05 }]),

    /* Slamming a folder on the table. */
    present: () =>
      seq([
        { freq: 180, to: 70, dur: 0.14, type: "triangle", gain: 0.14 },
        { freq: 900, to: 1200, dur: 0.09, delay: 0.06, gain: 0.05 },
      ]),

    hurt: () =>
      seq([
        { freq: 300, to: 120, dur: 0.16, type: "square", gain: 0.07 },
        { freq: 150, to: 60, dur: 0.2, delay: 0.06, type: "triangle", gain: 0.08 },
      ]),

    unlock_: () =>
      seq([
        { freq: 784, dur: 0.07, gain: 0.05 },
        { freq: 988, dur: 0.07, delay: 0.07, gain: 0.05 },
        { freq: 1319, dur: 0.14, delay: 0.14, gain: 0.05 },
      ]),

    win: () =>
      seq([
        { freq: 523, dur: 0.1, gain: 0.06 },
        { freq: 659, dur: 0.1, delay: 0.1, gain: 0.06 },
        { freq: 784, dur: 0.1, delay: 0.2, gain: 0.06 },
        { freq: 1047, dur: 0.34, delay: 0.3, gain: 0.06 },
      ]),

    lose: () =>
      seq([
        { freq: 440, dur: 0.14, gain: 0.06 },
        { freq: 349, dur: 0.14, delay: 0.14, gain: 0.06 },
        { freq: 262, dur: 0.4, delay: 0.28, type: "triangle", gain: 0.07 },
      ]),

    start: () =>
      seq([
        { freq: 392, dur: 0.08, gain: 0.06 },
        { freq: 523, dur: 0.08, delay: 0.08, gain: 0.06 },
        { freq: 784, dur: 0.22, delay: 0.16, gain: 0.06 },
      ]),

    error: () =>
      seq([
        { freq: 200, dur: 0.12, type: "square", gain: 0.06 },
        { freq: 150, dur: 0.18, delay: 0.12, type: "square", gain: 0.06 },
      ]),
  };

  return api;
})();
