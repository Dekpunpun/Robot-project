"""Panels, text and the dialogue box.

Everything is drawn at the internal 384x240 resolution, so a "1px" border here
becomes a chunky 3px border on screen. There are no rounded corners, no
gradients and no soft shadows anywhere in this file — depth is one light edge
and one dark edge, the way a 1988 menu did it.
"""

import pygame

from settings import *

FONT_PATH = asset("PressStart2P.ttf")

_fonts = {}
pixel_font_loaded = False


def font(size=8):
    """The pixel font, or a legible fallback if the file went missing.

    The fallback keeps the game playable, so a packaging mistake shows up as
    ugly text rather than a crash. `pixel_font_loaded` is what a build check
    should assert on.
    """
    global pixel_font_loaded
    if size not in _fonts:
        try:
            f = pygame.font.Font(FONT_PATH, size)
            pixel_font_loaded = True
        except (OSError, FileNotFoundError):
            f = pygame.font.Font(None, size + 4)
        _fonts[size] = f
    return _fonts[size]


def text(surf, s, x, y, colour=UI_TEXT, size=8, shadow=True):
    f = font(size)
    if shadow:
        surf.blit(f.render(s, False, INK), (x + 1, y + 1))
    surf.blit(f.render(s, False, colour), (x, y))
    return f.size(s)[0]


def text_w(s, size=8):
    return font(size).size(s)[0]


def wrap(s, width, size=8):
    """Greedy word wrap to a pixel width. Long words are broken."""
    f = font(size)
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if f.size(trial)[0] <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        while f.size(word)[0] > width:
            cut = len(word)
            while cut > 1 and f.size(word[:cut])[0] > width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        lines.append(line)
    return lines


def header(surf, s, x, y, colour=ACCENT, size=8):
    """Header text wearing a phosphor halo.

    A CRT running bright amber blooms into the pixels around each glyph. Four
    offset copies in a dim amber under the real text is enough to read as that
    bloom without turning the letters to mush.
    """
    f = font(size)
    halo = f.render(s, False, GLOW_AMBER)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surf.blit(halo, (x + dx, y + dy))
    surf.blit(f.render(s, False, colour), (x, y))
    return f.size(s)[0]


