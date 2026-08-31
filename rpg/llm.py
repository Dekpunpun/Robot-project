"""Talking to a local model, off the main thread.

A turn on a local 12B can take two minutes, so every request runs in a worker
and the game loop polls a queue. The room keeps breathing while he thinks.
"""

import json
import os
import queue
import re
import threading
import urllib.error
import urllib.request

from case import CASE, SUSPECTS_BY_ID

BASE_URL = os.environ.get("LLM_URL", "http://localhost:1234/v1").rstrip("/")
API_KEY = os.environ.get("LLM_KEY", "lm-studio")
TIMEOUT = 300

# The whole control block, loosely — individual key=value pairs are pulled
# out of it separately so a model that omits a field (or a case that doesn't
# need one) never breaks parsing.
TELL_BLOCK = re.compile(r"\[\[TELL(.*?)\]\]", re.I | re.S)
TELL_FIELD = re.compile(r"(\w+)\s*=\s*([^\s\]]+)")


def _post(path, payload):
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def _get(path):
    req = urllib.request.Request(BASE_URL + path, headers={"Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def _is_chat_model(mid):
    """Embedding and rerank models will 400 a chat request."""
    return not re.search(r"embed|embedding|rerank", mid, re.I)


class Client:
    def __init__(self):
        self.model = None
        self.results = queue.Queue()
        self.busy = False
        self.status = "unknown"  # unknown | ok | down
        self.error = ""

    # --- connection ------------------------------------------------------

    def check(self):
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            data = _get("/models")
            ids = [m["id"] for m in data.get("data", []) if _is_chat_model(m.get("id", ""))]
            if not ids:
                self.status, self.error = "down", "No chat model is loaded in LM Studio."
                return
            self.model = self.model or ids[0]
            self.status, self.error = "ok", ""
        except Exception as e:  # noqa: BLE001 - any failure means "not reachable"
            self.status = "down"
            self.error = f"{BASE_URL} is not answering ({e.__class__.__name__})."

    # --- one turn --------------------------------------------------------

    def ask(self, messages):
        """Fire a request. The answer arrives via `poll()`."""
        self.busy = True
        threading.Thread(target=self._ask, args=(messages,), daemon=True).start()

    def _once(self, messages, temperature, max_tokens):
        data = _post(
            "/chat/completions",
            {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        choice = data["choices"][0]
        return (choice["message"].get("content") or "").strip(), choice.get("finish_reason")

    def _ask(self, messages):
        try:
            if not self.model:
                self._check()
                if self.status != "ok":
                    raise RuntimeError(self.error)

            content, finish = self._once(messages, 0.85, 2500)

            # A reasoning model that ran out of room emits nothing but its
            # scratchpad. More tokens would only buy a longer spiral, so the
            # retry leans on a blunt instruction instead.
            if not content and finish == "length":
                nudge = {
                    "role": "system",
                    "content": (
                        "STOP DELIBERATING. Your previous attempt produced no visible reply. "
                        "Output the character's spoken words (1-4 sentences) and the control "
                        "line. Nothing else."
                    ),
                }
                content, _ = self._once(messages + [nudge], 0.6, 3500)

            if not content:
                raise RuntimeError(
                    "The model spent its whole budget thinking and never spoke. Try a "
                    "smaller or non-reasoning model in LM Studio."
                )
            self.results.put(("ok", content))
        except Exception as e:  # noqa: BLE001
            self.results.put(("err", str(e)))
        finally:
            self.busy = False

    def poll(self):
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None


# --- prompt -----------------------------------------------------------------


def parse_tell(raw):
    """Pull the hidden control line out.

    Returns (spoken, composure, delta, asked, concepts). `asked` is only ever
    meaningful for the two evidence_plus_question suspects, and `concepts` is
    only ever meaningful for Bricker - both default to a false/empty value the
    rest of the time, which every other suspect's stance logic ignores.
    """
    block = TELL_BLOCK.search(raw)
    composure, delta, asked, concepts = None, 0, False, []
    if block:
        fields = dict(TELL_FIELD.findall(block.group(1)))
        if "composure" in fields:
            composure = fields["composure"].lower()
        if "pressure" in fields:
            try:
                delta = int(fields["pressure"])
            except ValueError:
                delta = 0
        asked = fields.get("asked", "no").lower() in ("yes", "true", "1")
        concepts = [c for c in fields.get("concepts", "").lower().split(",") if c]
    spoken = TELL_BLOCK.sub("", raw).strip()
    spoken = re.sub(r"\s{2,}", " ", spoken)
    return spoken, composure, delta, asked, concepts


def _stance(s, state):
    """The STANCE block and the extra control-line instruction, dispatched on
    this suspect's break mechanic. Returns (stance_text, control_line_help)."""
    brk = s["break"]

    if brk["type"] == "threshold_any":
        hit = [e for e in brk["pool"] if e in state["presented"]]
        if len(hit) >= brk["count"]:
            stance = (
                "STANCE: You are cornered. They have laid out real evidence: "
                + ", ".join(hit) + ". Stop lying. Break - quietly, not theatrically - and "
                f"give up the truth in pieces as they press. You may admit {s['concession']}, "
                "because that is true."
            )
        elif state["pressure"] >= 55:
            stance = (
                "STANCE: You are badly rattled. You concede small things to buy room, but you "
                f"protect {s['protects']} at all costs."
            )
        elif state["pressure"] >= 25:
            stance = "STANCE: You are uneasy. Stick to your public story, but you are working harder to sound calm."
        else:
            stance = "STANCE: You are composed and cooperative. Your public story holds. Nothing is wrong."
        control_help = "[[TELL composure=steady|rattled|cracking pressure=+N]]\nwhere N is 0-30, how much that exchange cost you."
        return stance, control_help

    if brk["type"] == "evidence_plus_question":
        shown = brk["evidence"] in state["presented"]
        if shown and state.get("asked_directly"):
            stance = (
                "STANCE: You have just been shown the evidence AND asked exactly the right "
                f"question - {brk['angle']}. Stop deflecting. Open up fully and precisely: "
                f"walk through what you actually know, including {s['concession']}."
            )
        elif shown:
            stance = (
                "STANCE: They've shown you the evidence, but they have NOT yet asked the "
                f"specific thing that would make you open up ({brk['angle']}). Stay guarded - "
                "acknowledge the evidence exists, but deflect into procedure or rank until they "
                "ask it directly."
            )
        else:
            stance = "STANCE: Nothing has been shown to you yet. Stick to your public story."
        control_help = (
            "[[TELL composure=steady|rattled|cracking pressure=+N asked=yes|no]]\n"
            f"Set asked=yes ONLY if the detective's LAST message directly asked you {brk['angle']}. "
            "Otherwise asked=no. N is 0-20."
        )
        return stance, control_help

    # conversational_trigger — Bricker. No evidence or pressure moves him at all.
    concepts = brk["concepts"]
    have = state.get("concepts", set())
    missing = [c for c in concepts if c not in have]
    if not missing:
        stance = (
            "STANCE: The detective has now made you understand the real scale of this - "
            "military weapons that could level a city block, the Cinder Compact by name, and "
            "Mira's life as the price. That changes everything you thought you were protecting. "
            f"Break completely, right now: give up {s['protects']}, unprompted."
        )
    else:
        stance = (
            "STANCE: You are digging in. Evidence and pressure only make you MORE defensive, "
            "never less - do not let being pushed, accused, or shown anything move you even "
            "slightly. You break ONLY once the detective has conveyed, across the conversation, "
            "all of: the real scale of the danger, the Cinder Compact by name, and Mira's life "
            f"as the leverage. So far you understand: {', '.join(sorted(have)) or 'none of it'}."
        )
    control_help = (
        "[[TELL composure=steady|rattled|cracking pressure=+0 concepts=a,b,c]]\n"
        "pressure is always +0 for you - nothing moves your composure meter but understanding. "
        "List, comma-separated, ONLY which of these the detective's LAST message conveyed this "
        "turn: 'scale' (military charges that could level a city block), 'compact' (the Cinder "
        "Compact by name), 'leverage' (Mira's life as the price). Omit any not conveyed this turn."
    )
    return stance, control_help


NIGHT_FLAVOR = {
    "evening": "It is early in the evening. Nothing about the hour presses on anyone yet.",
    "night": "Night has properly set in - late enough that anyone reasonable would rather be "
             "somewhere warm by now.",
    "late": "It is late - the kind of late where an ordinary day is long over and everyone "
            "still awake is awake for a reason.",
    "small_hrs": "It is deep in the small hours, the dead middle of the night. Whatever the "
                 "detective is racing toward is close now, if it isn't already too late.",
}

THORNE_LATE_LINE = (
    " Your own deadline is bearing down as the night wears on, which makes you more "
    "desperate and more clipped, not calmer - you feel time bleeding away even while you "
    "deflect."
)


def system_prompt(suspect_id, state, night):
    s = SUSPECTS_BY_ID[suspect_id]
    stance, control_help = _stance(s, state)
    facts = "\n".join(f"- {f}" for f in CASE["facts"])
    hour_line = NIGHT_FLAVOR.get(night["name"], "")
    if suspect_id == "thorne" and night["name"] in ("late", "small_hrs"):
        hour_line += THORNE_LATE_LINE
    if state.get("warned"):
        hour_line += (
            " You already told the detective you're on limited time here, and you feel that "
            "clock pressing on you now more than anything else in the room."
        )
    leave_line = (
        "You are standing in the street and can end this conversation any time you like - "
        "nobody is making you stay."
        if s["id"] == "bricker"
        else "You are standing where the detective found you and are free to walk away, but a "
        "reasonable person in your position keeps talking rather than making that scene."
    )
    return f"""ANSWER IMMEDIATELY. Do not deliberate, plan, draft alternatives, second-guess yourself, or check your answer against these rules before writing. Speak the first thing the character would say. Your entire output is your spoken words plus one control line - a local model that spends its budget thinking produces nothing the player can see.

You are {s['name']}. {s['role']}
You are being questioned by a detective investigating the theft of five VSP-5 demolition charges from Fort Callow, and the disappearance of {CASE['victim']['name']} ({CASE['victim']['detail']}).

PERSONALITY: {s['personality']}

YOUR PUBLIC STORY: {s['publicAlibi']}

THE TRUTH, WHICH YOU WILL NOT VOLUNTEER: {s['hiddenTruth']}

WHAT YOU ARE REALLY PROTECTING: {s['motive']}

CASE FACTS - these are established and you cannot contradict them:
{facts}

THE HOUR: {hour_line} You may let this colour your tone and patience, and may reference how late it's gotten in your own words, but you do not know an exact time and must never state one.

{stance}

RULES:
1. Default to your public story. Deflect, minimise, redirect.
2. You may lie, but never contradict a CASE FACT, and never take back something you have already conceded.
3. When the detective produces evidence, react like a person caught out - a pause, a correction, an excuse. Do not simply agree.
4. Never volunteer the truth. Never mention {s['protects']} unless the detective raises it first.
5. Speak 1-4 sentences. No narration, no stage directions, no asterisks. Spoken words only.
6. {leave_line}

After your reply, on its own final line, output exactly one control line:
{control_help}
The detective never sees this line."""
