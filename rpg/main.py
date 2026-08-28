"""The Vesper Manifest — a walking detective RPG.

    python3 rpg/main.py

Move with WASD or the arrow keys, E to look at things, TAB for the case file.
Four people know something. Only one of them did it.
"""

import os
import sys
import traceback

import pygame

import art
import llm
import sfx
import ui
from case import CASE, EVIDENCE_BY_ID, SUSPECTS_BY_ID
from entities import NPC, Player
from settings import *
from world import MAP_H, MAP_W, World

TITLE_SCREEN, PLAYING, CASEFILE, TALKING, ACCUSE, ENDING = range(6)

# Set LE_DEBUG=1 to have the game dump frames and a log of what it did.
# There is no way to see the player's real screen from here, so when
# something only shows up on a real display, the game has to report on
# itself instead of being screenshotted.
DEBUG = os.environ.get("LE_DEBUG") == "1"
DEBUG_DIR = os.environ.get("LE_DEBUG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug"))


def _debug_log(msg):
    if not DEBUG:
        return
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, "debug.log"), "a") as f:
        f.write(msg + "\n")


class Game:
    def __init__(self):
        pygame.init()
        sfx.init()
        self.screen = pygame.display.set_mode((SCREEN_W * SCALE, SCREEN_H * SCALE))
        pygame.display.set_caption(TITLE)
        self.scene = pygame.Surface((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.tick = 0
        self.fullscreen = False

        self.world = World()
        self.player = self._spawn_player()

        self.npcs = {}
        for sid, spot in self.world.npc_spots.items():
            calm, broken = art.NPC_ART[SUSPECTS_BY_ID[sid]["sprite"]]
            self.npcs[sid] = NPC(sid, spot["x"], spot["y"], calm, broken)
            self.world.blockers.append(spot["blocker"])
            self.world.interactables.append(
                {
                    "rect": spot["rect"],
                    "title": SUSPECTS_BY_ID[sid]["name"],
                    "body": None,
                    "evidence": None,
                    "npc": True,
                    "suspect_id": sid,
                }
            )

        self.box = ui.DialogBox()
        self.toast = ui.Toast()
        self.lights = {}

        self.ai = llm.Client()
        self.ai.check()

        if DEBUG:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            drivers = {
                k: os.environ.get(k)
                for k in ("SDL_VIDEODRIVER", "SDL_AUDIODRIVER", "SDL_RENDER_DRIVER")
            }
            _debug_log(
                f"--- start --- window={self.screen.get_size()} "
                f"internal={self.scene.get_size()} scale={SCALE} drivers={drivers} "
                f"pygame={pygame.version.ver} sdl={pygame.version.SDL}"
            )

        self.scanlines = self.build_scanlines()
        self.state = TITLE_SCREEN
        self.reset_run()

    def _spawn_player(self):
        tx, ty = CASE["meta"]["spawn"]
        return Player((tx + 0.5) * TILE, ty * TILE)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        names = {TITLE_SCREEN: "TITLE_SCREEN", PLAYING: "PLAYING", CASEFILE: "CASEFILE",
                  TALKING: "TALKING", ACCUSE: "ACCUSE", ENDING: "ENDING"}
        if DEBUG and getattr(self, "_state", None) != value:
            _debug_log(f"[{self.tick}] state -> {names.get(value, value)}")
        self._state = value

    # -- run state -----------------------------------------------------------

    def reset_run(self):
        self.found = []  # evidence ids picked up in the world (or unlocked by dialogue)
        self.convo = {
            sid: {
                "presented": [],       # evidence ids put to this suspect
                "pressure": 0.0,
                "composure": "steady",
                "turns": 0,
                "history": [],         # chat messages for the model
                "log": [],             # (speaker, text) - first-time-talking marker
                "concepts": set(),     # Bricker only: which of the 3 ideas have landed
                "asked_directly": False,  # Doss/Ashworth only: was the right question ever asked
            }
            for sid in SUSPECTS_BY_ID
        }
        self.active_suspect = None
        self.talk_mode = "read"  # read | input | evidence
        self.typed = ""
        self.ev_index = 0
        self.waiting_since = None
        self.ending = None
        self.casefile_page = 0
        self.accuse_index = 0
        self.accuse_confirm = None
        self.accuse_return = PLAYING
        for npc in self.npcs.values():
            npc.mood = "steady"
            npc.shake = 0.0

    # -- helpers -------------------------------------------------------------

    @property
    def camera(self):
        cx = int(self.player.x) - SCREEN_W // 2
        cy = int(self.player.y) - SCREEN_H // 2
        cx = max(0, min(cx, MAP_W * TILE - SCREEN_W))
        cy = max(0, min(cy, MAP_H * TILE - SCREEN_H))
        return cx, cy

    def light(self, radius):
        if radius not in self.lights:
            self.lights[radius] = art.make_light(radius)
        return self.lights[radius]

    def available_evidence(self):
        return [EVIDENCE_BY_ID[e] for e in self.found]

    # -- interaction ---------------------------------------------------------

    def interact(self):
        target = self.world.interactable_near((self.player.x, self.player.y - 8))
        if not target:
            return
        if target.get("npc"):
            self.begin_interview(target["suspect_id"])
            return

        eid = target.get("evidence")
        if eid and eid not in self.found:
            ev = EVIDENCE_BY_ID[eid]
            need = ev.get("requires")
            if need and need not in self.found:
                sfx.play("close")
                self.box.open(ev["locked_text"], target["title"])
                return
            self.found.append(eid)
            sfx.play("pickup")
            self.box.open(
                ev["found_text"],
                target["title"],
                on_close=lambda n=ev["name"]: self.toast.show(f"ADDED: {n.upper()}"),
            )
            return

        sfx.play("open")
        body = target["body"] or "Nothing more here."
        if eid:
            body = f"{EVIDENCE_BY_ID[eid]['name']} - already in your file."
        self.box.open(body, target["title"])

    # -- the interview -------------------------------------------------------

    def begin_interview(self, sid):
        if self.ai.status == "down":
            sfx.play("error")
            self.box.open(
                "They look at you and say nothing. " + self.ai.error +
                " Start LM Studio, load a chat model, and try again.",
                "No connection",
            )
            return
        sfx.play("open")
        self.state = TALKING
        self.active_suspect = sid
        self.talk_mode = "read"
        c = self.convo[sid]
        if not c["log"]:
            self.say_suspect(sid, SUSPECTS_BY_ID[sid]["opener"])

    def say_suspect(self, sid, line):
        self.convo[sid]["log"].append(("suspect", line))
        self.box.open(line, SUSPECTS_BY_ID[sid]["name"])

    def send(self, user_text, evidence=None):
        sid = self.active_suspect
        c = self.convo[sid]
        c["turns"] += 1
        c["history"].append({"role": "user", "content": user_text})
        c["log"].append(("you", user_text))
        messages = [{"role": "system", "content": llm.system_prompt(sid, c)}]
        messages += c["history"]
        self.ai.ask(messages)
        self.waiting_since = pygame.time.get_ticks()
        self.talk_mode = "read"
        self.box.active = False
        if evidence:
            sfx.play("present")
        else:
            sfx.play("select")

    def present(self, ev):
        c = self.convo[self.active_suspect]
        if ev["id"] in c["presented"]:
            self.toast.show("ALREADY PRESENTED")
            sfx.play("error")
            return
        c["presented"].append(ev["id"])
        self.send(
            f"[EVIDENCE PRESENTED: {ev['name']}] {ev['summary']} "
            f"This contradicts: {ev['contradicts']}",
            evidence=ev,
        )

    def receive(self, kind, payload):
        sid = self.active_suspect
        c = self.convo[sid]
        self.waiting_since = None
        if kind == "err":
            sfx.play("error")
            c["history"].pop()  # the question never landed; let them retry it
            c["turns"] -= 1
            c["log"].append(("system", payload))
            self.box.open(payload, "Connection")
            return

        spoken, composure, delta, asked, concepts = llm.parse_tell(payload)
        c["history"].append({"role": "assistant", "content": payload})

        s = SUSPECTS_BY_ID[sid]
        brk = s["break"]
        npc = self.npcs[sid]

        before = c["pressure"]
        c["pressure"] = max(0.0, min(100.0, c["pressure"] + delta))
        # Hard evidence guarantees progress even if the model undersells it.
        floor = min(95.0, float(sum(EVIDENCE_BY_ID[e]["pressure"] for e in c["presented"])))
        c["pressure"] = max(c["pressure"], floor)

        if brk["type"] == "evidence_plus_question" and asked:
            c["asked_directly"] = True

        if brk["type"] == "conversational_trigger":
            c["concepts"] |= set(concepts)
            # Deterministic backstop: also scan what the PLAYER just typed, so
            # a model that forgets to self-report a concept it clearly heard
            # can't stall a deserving turn. Never scans the model's own reply.
            user_text = (c["history"][-2]["content"] if len(c["history"]) >= 2 else "").lower()
            for concept, keywords in brk["keyword_backstop"].items():
                if any(k in user_text for k in keywords):
                    c["concepts"].add(concept)
            complete = c["concepts"] >= set(brk["concepts"])
            if complete and "bricker-account" not in self.found:
                self.found.append("bricker-account")
                self.toast.show("ADDED: BRICKER'S ACCOUNT")
            npc.mood = "cracking" if complete else "steady"
        else:
            if composure in ("steady", "rattled", "cracking"):
                c["composure"] = composure
            else:
                c["composure"] = "cracking" if c["pressure"] >= 70 else "rattled" if c["pressure"] >= 35 else "steady"
            npc.mood = c["composure"]

        if c["pressure"] > before:
            npc.hit()
            sfx.play("hurt")
        self.say_suspect(sid, spoken)

    def resolve(self, accused_id):
        culprit = CASE["conviction"]["culprit"]
        strong = CASE["conviction"]["strong"]
        c = self.convo[culprit]

        if accused_id != culprit:
            shape = "wrong_suspect"
        else:
            hit = sum(1 for e in strong["pool"] if e in c["presented"])
            strong_case = hit >= strong["requires_count"] and c["pressure"] >= strong["minPressure"]
            shape = "correct_strong" if strong_case else "correct_thin"

        grade = caption = None
        if shape == "correct_strong":
            turns = c["turns"]
            if turns <= 10:
                grade, caption = "S", "SURGICAL"
            elif turns <= 16:
                grade, caption = "A", "SOLID POLICE WORK"
            elif turns <= 24:
                grade, caption = "B", "GOT THERE IN THE END"
            else:
                grade, caption = "C", "A LONG NIGHT"

        ending_def = CASE["endings"][shape]
        self.ending = {
            "shape": shape,
            "accused": accused_id,
            "grade": grade,
            "caption": caption or ending_def["caption"],
            "prose": ending_def["prose"],
        }
        self.state = ENDING
        sfx.play("win" if shape == "correct_strong" else "lose")

    # -- input ---------------------------------------------------------------

    def on_key(self, e):
        if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return
        if e.key == pygame.K_m:
            if self.state != TALKING or self.talk_mode != "input":
                self.toast.show("SOUND OFF" if sfx.toggle() else "SOUND ON")
                return

        if self.state == TITLE_SCREEN:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                sfx.play("start")
                self.state = PLAYING
                self.box.open(CASE["meta"]["opening"], "Detective")
            elif e.key == pygame.K_ESCAPE:
                self.quit()
            return

        if self.state == ENDING:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.reset_run()
                self.player = self._spawn_player()
                self.state = TITLE_SCREEN
            elif e.key == pygame.K_ESCAPE:
                self.quit()
            return

        if self.state == ACCUSE:
            self.on_key_accuse(e)
            return

        if self.state == CASEFILE:
            if e.key in (pygame.K_TAB, pygame.K_ESCAPE):
                sfx.play("close")
                self.state = PLAYING
            elif e.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT):
                self.casefile_page = min(len(self.found), self.casefile_page + 1)
                sfx.play("move")
            elif e.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT):
                self.casefile_page = max(0, self.casefile_page - 1)
                sfx.play("move")
            elif e.key == pygame.K_a:
                self.open_accuse(CASEFILE)
            return

        if self.state == TALKING:
            self.on_key_talking(e)
            return

        # -- walking around
        if self.box.active:
            if e.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.box.advance()
            return
        if e.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.interact()
        elif e.key == pygame.K_TAB:
            sfx.play("open")
            self.casefile_page = 0
            self.state = CASEFILE
        elif e.key == pygame.K_ESCAPE:
            self.quit()

    def open_accuse(self, return_to):
        self.accuse_index = 0
        self.accuse_confirm = None
        self.accuse_return = return_to
        self.state = ACCUSE
        sfx.play("select")

    def on_key_accuse(self, e):
        suspects = CASE["suspects"]
        if self.accuse_confirm is None:
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.accuse_index = (self.accuse_index + 1) % len(suspects)
                sfx.play("move")
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.accuse_index = (self.accuse_index - 1) % len(suspects)
                sfx.play("move")
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.accuse_confirm = suspects[self.accuse_index]["id"]
                sfx.play("select")
            elif e.key in (pygame.K_TAB, pygame.K_ESCAPE):
                sfx.play("close")
                self.state = self.accuse_return
            return

        if e.key == pygame.K_y:
            self.resolve(self.accuse_confirm)
        elif e.key in (pygame.K_n, pygame.K_ESCAPE):
            self.accuse_confirm = None
            sfx.play("close")

    def on_key_talking(self, e):
        if self.talk_mode == "input":
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                q = self.typed.strip()
                if q and not self.ai.busy:
                    self.typed = ""
                    self.send(q)
                return
            if e.key == pygame.K_BACKSPACE:
                self.typed = self.typed[:-1]
                return
            if e.key == pygame.K_ESCAPE:
                self.talk_mode = "read"
                sfx.play("close")
            return

        if self.talk_mode == "evidence":
            items = self.available_evidence()
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.ev_index = (self.ev_index + 1) % max(1, len(items))
                sfx.play("move")
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.ev_index = (self.ev_index - 1) % max(1, len(items))
                sfx.play("move")
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and items and not self.ai.busy:
                self.present(items[self.ev_index])
            elif e.key in (pygame.K_TAB, pygame.K_ESCAPE):
                self.talk_mode = "read"
                sfx.play("close")
            return

        # read mode
        if self.box.active and self.box.advance():
            return
        if self.ai.busy:
            return
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE):
            self.talk_mode = "input"
            sfx.play("open")
        elif e.key == pygame.K_TAB:
            if self.found:
                self.ev_index = min(self.ev_index, len(self.found) - 1)
                self.talk_mode = "evidence"
                sfx.play("open")
            else:
                self.toast.show("NOTHING IN THE FILE YET")
                sfx.play("error")
        elif e.key == pygame.K_a:
            self.open_accuse(TALKING)
        elif e.key == pygame.K_ESCAPE:
            self.state = PLAYING
            self.box.active = False
            sfx.play("close")

    def on_text(self, e):
        if self.state == TALKING and self.talk_mode == "input" and len(self.typed) < 90:
            self.typed += e.text

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else 0
        self.screen = pygame.display.set_mode((SCREEN_W * SCALE, SCREEN_H * SCALE), flags)
        self.scanlines = self.build_scanlines()

    def quit(self):
        pygame.quit()
        sys.exit(0)

    # -- update --------------------------------------------------------------

    def update(self, dt):
        self.tick += 1
        self.box.update(dt)
        self.toast.update(dt)
        for npc in self.npcs.values():
            npc.update(dt)

        result = self.ai.poll()
        if result:
            self.receive(*result)

        if self.state != PLAYING or self.box.active:
            self.player.moving = False
            return

        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        was = int(self.player.frame)
        self.player.update(dt, dx, dy, self.world, running)
        if self.player.moving and int(self.player.frame) != was and int(self.player.frame) % 2 == 1:
            sfx.play("step")

    # -- draw ----------------------------------------------------------------

    def draw_world(self):
        cam = self.camera
        s = self.scene
        s.blit(self.world.floor, (-cam[0], -cam[1]))

        view = pygame.Rect(cam[0] - 64, cam[1] - 64, SCREEN_W + 128, SCREEN_H + 128)
        drawables = [
            (sort_y, surf, x, y)
            for surf, x, y, sort_y in self.world.objects
            if view.collidepoint(x + surf.get_width() // 2, y + surf.get_height() // 2)
        ]
        drawables.sort(key=lambda d: d[0])

        entities = [(self.player.sort_y, "player", None)]
        entities += [(npc.sort_y, "npc", npc) for npc in self.npcs.values()]
        merged = sorted(
            [(d[0], "obj", d) for d in drawables] + entities,
            key=lambda m: m[0],
        )
        for _, kind, data in merged:
            if kind == "obj":
                _, surf, x, y = data
                s.blit(surf, (x - cam[0], y - cam[1]))
            elif kind == "player":
                self.player.draw(s, cam)
            else:
                data.draw(s, cam, self.tick)

        # Night, punched through by every lamp in range.
        dark = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dark.fill((10, 12, 30, 132))
        for lx, ly, r in self.world.lights:
            if abs(lx - cam[0] - SCREEN_W // 2) > SCREEN_W // 2 + r:
                continue
            if abs(ly - cam[1] - SCREEN_H // 2) > SCREEN_H // 2 + r:
                continue
            dark.blit(self.light(r), (lx - r - cam[0], ly - r - cam[1]), special_flags=pygame.BLEND_RGBA_SUB)
        dark.blit(
            self.light(40),
            (int(self.player.x) - 40 - cam[0], int(self.player.y) - 48 - cam[1]),
            special_flags=pygame.BLEND_RGBA_SUB,
        )
        s.blit(dark, (0, 0))

    def draw_hud(self):
        s = self.scene
        found, total = len(self.found), len(CASE["evidence"])
        ui.panel(s, (6, 6, 96, 14), UI_BG, UI_LINE)
        ui.text(s, f"EVIDENCE {found}/{total}", 12, 9, ACCENT if found < total else GREEN)

        if self.state == PLAYING and not self.box.active:
            t = self.world.interactable_near((self.player.x, self.player.y - 8))
            if t:
                cam = self.camera
                ui.prompt(s, "E  LOOK" if not t.get("npc") else "E  TALK",
                          int(t["rect"].centerx) - cam[0], int(t["rect"].top) - cam[1] - 18)
            ui.text(s, "TAB  CASE FILE", 6, SCREEN_H - 12, UI_FAINT)

    def draw_talk(self):
        s = self.scene
        sid = self.active_suspect
        suspect = SUSPECTS_BY_ID[sid]
        c = self.convo[sid]
        name = suspect["name"].upper()
        ui.panel(s, (6, 6, SCREEN_W - 12, 22), UI_BG, UI_LINE)
        ui.text(s, name, 12, 10, UI_TEXT)
        label = {"steady": "COMPOSED", "rattled": "RATTLED", "cracking": "CRACKING"}[c["composure"]]
        col = {"steady": UI_DIM, "rattled": ACCENT, "cracking": DANGER}[c["composure"]]
        if c["composure"] == "cracking" and (self.tick // 16) % 2 == 0:
            col = UI_TEXT
        ui.text(s, label, 12 + ui.text_w(name) + 12, 10, col)
        ui.meter(s, SCREEN_W - 100, 11, c["pressure"])
        ui.text(s, f"{int(c['pressure']):3d}%", SCREEN_W - 30, 10, UI_DIM)

        if self.ai.busy:
            secs = (pygame.time.get_ticks() - (self.waiting_since or 0)) // 1000
            dots = "." * (1 + (self.tick // 24) % 3)
            ui.panel(s, (12, SCREEN_H - 66, SCREEN_W - 24, 58))
            ui.text(s, f"THINKING{dots}", 20, SCREEN_H - 46, UI_DIM)
            ui.text(s, f"{secs}s", 20, SCREEN_H - 32, UI_FAINT)
            return

        if self.talk_mode == "evidence":
            items = self.available_evidence()
            h = 22 + len(items) * 12
            ui.panel(s, (12, SCREEN_H - h - 8, SCREEN_W - 24, h))
            ui.text(s, "PRESENT WHAT?", 20, SCREEN_H - h + 0, ACCENT)
            for i, ev in enumerate(items):
                y = SCREEN_H - h + 16 + i * 12
                sel = i == self.ev_index
                done = ev["id"] in c["presented"]
                if sel:
                    pygame.draw.rect(s, UI_BG_2, (16, y - 2, SCREEN_W - 32, 12))
                    ui.text(s, ">", 18, y, ACCENT)
                ui.text(s, ev["name"][:34], 28, y, UI_FAINT if done else (UI_TEXT if sel else UI_DIM))
            ui.text(s, "ENTER PRESENT   TAB BACK", 20, SCREEN_H - 14, UI_FAINT)
            return

        if self.talk_mode == "input":
            ui.panel(s, (12, SCREEN_H - 40, SCREEN_W - 24, 32))
            caret = "_" if (self.tick // 16) % 2 == 0 else " "
            shown = self.typed[-40:]
            ui.text(s, "> " + shown + caret, 20, SCREEN_H - 32, UI_TEXT)
            ui.text(s, "ENTER ASK    ESC BACK", 20, SCREEN_H - 18, UI_FAINT)
            return

        self.box.draw(s, self.tick)
        if not self.box.active:
            ui.panel(s, (12, SCREEN_H - 30, SCREEN_W - 24, 22))
            hint = "ENTER ASK   TAB PRESENT   A ACCUSE   ESC LEAVE"
            ui.text(s, hint, 20, SCREEN_H - 23, UI_FAINT)

    def draw_accuse(self):
        s = self.scene
        s.fill(UI_BG)
        ui.panel(s, (8, 8, SCREEN_W - 16, SCREEN_H - 16), UI_BG, UI_LINE)
        suspects = CASE["suspects"]

        if self.accuse_confirm is None:
            ui.text(s, "WHO DID THIS?", 18, 16, ACCENT)
            y = 40
            for i, sp in enumerate(suspects):
                sel = i == self.accuse_index
                if sel:
                    pygame.draw.rect(s, UI_BG_2, (14, y - 3, SCREEN_W - 28, 30))
                    ui.text(s, ">", 18, y + 4, ACCENT)
                ui.text(s, sp["name"], 28, y, UI_TEXT if sel else UI_DIM)
                ui.text(s, sp["role"], 28, y + 12, UI_FAINT)
                y += 34
            ui.text(s, "ENTER ACCUSE   TAB BACK", 18, SCREEN_H - 20, UI_FAINT)
            return

        accused = SUSPECTS_BY_ID[self.accuse_confirm]
        ui.text(s, f"ACCUSE {accused['name'].upper()}?", 18, 16, DANGER)
        for i, line in enumerate(
            ui.wrap(
                "This is your one shot. Once you name someone, the case closes tonight, "
                "for better or worse.",
                SCREEN_W - 44,
            )
        ):
            ui.text(s, line, 18, 40 + i * 11, UI_DIM)
        ui.text(s, "Y  ACCUSE     N  NOT YET", 18, SCREEN_H - 20, ACCENT)

    def draw_casefile(self):
        s = self.scene
        s.fill(UI_BG)
        ui.panel(s, (8, 8, SCREEN_W - 16, SCREEN_H - 16), UI_BG, UI_LINE)
        if self.casefile_page == 0:
            ui.text(s, "CASE FILE - " + CASE["title"].upper(), 18, 16, ACCENT)
            y = 32
            ui.text(s, "VICTIM", 18, y, UI_DIM)
            y += 12
            for line in ui.wrap(f"{CASE['victim']['name']}. {CASE['victim']['detail']}", SCREEN_W - 44):
                ui.text(s, line, 18, y)
                y += 11
            y += 5
            ui.text(s, "SUSPECTS", 18, y, UI_DIM)
            y += 12
            for sp in CASE["suspects"]:
                ui.text(s, sp["name"], 18, y, UI_TEXT)
                y += 11
                ui.text(s, ui.wrap(sp["role"], SCREEN_W - 44)[0], 18, y, UI_FAINT)
                y += 11
        else:
            ev = EVIDENCE_BY_ID[self.found[self.casefile_page - 1]]
            ui.text(s, f"EXHIBIT {self.casefile_page}", 18, 16, ACCENT)
            ui.text(s, ev["name"].upper()[:36], 18, 32, UI_TEXT)
            y = 52
            for line in ui.wrap(ev["detail"], SCREEN_W - 44):
                ui.text(s, line, 18, y)
                y += 11
            y += 8
            ui.text(s, "CONTRADICTS", 18, y, UI_DIM)
            y += 12
            for line in ui.wrap(ev["contradicts"], SCREEN_W - 44):
                ui.text(s, line, 18, y, ACCENT)
                y += 11
            if any(ev["id"] in c["presented"] for c in self.convo.values()):
                ui.text(s, "PRESENTED", 18, SCREEN_H - 40, GREEN)
        ui.text(
            s,
            f"{self.casefile_page + 1}/{len(self.found) + 1}   ARROWS PAGE   A ACCUSE   TAB CLOSE",
            18,
            SCREEN_H - 24,
            UI_FAINT,
        )

    def draw_title(self):
        s = self.scene
        s.fill((12, 13, 26))
        for y in range(0, SCREEN_H, 2):
            pygame.draw.line(s, (16, 18, 34), (0, y), (SCREEN_W, y))
        big = ui.font(20)
        for i, word in enumerate(CASE["meta"]["title_lines"]):
            w = big.size(word)[0]
            x = (SCREEN_W - w) // 2
            y = 26 + i * 26
            s.blit(big.render(word, False, INK), (x + 3, y + 3))
            s.blit(big.render(word, False, ACCENT if i else UI_TEXT), (x, y))
        subtitle = CASE["meta"]["subtitle"]
        ui.text(s, subtitle, (SCREEN_W - ui.text_w(subtitle)) // 2, 84, UI_FAINT)

        frame = self.player.frames["down"][(self.tick // 14) % 4]
        big_sprite = pygame.transform.scale(frame, (frame.get_width() * 3, frame.get_height() * 3))
        s.blit(big_sprite, ((SCREEN_W - big_sprite.get_width()) // 2, 100))

        if (self.tick // 22) % 3 != 2:
            msg = "PRESS ENTER TO BEGIN"
            ui.text(s, msg, (SCREEN_W - ui.text_w(msg)) // 2, 186, ACCENT)
        foot = "WASD MOVE   E LOOK   TAB FILE   M SOUND"
        ui.text(s, foot, (SCREEN_W - ui.text_w(foot)) // 2, SCREEN_H - 18, UI_FAINT)

        dot = GREEN if self.ai.status == "ok" else DANGER if self.ai.status == "down" else ACCENT
        pygame.draw.rect(s, dot, (SCREEN_W - 14, 10, 5, 5))

    def draw_ending(self):
        s = self.scene
        s.fill(UI_BG)
        e = self.ending
        heads = {
            "correct_strong": ("CASE CLOSED", GREEN),
            "wrong_suspect": ("CASE GONE COLD", DANGER),
            "correct_thin": ("CASE CLOSED - HOLLOW", ACCENT),
        }
        head, head_col = heads[e["shape"]]
        big = ui.font(16)
        w = big.size(head)[0]
        s.blit(big.render(head, False, INK), ((SCREEN_W - w) // 2 + 2, 20))
        s.blit(big.render(head, False, head_col), ((SCREEN_W - w) // 2, 18))

        y = 46
        if e["grade"]:
            grade = ui.font(32)
            gw = grade.size(e["grade"])[0]
            ui.panel(s, ((SCREEN_W - gw) // 2 - 10, y, gw + 20, 44), (18, 16, 30), UI_LINE)
            s.blit(grade.render(e["grade"], False, ACCENT), ((SCREEN_W - gw) // 2, y + 6))
            y += 44
        ui.text(s, e["caption"], (SCREEN_W - ui.text_w(e["caption"])) // 2, y + 4, UI_TEXT)

        turns = sum(c["turns"] for c in self.convo.values())
        stat = f"{turns} QUESTIONS   {len(self.found)}/{len(CASE['evidence'])} FOUND"
        ui.text(s, stat, (SCREEN_W - ui.text_w(stat)) // 2, y + 20, UI_DIM)

        ty = y + 42
        for line in ui.wrap(e["prose"], SCREEN_W - 44):
            ui.text(s, line, 18, ty, UI_DIM)
            ty += 11
        ui.text(s, "ENTER  NEW CASE", 18, SCREEN_H - 20, ACCENT)

    def draw(self):
        if self.state == TITLE_SCREEN:
            self.draw_title()
        elif self.state == CASEFILE:
            self.draw_casefile()
        elif self.state == ACCUSE:
            self.draw_accuse()
        elif self.state == ENDING:
            self.draw_ending()
        else:
            self.draw_world()
            if self.state == TALKING:
                self.draw_talk()
            else:
                self.draw_hud()
                self.box.draw(self.scene, self.tick)
            self.toast.draw(self.scene)

        # `scene` inherits the real display's pixel format, which on this
        # Mac's window includes a genuine per-pixel alpha byte. Blitting any
        # SRCALPHA surface onto it (the darkness overlay, the title screen's
        # scaled-up sprite, anything drawn with `from_art`) leaves that alpha
        # near-zero across the blitted rect instead of the destination
        # staying opaque — a dummy/offscreen driver never composites the
        # window against anything so this was invisible in every headless
        # test, but a real macOS window honours that alpha for compositing,
        # so those areas turned see-through to whatever was behind the
        # window. Normalizing once here, right before the scene ever reaches
        # the screen, fixes every draw call that could hit this rather than
        # chasing it call site by call site. MAX is a plain per-channel
        # maximum, not alpha-blend math, so it reliably forces opacity back
        # to 255 without touching any RGB colour.
        self.scene.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MAX)

        if DEBUG and self.tick % 60 == 0:
            # Both surfaces, so a black window with a correct internal scene
            # points at the upscale/flip step rather than at drawing itself.
            pygame.image.save(self.scene, os.path.join(DEBUG_DIR, f"{self.tick:06d}_scene.png"))

        pygame.transform.scale(self.scene, self.screen.get_size(), self.screen)
        # Scanlines go on after the upscale, so they stay one screen pixel
        # thick however far the window is blown up.
        self.screen.blit(self.scanlines, (0, 0))

        if DEBUG and self.tick % 60 == 0:
            pygame.image.save(self.screen, os.path.join(DEBUG_DIR, f"{self.tick:06d}_screen.png"))
            _debug_log(f"[{self.tick}] dumped frame, state={self._state}")

        pygame.display.flip()

    def build_scanlines(self):
        w, h = self.screen.get_size()
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 3):
            pygame.draw.line(s, (0, 0, 0, 46), (0, y), (w, y))
        return s

    # -- loop ----------------------------------------------------------------

    def run(self):
        try:
            self._run()
        except Exception:
            # A crash mid-frame otherwise just vanishes when the game is
            # launched from Finder rather than a terminal.
            _debug_log(f"[{self.tick}] CRASH:\n{traceback.format_exc()}")
            raise

    def _run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit()
                elif e.type == pygame.KEYDOWN:
                    self.on_key(e)
                elif e.type == pygame.TEXTINPUT:
                    self.on_text(e)
            self.update(dt)
            self.draw()


def selftest():
    """Prove a packaged build works: boot, render, and check the font loaded.

    Frozen builds fail quietly — a missing data file falls back to a default
    font instead of crashing — so the check has to be explicit.
    """
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    g = Game()
    for _ in range(8):
        g.update(1 / 60)
        g.draw()
    g.state = PLAYING
    g.box.active = False
    for _ in range(4):
        g.update(1 / 60)
        g.draw()
    problems = []
    if not ui.pixel_font_loaded:
        problems.append(f"pixel font not found at {ui.FONT_PATH}")
    if len(g.world.objects) < 100:
        problems.append(f"world looks empty ({len(g.world.objects)} props)")
    if len(g.npcs) != len(CASE["suspects"]):
        problems.append(f"expected {len(CASE['suspects'])} suspects, found {len(g.npcs)}")
    if not sfx.ok:
        problems.append("audio device unavailable (harmless under a dummy driver)")
    out = sys.argv[sys.argv.index("--selftest") + 1] if len(sys.argv) > 2 else None
    if out:
        pygame.image.save(g.screen, out)
        print("wrote", out)
    print(f"props={len(g.world.objects)} npcs={len(g.npcs)} font={ui.pixel_font_loaded} audio={sfx.ok}")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if any("font" in p or "empty" in p or "suspects" in p for p in problems) else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    Game().run()