def terminal_frame(surf, label, tick, footer=None):
    """Full-screen terminal chrome: housing, keyline, a title bar with a live
    cursor, and an optional footer strip. The record screens all sit in this."""
    surf.fill(UI_BG)
    # Faint horizontal ruling, so empty areas still read as a screen.
    for y in range(0, SCREEN_H, 4):
        pygame.draw.line(surf, (26, 21, 18), (0, y), (SCREEN_W, y))
    pygame.draw.rect(surf, UI_LINE, (6, 6, SCREEN_W - 12, SCREEN_H - 12), 1)
    pygame.draw.rect(surf, UI_BG_2, (7, 7, SCREEN_W - 14, 13))
    pygame.draw.line(surf, UI_HI, (7, 20), (SCREEN_W - 8, 20))
    header(surf, label, 12, 9, ACCENT)
    if (tick // 20) % 2 == 0:
        pygame.draw.rect(surf, ACCENT, (SCREEN_W - 16, 10, 5, 7))
    if footer:
        pygame.draw.line(surf, UI_LINE, (7, SCREEN_H - 20), (SCREEN_W - 8, SCREEN_H - 20))
        text(surf, footer, 12, SCREEN_H - 16, UI_FAINT)


def caret(surf, x, y, tick, colour=ACCENT):
    """The blinking block cursor at the end of a typed line."""
    if (tick // 16) % 2 == 0:
        pygame.draw.rect(surf, colour, (x, y, 5, 8))


def panel(surf, rect, fill=UI_BG, light=UI_HI, dark=INK):
    """A sunk-and-lit box. Two edges lit, two in shadow, one black keyline."""
    x, y, w, h = rect
    pygame.draw.rect(surf, fill, rect)
    pygame.draw.line(surf, light, (x, y), (x + w - 1, y))
    pygame.draw.line(surf, light, (x, y), (x, y + h - 1))
    pygame.draw.line(surf, dark, (x, y + h - 1), (x + w - 1, y + h - 1))
    pygame.draw.line(surf, dark, (x + w - 1, y), (x + w - 1, y + h - 1))
    pygame.draw.rect(surf, INK, (x - 1, y - 1, w + 2, h + 2), 1)


def meter(surf, x, y, value, cells=16, cell_w=4, cell_h=7):
    """The pressure meter: discrete cells, never a smooth bar."""
    lit = round(max(0, min(100, value)) / 100 * cells)
    colour = DANGER if value >= 70 else ACCENT if value >= 35 else COOL
    for i in range(cells):
        r = (x + i * (cell_w + 1), y, cell_w, cell_h)
        if i < lit:
            pygame.draw.rect(surf, colour, r)
            pygame.draw.rect(surf, INK, (r[0], r[1] + cell_h - 2, cell_w, 2))
        else:
            pygame.draw.rect(surf, (26, 24, 44), r)
            pygame.draw.rect(surf, (14, 13, 26), (r[0], r[1] + cell_h - 2, cell_w, 2))


class DialogBox:
    """A bottom-of-screen text box that types itself out.

    Lines arrive a character at a time because a box that fills instantly reads
    as a web page. Any key finishes the current page early.
    """

    CHARS_PER_SEC = 42

    def __init__(self):
        self.pages = []
        self.page = 0
        self.shown = 0.0
        self.speaker = None
        self.active = False
        self.on_close = None

    def open(self, body, speaker=None, on_close=None, width=None):
        w = width or SCREEN_W - 24
        lines = wrap(body, w - 16)
        self.pages = [lines[i : i + 3] for i in range(0, len(lines), 3)] or [[""]]
        self.page = 0
        self.shown = 0.0
        self.speaker = speaker
        self.active = True
        self.on_close = on_close

    @property
    def _page_text(self):
        return "\n".join(self.pages[self.page])

    @property
    def done_typing(self):
        return self.shown >= len(self._page_text)

    def update(self, dt):
        if self.active and not self.done_typing:
            self.shown += dt * self.CHARS_PER_SEC

    def advance(self):
        """Returns True if the box consumed the keypress."""
        if not self.active:
            return False
        if not self.done_typing:
            self.shown = len(self._page_text)
            return True
        self.page += 1
        if self.page >= len(self.pages):
            self.active = False
            self.page = 0
            if self.on_close:
                cb, self.on_close = self.on_close, None
                cb()
        return True

    def draw(self, surf, tick):
        if not self.active:
            return
        h = 58
        y = SCREEN_H - h - 8
        panel(surf, (12, y, SCREEN_W - 24, h))
        if self.speaker:
            w = text_w(self.speaker) + 8
            panel(surf, (16, y - 6, w, 12), UI_BG_2, UI_LINE)
            text(surf, self.speaker, 20, y - 4, ACCENT)
        shown = int(self.shown)
        used = 0
        for i, line in enumerate(self.pages[self.page]):
            if used >= shown:
                break
            take = line[: max(0, shown - used)]
            text(surf, take, 20, y + 10 + i * 12, UI_TEXT)
            used += len(line) + 1
        # A blinking marker rather than a glyph — the font has no arrow.
        if self.done_typing and (tick // 24) % 2 == 0:
            mx, my = SCREEN_W - 26, y + h - 12
            if self.page < len(self.pages) - 1:
                pygame.draw.polygon(surf, ACCENT, [(mx, my), (mx + 6, my), (mx + 3, my + 4)])
            else:
                pygame.draw.rect(surf, ACCENT, (mx + 1, my, 4, 4))


class Toast:
    """A short banner for 'evidence added' — never blocks the player."""

    def __init__(self):
        self.msg = None
        self.t = 0.0

    def show(self, msg, seconds=2.6):
        self.msg = msg
        self.t = seconds

    def update(self, dt):
        if self.t > 0:
            self.t = max(0.0, self.t - dt)
            if self.t == 0:
                self.msg = None

    def draw(self, surf):
        if not self.msg:
            return
        w = text_w(self.msg) + 16
        x = (SCREEN_W - w) // 2
        y = 14 if self.t > 0.3 else 14 - int((0.3 - self.t) * 40)
        panel(surf, (x, y, w, 16), UI_BG_2, ACCENT)
        text(surf, self.msg, x + 8, y + 4, ACCENT)


def prompt(surf, label, x, y):
    """The little 'E' key hint that floats over an interactable."""
    w = text_w(label) + 8
    panel(surf, (x - w // 2, y, w, 14), UI_BG_2, UI_HI)
    text(surf, label, x - w // 2 + 4, y + 3, ACCENT)
