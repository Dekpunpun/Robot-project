# The Last Exhibit

An 8-bit detective interrogation game. You question a single AI-powered suspect in free
text, present evidence to catch him contradicting himself, and close the case with an
accusation you can actually back up.

The suspect is drawn as a pixel sprite that blinks, sweats and flinches as his story comes
apart; dialogue types out with a blip; the sound is synthesised square waves. Nothing is
loaded from an image or audio file — the whole presentation is code.

## Running it

The game needs an OpenAI-compatible LLM server. It defaults to LM Studio on
`localhost:1234`.

1. Start your local server and load a chat model.
2. Then:

```bash
node server.mjs
```

Open <http://localhost:5173>.

That's it — no install step, no dependencies, no build.

### Why there's a server

LM Studio sends no `Access-Control-Allow-Origin` header, so a browser page cannot call it
cross-origin — every request fails CORS. `server.mjs` serves the game *and* proxies
`/v1/*` to the model on the same origin, which sidesteps the problem without touching any
LM Studio settings.

You can still open `index.html` straight off disk, but then you must enable LM Studio's
CORS toggle yourself.

To point at a different backend:

```bash
LLM_URL=http://localhost:8000 node server.mjs
```

The model is auto-detected from `/v1/models` (embedding models are skipped). Override the
URL, model, or API key with the ⚙ button in the app; settings persist in `localStorage`.

## How it plays

Press Enter on the title screen. **Case File** (left) holds the facts the suspect can never
contradict. **Interrogation** (centre) is free-text chat. **Evidence Board** (right) holds
what you can put in front of him.

Elias Nunn opens with a clean alibi and will hold it against vague questions. Presenting
evidence that contradicts him forces a retreat — a correction, a new partial lie — and
raises the **Pressure** meter. Two evidence items start off-board and arrive from forensics
as pressure builds, so the case opens up as you push.

Present all three of the case-critical items and he has nowhere left to stand: the
character is instructed to break and give up the truth in pieces.

**Accuse** ends the run. A correct verdict only sticks if you actually put the proving
evidence in front of him *and* applied enough pressure — naming the right suspect on a thin
file gets the case thrown back at you. The results screen grades the run from **S** down to
**F** on whether the charge held and how few questions it took.

Click the chat log to skip the typewriter. **SFX** mutes; **CFG** opens the LLM settings.

## Swapping in a new case

Everything scenario-specific lives in [`js/case.js`](js/case.js) — victim, scene, timeline,
public facts, the suspect's personality and alibi, the hidden truth, the evidence list, and
the win condition. Rewrite that one object and the rest of the game adapts. No other file
needs to change.

Evidence entries support two unlock modes:

```js
available: true                        // on the board from the start
unlock: { pressure: 30 }               // arrives once pressure hits 30
unlock: { afterPresenting: "some-id" } // arrives after another item lands
```

`breakingPoint` lists the evidence that corners the suspect into confessing.
`conviction.requires` lists what a verdict actually needs to hold up.

## How the AI works

Each turn sends a freshly built system prompt ([`js/api.js`](js/api.js)) containing the
public facts, the character, the hidden truth, every piece of evidence already presented,
and a stance line derived from current pressure. The model only ever speaks as the
character — the solution object is never exposed to the player directly.

The character also appends a hidden control line:

```
[[TELL composure=rattled pressure=+12]]
```

This is stripped before display and drives the meter and the status chip. Presented
evidence sets a floor on the pressure gain, so a stubborn model can't stall the game.

### Note on reasoning models

Reasoning models spend their token budget thinking before writing dialogue, and left alone
they will spend *all* of it. On `gemma-4-12b-qat` a turn was observed burning the entire
2,500-token budget drafting and re-drafting the same three sentences ten times over, then
returning empty content — `reasoning_content` full, `content` blank.

Two things guard against it. The system prompt opens by forbidding deliberation outright,
which was enough to turn that failing turn into a clean reply. If a turn still comes back
empty, the client retries once with a blunt "stop deliberating" system message and a lower
temperature rather than a bigger budget — more room only buys a longer spiral.

Turns on a local 12B model take 30s–2½min. The typing indicator counts the seconds so a
slow turn never looks like a hung one.

## If the suspect won't answer

The game checks the connection on load and says so in the chat panel if something is
wrong, so most problems announce themselves before you ask anything.

| Symptom | Cause |
|---|---|
| "Opened straight from disk" | You double-clicked `index.html`. Run `node server.mjs` and use <http://localhost:5173>. |
| "Can't reach the model" | LM Studio's server isn't running, or it's on a different port. |
| "No chat model loaded" | Only an embedding model is loaded in LM Studio. |
| "Spent its whole budget thinking" | The model deliberated instead of answering, twice. Use a smaller or non-reasoning model. |
| It just sits there | It's working. A turn takes 30s–2½min on a local 12B model — the bubble shows a live elapsed counter. |

Nothing is ever spent on a failed turn: the question is rolled back and any evidence you
presented returns to the board, so you can retry.

## Files

| File | Purpose |
|---|---|
| `index.html` | Title screen, three-panel layout, modals |
| `css/styles.css` | All styling — bevels, CRT overlay, pixel type |
| `js/case.js` | The case — swap this to make a new one |
| `js/sprite.js` | The suspect's face, drawn as rectangles on a 32x32 grid |
| `js/audio.js` | WebAudio chiptune blips |
| `js/api.js` | LLM client and system prompt builder |
| `js/game.js` | State, rendering, pressure, unlocks, win/lose |
| `server.mjs` | Static server + same-origin LLM proxy |
| `fonts/` | Press Start 2P (SIL Open Font License) |

### The look

Three rules keep it consistent: no rounded corners, no gradients, no soft shadows. Depth is
a hard 3px bevel — light on the top-left, black on the bottom-right, inverted when a button
is pressed. Animations use `steps()` so nothing eases.

The portrait has no art asset. `js/sprite.js` draws it as filled rectangles on a 32x32 grid
and rebuilds it every frame, so the brows, mouth, eyes and sweat can be swapped for the
current mood. A case can override the palette with a `suspect.sprite` object.

## Not built yet

The stretch goals from the brief: multiple cross-referencing suspects, AI-generated cases,
and a scored player notebook.
