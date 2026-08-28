"""Every pixel in the game is made here.

There are no image files. Characters are hand-authored as string art — one
character per pixel, read against a legend — because shape is what sells a
16-pixel sprite. Tiles and furniture are generated with seeded noise so a floor
has texture without a hundred variants being drawn by hand.
"""

import math
import random

import pygame

from settings import *


# --- string art --------------------------------------------------------------


def from_art(rows, legend):
    """Turn rows of legend characters into a surface. '.' is transparent."""
    h = len(rows)
    w = len(rows[0])
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        assert len(row) == w, f"row {y} is {len(row)} wide, expected {w}"
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            surf.set_at((x, y), legend[ch])
    return surf


def stack(*parts):
    """Compose sprites top to bottom into one surface."""
    w = max(p.get_width() for p in parts)
    h = sum(p.get_height() for p in parts)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    y = 0
    for p in parts:
        out.blit(p, ((w - p.get_width()) // 2, y))
        y += p.get_height()
    return out


# --- the detective -----------------------------------------------------------

COAT = (66, 74, 118)
COAT_D = (42, 48, 84)
COAT_L = (96, 106, 156)

DET = {
    "_": INK,
    "H": (48, 44, 68),
    "h": (70, 66, 94),
    "b": (30, 28, 46),
    "s": (216, 162, 120),
    "S": (172, 122, 88),
    "e": (30, 24, 36),
    "c": COAT,
    "C": COAT_D,
    "k": COAT_L,
    "t": (203, 202, 190),
    "p": (56, 54, 78),
    "o": (42, 36, 44),
}

# Twenty rows of body; the last three rows are swapped out per walk frame.
DET_DOWN = [
    "................",
    ".....______.....",
    "...._HHhhHH_....",
    "...._HhhhhH_....",
    "...._HHHHHH_....",
    ".._HHHHHHHHHH_..",
    ".._bbbbbbbbbb_..",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    ".._cccccccccc_..",
    ".._ccckttkcck_..",
    ".._ccckttkcck_..",
    ".._ccckttkcck_..",
    ".._CcckttkccC_..",
    ".._CCCCCCCCCC_..",
]

DET_UP = [
    "................",
    ".....______.....",
    "...._HHhhHH_....",
    "...._HhhhhH_....",
    "...._HHHHHH_....",
    ".._HHHHHHHHHH_..",
    ".._bbbbbbbbbb_..",
    "...._bbbbbb_....",
    "...._HHHHHH_....",
    "...._HHHHHH_....",
    "...._HHHHHH_....",
    "...._SHHHHS_....",
    "....._ssss_.....",
    "....._cccc_.....",
    ".._cccccccccc_..",
    ".._ccccCCccck_..",
    ".._ccccCCccck_..",
    ".._ccccCCccck_..",
    ".._CcccCCcccC_..",
    ".._CCCCCCCCCC_..",
]

# Profile, facing right. Mirrored at build time for the left-facing set.
DET_SIDE = [
    "................",
    ".....?????......",
    "...._HHHHH_.....",
    "...._HhhhH_.....",
    "...._HHHHH_.....",
    "..._HHHHHHHHH_..",
    "..._bbbbbbbbb_..",
    "...._SSSSS_.....",
    "...._sssss_.....",
    "...._ssess_.....",
    "...._sssss_.....",
    "...._sSSss_.....",
    "....._sss_......",
    "....._ttt_......",
    "..._ccccccc_....",
    "..._Ckccccc_....",
    "..._Ckccccc_....",
    "..._Ckccccc_....",
    "..._CCcccck_....",
    "..._CCCCCCC_....",
]
DET_SIDE = [r.replace("?", "_") for r in DET_SIDE]

# Walk cycle: stand, left foot, stand, right foot.
LEGS_FRONT = [
    ["....ppp..ppp....", "....ppp..ppp....", "....ooo..ooo...."],
    ["....ppp..ppp....", "...ppp....pp....", "...ooo....oo...."],
    ["....ppp..ppp....", "....ppp..ppp....", "....ooo..ooo...."],
    ["....ppp..ppp....", "....pp....ppp...", "....oo....ooo..."],
]

LEGS_SIDE = [
    ["....ppppp.......", "....ppppp.......", "...oooooo......."],
    ["...pp..ppp......", "..ppp....pp.....", "..ooo....ooo...."],
    ["....ppppp.......", "....ppppp.......", "...oooooo......."],
    ["...ppp.ppp......", "...pp....ppp....", "...oo....ooo...."],
]


def build_actor(body_down, body_up, body_side, legs_front, legs_side, legend):
    """Assemble a four-direction, four-frame walk cycle."""
    out = {}
    for name, body, legs in (
        ("down", body_down, legs_front),
        ("up", body_up, legs_front),
        ("right", body_side, legs_side),
    ):
        out[name] = [from_art(body + frame, legend) for frame in legs]
    out["left"] = [pygame.transform.flip(f, True, False) for f in out["right"]]
    return out


# --- Elias, seated -----------------------------------------------------------

ELIAS = {
    "_": INK,
    "n": (43, 34, 51),
    "s": (208, 168, 134),
    "S": (168, 126, 98),
    "e": (30, 24, 36),
    "a": (198, 196, 182),
    "A": (158, 156, 146),
    "w": (104, 108, 138),
    "p": (60, 58, 74),
}

ELIAS_SEATED = [
    "................",
    "....._nnnn_.....",
    "...._nnnnnn_....",
    "...._nnnnnn_....",
    "...._nssssn_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._SssS_.....",
    "..._wwaaaaww_...",
    "..._wwaaaaww_...",
    "..._wwaaaaww_...",
    "..._wwaaaaww_...",
    "..._sAaaaaAs_...",
    "..._AAAAAAAA_...",
    "..._pppppppp_...",
    "..._pppppppp_...",
]

# The same man, slumped — used once his composure is gone.
ELIAS_BROKEN = [
    "................",
    "................",
    "....._nnnn_.....",
    "...._nnnnnn_....",
    "...._nnnnnn_....",
    "...._nssssn_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "...._ssssss_....",
    "....._SSSS_.....",
    "....._SssS_.....",
    "..._wwaaaaww_...",
    "..._wwaaaaww_...",
    "..._wwaaaaww_...",
    "..._sAaaaaAs_...",
    "..._AAAAAAAA_...",
    "..._pppppppp_...",
    "..._pppppppp_...",
    "................",
]


# --- the four suspects, standing --------------------------------------------
#
# All four reuse the detective's own proven body geometry (DET_DOWN for a
# normal, composed stance; DET_UP - head tucked down and away - for the
# "broken" reaction) so there is zero risk of a row-width mismatch. What makes
# each character read as a different person is the legend: uniform colour,
# skin tone, cap. None of the four ever walk, so there is no per-direction
# walk cycle - just one calm pose and one broken pose apiece, standing on the
# same static leg frame the detective uses at rest.

_STAND_LEGS = LEGS_FRONT[0]


def _standing(body, legend):
    return from_art(body + _STAND_LEGS, legend)


# Each suspect gets their own build and headgear rather than a recolour of the
# detective: a patrol cap over heavy shoulders reads as a different man from a
# garrison cap over a narrow frame, even at sixteen pixels. Every body is 20
# rows of 16 so it drops onto the same standing legs.

THORNE_BODY = [
    "................",
    "...._______.....",
    "..._HHhhhhHH_...",
    "..._HhhhhhhH_...",
    "..._HHHHHHHH_...",
    ".._bbbbbbbbbb_..",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    "._cccccccccccc_.",
    "._ccckttkccccc_.",
    "._ccckttkccccc_.",
    "._ccckttkccccc_.",
    "._ccckttkccccc_.",
    "._CcckttkcccCC_.",
    "._CCCCCCCCCCCC_.",
]
THORNE_SLUMP = [
    "................",
    "................",
    "...._______.....",
    "..._HHhhhhHH_...",
    "..._HhhhhhhH_...",
    "..._HHHHHHHH_...",
    ".._bbbbbbbbbb_..",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    "._cccccccccccc_.",
    "._ccckttkccccc_.",
    "._ccckttkccccc_.",
    "._ccckttkccccc_.",
    "._CcckttkcccCC_.",
    "._CCCCCCCCCCCC_.",
    "................",
    "................",
]

DOSS_BODY = [
    "................",
    "................",
    "....._HHHH_.....",
    "...._HhhhhH_....",
    "..._HHHHHHHH_...",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._ssss_.....",
    "....._tttt_.....",
    "..._cccccccc_...",
    "..._ckttkccc_...",
    "..._ckttkccc_...",
    "..._ckttkccc_...",
    "..._ckttkccc_...",
    "..._CkttkccC_...",
    "..._CCCCCCCC_...",
]
DOSS_SLUMP = [
    "................",
    "................",
    "................",
    "....._HHHH_.....",
    "...._HhhhhH_....",
    "..._HHHHHHHH_...",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    "..._cccccccc_...",
    "..._ckttkccc_...",
    "..._ckttkccc_...",
    "..._ckttkccc_...",
    "..._CkttkccC_...",
    "..._CCCCCCCC_...",
    "................",
    "................",
    "................",
]

ASHWORTH_BODY = [
    "................",
    "...._______.....",
    "...._HHHHHH_....",
    "...._HhhhhH_....",
    "..._HHHHHHHH_...",
    ".._bbbbbbbbbb_..",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    ".._cccccccccc_..",
    ".._cckcccckcc_..",
    ".._cckcccckcc_..",
    ".._cckcccckcc_..",
    ".._cckcccckcc_..",
    ".._CckcccckcC_..",
    ".._CCCCCCCCCC_..",
]
ASHWORTH_SLUMP = [
    "................",
    "................",
    "...._______.....",
    "...._HHHHHH_....",
    "...._HhhhhH_....",
    "..._HHHHHHHH_...",
    ".._bbbbbbbbbb_..",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    ".._cccccccccc_..",
    ".._cckcccckcc_..",
    ".._cckcccckcc_..",
    ".._cckcccckcc_..",
    ".._CckcccckcC_..",
    ".._CCCCCCCCCC_..",
    "................",
    "................",
]

# Bricker stands hunched: short neck, shoulders riding high, hands in pockets.
BRICKER_BODY = [
    "................",
    "................",
    "....._HHHH_.....",
    "...._HHHHHH_....",
    "...._hhhhhh_....",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sesses_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    ".._cccccccccc_..",
    ".._cccccccccc_..",
    ".._cCCccccCCc_..",
    ".._cCCccccCCc_..",
    ".._cccccccccc_..",
    ".._cccccccccc_..",
    ".._CccccccccC_..",
    ".._CCCCCCCCCC_..",
]
BRICKER_SLUMP = [
    "................",
    "................",
    "................",
    "....._HHHH_.....",
    "...._HHHHHH_....",
    "...._hhhhhh_....",
    "...._SSSSSS_....",
    "...._ssssss_....",
    "...._sSSSSs_....",
    "....._ssss_.....",
    "....._tttt_.....",
    ".._cccccccccc_..",
    ".._cCCccccCCc_..",
    ".._cCCccccCCc_..",
    ".._cccccccccc_..",
    ".._cccccccccc_..",
    ".._CccccccccC_..",
    ".._CCCCCCCCCC_..",
    "................",
    "................",
]


THORNE = {
    "_": INK, "H": (52, 58, 44), "h": (74, 86, 58), "b": (30, 28, 46),
    "s": (208, 168, 134), "S": (172, 122, 88), "e": (30, 24, 36),
    "c": (74, 86, 58), "C": (54, 64, 42), "k": (100, 114, 80),
    "t": (60, 70, 50), "p": (40, 38, 34), "o": (26, 24, 22),
}
THORNE_STANDING = _standing(THORNE_BODY, THORNE)
THORNE_BROKEN = _standing(THORNE_SLUMP, THORNE)

DOSS = {
    "_": INK, "H": (74, 66, 48), "h": (132, 118, 84), "b": (30, 28, 46),
    "s": (216, 172, 132), "S": (176, 128, 92), "e": (30, 24, 36),
    "c": (132, 118, 84), "C": (98, 86, 58), "k": (162, 148, 112),
    "t": (98, 86, 58), "p": (52, 46, 36), "o": (30, 26, 20),
}
DOSS_STANDING = _standing(DOSS_BODY, DOSS)
DOSS_OPEN = _standing(DOSS_SLUMP, DOSS)

ASHWORTH = {
    "_": INK, "H": (34, 36, 46), "h": (58, 60, 74), "b": (24, 22, 34),
    "s": (196, 158, 128), "S": (158, 118, 92), "e": (30, 24, 36),
    "c": (58, 60, 74), "C": (40, 42, 54), "k": (82, 84, 100),
    "t": (188, 148, 70), "p": (36, 38, 48), "o": (22, 20, 30),
}
ASHWORTH_STANDING = _standing(ASHWORTH_BODY, ASHWORTH)
ASHWORTH_OPEN = _standing(ASHWORTH_SLUMP, ASHWORTH)

BRICKER = {
    "_": INK, "H": (40, 40, 44), "h": (60, 60, 66), "b": (26, 26, 32),
    "s": (212, 166, 126), "S": (170, 120, 86), "e": (30, 24, 36),
    "c": (70, 84, 96), "C": (50, 62, 72), "k": (96, 112, 124),
    "t": (50, 62, 72), "p": (44, 44, 48), "o": (28, 26, 24),
}
BRICKER_STANDING = _standing(BRICKER_BODY, BRICKER)
BRICKER_SHAKEN = _standing(BRICKER_SLUMP, BRICKER)

def _mark(surf, pixels):
    """Stamp a few extra pixels onto a built sprite — small insignia and
    wear that make four recolours of the same body read as four people."""
    for x, y, colour in pixels:
        surf.set_at((x, y), colour)
    return surf


# Insignia sit on the sleeve of each body, so the coordinates below are per
# build rather than shared — a mark placed for one silhouette lands off the
# edge of a narrower one.

# Sergeant's chevrons, on the broad sleeve.
_mark(THORNE_STANDING, [
    (3, 15, (196, 190, 150)), (4, 16, (196, 190, 150)), (3, 17, (196, 190, 150)),
])
_mark(THORNE_BROKEN, [
    (3, 14, (196, 190, 150)), (4, 15, (196, 190, 150)), (3, 16, (196, 190, 150)),
])

# A wrench on the belt — the vault NCO who signs for the tools.
_mark(DOSS_STANDING, [
    (10, 17, (176, 176, 184)), (10, 18, (176, 176, 184)), (9, 18, (140, 140, 148)),
])
_mark(DOSS_OPEN, [
    (10, 15, (176, 176, 184)), (10, 16, (176, 176, 184)), (9, 16, (140, 140, 148)),
])

# A colonel's shoulder star — gold, unmissable next to two corporals.
_mark(ASHWORTH_STANDING, [
    (10, 14, BRASS), (11, 14, BRASS), (10, 15, BRASS_D),
])
_mark(ASHWORTH_OPEN, [
    (10, 13, BRASS), (11, 13, BRASS), (10, 14, BRASS_D),
])

# Grease on the coat — a motor pool mechanic never quite gets clean.
_mark(BRICKER_STANDING, [
    (7, 17, (64, 46, 28)), (8, 18, (64, 46, 28)), (6, 18, (82, 60, 36)),
])
_mark(BRICKER_SHAKEN, [
    (7, 15, (64, 46, 28)), (8, 16, (64, 46, 28)), (6, 16, (82, 60, 36)),
])

NPC_ART = {
    "thorne": (THORNE_STANDING, THORNE_BROKEN),
    "doss": (DOSS_STANDING, DOSS_OPEN),
    "ashworth": (ASHWORTH_STANDING, ASHWORTH_OPEN),
    "bricker": (BRICKER_STANDING, BRICKER_SHAKEN),
}


# --- tiles -------------------------------------------------------------------


def _speckle(surf, rng, colours, count):
    for _ in range(count):
        x, y = rng.randrange(TILE), rng.randrange(TILE)
        surf.set_at((x, y), rng.choice(colours))


def tile_grass(seed):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(GRASS)
    _speckle(s, rng, [GRASS_D, GRASS_L], 34)
    # A few upright blades so the ground has a direction.
    for _ in range(rng.randrange(2, 5)):
        x, y = rng.randrange(1, TILE - 1), rng.randrange(2, TILE - 2)
        pygame.draw.line(s, GRASS_L, (x, y), (x, y - 2))
        s.set_at((x, y + 1), GRASS_D)
    return s


def tile_stone_path(seed):
    """Irregular cobbles — the mortar is what reads at this size."""
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(STONE_D)
    y = 0
    row = 0
    while y < TILE:
        h = rng.choice((5, 6))
        x = -rng.randrange(0, 6) if row % 2 else 0
        while x < TILE:
            w = rng.choice((5, 6, 7))
            pygame.draw.rect(s, rng.choice((STONE, STONE, STONE_L)), (x + 1, y + 1, w - 1, h - 1))
            x += w
        y += h
        row += 1
    _speckle(s, rng, [STONE_D, STONE_L], 8)
    return s


def tile_marble(seed, dark=False):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(MARBLE_D if dark else MARBLE)
    # Veining: a short drunken walk across the slab.
    vein = MARBLE_L if dark else MARBLE_D
    x, y = rng.randrange(TILE), rng.randrange(TILE)
    for _ in range(rng.randrange(5, 11)):
        s.set_at((x % TILE, y % TILE), vein)
        x += rng.choice((0, 1, 1))
        y += rng.choice((-1, 0, 1))
    # Grout on two edges only, so slabs read as a grid rather than as boxes.
    pygame.draw.line(s, STONE_D, (0, 0), (TILE - 1, 0))
    pygame.draw.line(s, STONE_D, (0, 0), (0, TILE - 1))
    return s


def tile_wood(seed):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(WOOD)
    for y in range(0, TILE, 4):
        pygame.draw.line(s, WOOD_D, (0, y), (TILE - 1, y))
        for _ in range(3):
            gx = rng.randrange(TILE)
            pygame.draw.line(s, WOOD_L, (gx, y + 2), (min(TILE - 1, gx + rng.randrange(2, 5)), y + 2))
    # Butt joints between boards.
    for y in range(0, TILE, 4):
        if rng.random() < 0.4:
            jx = rng.randrange(TILE)
            pygame.draw.line(s, WOOD_D, (jx, y), (jx, y + 3))
    return s


def tile_carpet(seed, border=None):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(CARPET)
    _speckle(s, rng, [CARPET_D, CARPET_L], 40)
    if border:
        for edge in border:
            if edge == "n":
                pygame.draw.rect(s, BRASS_D, (0, 0, TILE, 2))
            elif edge == "s":
                pygame.draw.rect(s, BRASS_D, (0, TILE - 2, TILE, 2))
            elif edge == "w":
                pygame.draw.rect(s, BRASS_D, (0, 0, 2, TILE))
            elif edge == "e":
                pygame.draw.rect(s, BRASS_D, (TILE - 2, 0, 2, TILE))
    return s


def tile_wall_face(seed):
    """The side of a wall you actually look at, in three-quarter view."""
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(WALL_D)
    for i, y in enumerate(range(0, TILE, 8)):
        off = 0 if i % 2 == 0 else -4
        x = off
        while x < TILE:
            pygame.draw.rect(s, WALL, (x + 1, y + 1, 7, 6))
            pygame.draw.line(s, WALL_L, (x + 1, y + 1), (x + 7, y + 1))
            x += 8
    _speckle(s, rng, [WALL_D, WALL_L], 6)
    return s


def tile_wall_top(seed):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(WALL_L)
    _speckle(s, rng, [WALL, (120, 118, 146)], 20)
    pygame.draw.line(s, WALL, (0, TILE - 1), (TILE - 1, TILE - 1))
    return s


def tile_wainscot(seed):
    """Panelled dado — the gallery walls, so they don't read as a dungeon."""
    s = tile_wall_face(seed)
    pygame.draw.rect(s, WOOD_D, (0, 6, TILE, TILE - 6))
    pygame.draw.rect(s, WOOD, (1, 8, TILE - 2, TILE - 10))
    pygame.draw.line(s, WOOD_L, (1, 8), (TILE - 2, 8))
    pygame.draw.rect(s, BRASS_D, (0, 5, TILE, 1))
    return s


def tile_void():
    s = pygame.Surface((TILE, TILE))
    s.fill(NIGHT)
    return s


def tile_hedge(seed):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill(HEDGE)
    for _ in range(26):
        x, y = rng.randrange(TILE), rng.randrange(TILE)
        pygame.draw.rect(s, rng.choice((HEDGE_L, HEDGE, (28, 56, 40))), (x, y, 2, 2))
    return s


def tile_water(seed):
    rng = random.Random(seed)
    s = pygame.Surface((TILE, TILE))
    s.fill((44, 74, 122))
    for y in range(0, TILE, 3):
        pygame.draw.line(s, (60, 98, 152), (rng.randrange(0, 6), y), (rng.randrange(9, TILE), y))
    _speckle(s, rng, [(96, 140, 190)], 6)
    return s


def build_tiles():
    """Four variants per ground type; the map picks one from the coordinates."""
    t = {}
    t["grass"] = [tile_grass(i) for i in range(4)]
    t["path"] = [tile_stone_path(i) for i in range(4)]
    t["marble"] = [tile_marble(i, dark=False) for i in range(3)]
    t["marble_d"] = [tile_marble(i + 10, dark=True) for i in range(3)]
    t["wood"] = [tile_wood(i) for i in range(4)]
    t["carpet"] = [tile_carpet(i) for i in range(3)]
    t["wall"] = [tile_wall_face(i) for i in range(3)]
    t["wall_top"] = [tile_wall_top(i) for i in range(3)]
    t["wainscot"] = [tile_wainscot(i) for i in range(3)]
    t["hedge"] = [tile_hedge(i) for i in range(3)]
    t["water"] = [tile_water(i) for i in range(3)]
    t["void"] = [tile_void()]
    return t


# --- furniture and props -----------------------------------------------------
#
# Drawn with rectangles rather than string art: at this size a chair is four
# boxes, and the code stays shorter than the picture would be.


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _box(s, rect, fill, top=None, shade=None, outline=INK):
    x, y, w, h = rect
    pygame.draw.rect(s, fill, rect)
    if top:
        pygame.draw.rect(s, top, (x, y, w, 1))
    if shade:
        pygame.draw.rect(s, shade, (x, y + h - 2, w, 2))
        pygame.draw.rect(s, shade, (x + w - 1, y, 1, h))
    if outline:
        pygame.draw.rect(s, outline, rect, 1)


def obj_plinth():
    """Marble pedestal with a small bust. One of these is missing its base."""
    s = _surf(16, 28)
    _box(s, (3, 12, 10, 15), MARBLE_D, MARBLE_L, STONE_D)
    _box(s, (1, 24, 14, 4), MARBLE, MARBLE_L, STONE_D)
    _box(s, (2, 10, 12, 3), MARBLE, MARBLE_L, STONE_D)
    # bust
    _box(s, (5, 4, 6, 7), (188, 178, 156), (216, 208, 188), (144, 134, 116))
    pygame.draw.rect(s, (144, 134, 116), (6, 6, 1, 2))
    pygame.draw.rect(s, (144, 134, 116), (9, 6, 1, 2))
    _box(s, (6, 1, 4, 4), (198, 188, 166), (222, 214, 196), (144, 134, 116))
    return s


def obj_plinth_empty():
    """The plinth the murder weapon came off. Its marble base is gone."""
    s = _surf(16, 28)
    _box(s, (3, 12, 10, 15), MARBLE, MARBLE_L, STONE_D)
    _box(s, (2, 10, 12, 3), MARBLE_L, (240, 236, 226), STONE_D)
    # The gap where the base was torn off, and the tape around it.
    pygame.draw.rect(s, INK, (4, 24, 8, 4))
    pygame.draw.rect(s, SHADOW, (5, 25, 6, 2))
    pygame.draw.rect(s, TAPE, (2, 15, 12, 1))
    return s


def obj_painting(w=32, empty=False, canvas=None):
    s = _surf(w, 18)
    _box(s, (0, 0, w, 18), BRASS_D, BRASS, (96, 68, 28))
    inner = (2, 2, w - 4, 14)
    if empty:
        pygame.draw.rect(s, (36, 32, 44), inner)
        pygame.draw.rect(s, (24, 20, 30), (3, 3, w - 6, 12))
        return s
    rng = random.Random(w + (1 if canvas else 0))
    sky, land = canvas or ((132, 150, 168), (86, 104, 68))
    pygame.draw.rect(s, sky, inner)
    pygame.draw.rect(s, land, (2, 10, w - 4, 6))
    for _ in range(w // 3):
        x = rng.randrange(3, w - 4)
        pygame.draw.line(s, (58, 74, 48), (x, 10), (x, 8 - rng.randrange(2)))
    pygame.draw.rect(s, (168, 176, 186), (w - 9, 4, 4, 2))
    return s


def obj_desk():
    s = _surf(32, 20)
    _box(s, (0, 4, 32, 8), WOOD, WOOD_L, WOOD_D)
    _box(s, (1, 12, 8, 8), WOOD_D, None, None)
    _box(s, (23, 12, 8, 8), WOOD_D, None, None)
    pygame.draw.rect(s, BRASS, (3, 15, 4, 1))
    pygame.draw.rect(s, BRASS, (25, 15, 4, 1))
    # papers and a desk lamp
    pygame.draw.rect(s, PAPER, (12, 2, 8, 4))
    pygame.draw.rect(s, PAPER_D, (13, 5, 7, 1))
    pygame.draw.rect(s, INK, (12, 2, 8, 4), 1)
    return s


def obj_table():
    s = _surf(48, 22)
    _box(s, (0, 2, 48, 10), WOOD_L, (176, 132, 92), WOOD_D)
    _box(s, (3, 12, 5, 10), WOOD_D, None, None)
    _box(s, (40, 12, 5, 10), WOOD_D, None, None)
    return s


def obj_chair(facing="down"):
    s = _surf(16, 20)
    if facing == "down":
        _box(s, (3, 8, 10, 6), WOOD, WOOD_L, WOOD_D)
        _box(s, (3, 1, 10, 8), WOOD_D, WOOD, None)
    else:
        _box(s, (3, 4, 10, 6), WOOD, WOOD_L, WOOD_D)
        _box(s, (3, 10, 10, 6), WOOD_D, None, None)
    pygame.draw.rect(s, WOOD_D, (4, 14, 2, 6))
    pygame.draw.rect(s, WOOD_D, (10, 14, 2, 6))
    return s


def obj_shelf():
    s = _surf(16, 26)
    _box(s, (0, 0, 16, 26), WOOD_D, WOOD, INK)
    rng = random.Random(7)
    for shelf_y in (3, 11, 19):
        pygame.draw.rect(s, (52, 34, 24), (1, shelf_y, 14, 6))
        x = 2
        while x < 14:
            bw = rng.choice((1, 2, 2))
            bh = rng.choice((4, 5, 6))
            col = rng.choice(((142, 58, 52), (60, 92, 128), (150, 128, 66), (86, 108, 70)))
            pygame.draw.rect(s, col, (x, shelf_y + 6 - bh, bw, bh))
            x += bw + 1
        pygame.draw.rect(s, WOOD, (1, shelf_y + 6, 14, 1))
    return s


def obj_cabinet():
    s = _surf(16, 24)
    _box(s, (0, 0, 16, 24), STONE_D, STONE, INK)
    for y in (3, 10, 17):
        pygame.draw.rect(s, STONE, (2, y, 12, 5))
        pygame.draw.rect(s, INK, (2, y, 12, 5), 1)
        pygame.draw.rect(s, BRASS, (7, y + 2, 3, 1))
    return s


def obj_plant():
    s = _surf(16, 24)
    _box(s, (4, 16, 8, 8), (146, 84, 58), (176, 108, 74), (96, 52, 34))
    rng = random.Random(3)
    for _ in range(16):
        x = rng.randrange(2, 14)
        y = rng.randrange(2, 16)
        pygame.draw.rect(s, rng.choice((HEDGE, HEDGE_L, (30, 60, 42))), (x, y, 3, 3))
    return s


def obj_lamp(lit=True):
    s = _surf(16, 30)
    pygame.draw.rect(s, (52, 50, 66), (7, 10, 2, 18))
    _box(s, (4, 27, 8, 3), (52, 50, 66), None, INK)
    shade = LAMP if lit else (96, 92, 104)
    _box(s, (2, 2, 12, 9), shade, GLOW if lit else (120, 116, 128), LAMP_D if lit else (70, 66, 80))
    return s


def obj_sconce():
    s = _surf(16, 12)
    _box(s, (5, 6, 6, 5), BRASS_D, BRASS, INK)
    _box(s, (4, 1, 8, 6), LAMP, GLOW, LAMP_D)
    return s


def obj_dumpster():
    s = _surf(32, 22)
    _box(s, (0, 6, 32, 16), (58, 84, 68), (78, 108, 86), (34, 52, 42))
    _box(s, (0, 2, 32, 5), (46, 68, 56), (72, 98, 78), (34, 52, 42))
    pygame.draw.rect(s, (34, 52, 42), (10, 7, 1, 14))
    pygame.draw.rect(s, (34, 52, 42), (21, 7, 1, 14))
    return s


def obj_door(open_=False):
    s = _surf(16, 16)
    if open_:
        pygame.draw.rect(s, (12, 10, 18), (2, 0, 12, 16))
        pygame.draw.rect(s, WOOD_D, (0, 0, 2, 16))
        pygame.draw.rect(s, WOOD_D, (14, 0, 2, 16))
        return s
    _box(s, (1, 0, 14, 16), WOOD, WOOD_L, WOOD_D)
    pygame.draw.rect(s, WOOD_D, (3, 2, 10, 5))
    pygame.draw.rect(s, WOOD_D, (3, 9, 10, 5))
    pygame.draw.rect(s, BRASS, (12, 8, 2, 2))
    return s


def obj_body_outline():
    """Tape on the floor where Marguerite was found — head, arms, legs."""
    s = _surf(30, 40)
    pygame.draw.circle(s, TAPE, (15, 6), 5, 1)
    pts = [
        (11, 10), (7, 14), (2, 22), (5, 24), (9, 17),  # left arm, flung out
        (9, 26), (7, 38), (11, 38), (14, 27),          # left leg
        (17, 27), (21, 38), (25, 37), (22, 25),        # right leg
        (22, 16), (27, 21), (29, 18), (23, 11),        # right arm
        (19, 10),
    ]
    pygame.draw.lines(s, TAPE, True, pts, 1)
    # The stain, under the head where the blow landed.
    pygame.draw.ellipse(s, (74, 22, 26), (8, 1, 12, 9))
    pygame.draw.ellipse(s, BLOOD, (10, 2, 8, 6))
    return s


def obj_tree():
    """Museum grounds. Two greens and a hard rim is all a canopy needs."""
    s = _surf(26, 36)
    pygame.draw.rect(s, (72, 46, 32), (11, 24, 4, 12))
    pygame.draw.rect(s, (52, 32, 22), (11, 24, 1, 12))
    rng = random.Random(11)
    pygame.draw.circle(s, (30, 58, 40), (13, 15), 13)
    for _ in range(90):
        a = rng.random() * math.tau
        r = rng.random() ** 0.5 * 11
        x = int(13 + r * math.cos(a))
        y = int(15 + r * math.sin(a))
        pygame.draw.rect(s, rng.choice((HEDGE, HEDGE_L, (46, 84, 54))), (x, y, 2, 2))
    pygame.draw.circle(s, (22, 44, 32), (13, 15), 13, 1)
    return s


def obj_bush():
    s = _surf(16, 14)
    rng = random.Random(5)
    pygame.draw.ellipse(s, HEDGE, (0, 2, 16, 12))
    for _ in range(24):
        x, y = rng.randrange(1, 14), rng.randrange(3, 12)
        pygame.draw.rect(s, rng.choice((HEDGE_L, HEDGE)), (x, y, 2, 2))
    return s


def obj_flowers():
    s = _surf(16, 10)
    rng = random.Random(9)
    pygame.draw.ellipse(s, (46, 84, 54), (0, 3, 16, 7))
    for _ in range(7):
        x, y = rng.randrange(2, 14), rng.randrange(3, 8)
        s.set_at((x, y), rng.choice(((214, 92, 108), (238, 206, 96), (176, 132, 214))))
    return s


def obj_crate():
    s = _surf(16, 15)
    _box(s, (0, 2, 16, 13), WOOD, WOOD_L, WOOD_D)
    pygame.draw.line(s, WOOD_D, (1, 3), (14, 13))
    pygame.draw.line(s, WOOD_D, (14, 3), (1, 13))
    pygame.draw.rect(s, WOOD_D, (0, 6, 16, 1))
    return s


def obj_pallet():
    s = _surf(22, 10)
    _box(s, (0, 2, 22, 8), WOOD_D, WOOD, INK)
    for x in range(1, 21, 4):
        pygame.draw.rect(s, WOOD, (x, 3, 3, 6))
    return s


def obj_stanchion():
    """Rope barrier. The rope is what tells you not to touch the art."""
    s = _surf(24, 20)
    for x in (2, 20):
        pygame.draw.rect(s, BRASS_D, (x, 6, 2, 12))
        pygame.draw.rect(s, BRASS, (x - 1, 4, 4, 3))
        pygame.draw.rect(s, BRASS_D, (x - 2, 18, 6, 2))
    pygame.draw.line(s, (86, 34, 40), (3, 7), (11, 10))
    pygame.draw.line(s, (86, 34, 40), (11, 10), (20, 7))
    pygame.draw.line(s, (128, 52, 58), (3, 6), (11, 9))
    pygame.draw.line(s, (128, 52, 58), (11, 9), (20, 6))
    return s


def obj_case():
    """Glass display case with something small and gold inside."""
    s = _surf(32, 22)
    _box(s, (0, 14, 32, 8), WOOD_D, WOOD, INK)
    pygame.draw.rect(s, (168, 198, 210), (2, 2, 28, 13))
    pygame.draw.rect(s, (196, 220, 230), (2, 2, 28, 2))
    pygame.draw.rect(s, INK, (2, 2, 28, 13), 1)
    pygame.draw.rect(s, BRASS, (12, 8, 8, 5))
    pygame.draw.rect(s, BRASS_D, (12, 12, 8, 1))
    for x in (10, 21):
        pygame.draw.line(s, (206, 228, 236), (x, 3), (x - 3, 14))
    return s


def obj_workbench():
    """A conservator's bench: jars, brushes, a lamp clamped to the edge."""
    s = _surf(32, 20)
    _box(s, (0, 4, 32, 9), WOOD_L, (180, 138, 96), WOOD_D)
    pygame.draw.rect(s, WOOD_D, (2, 13, 4, 7))
    pygame.draw.rect(s, WOOD_D, (26, 13, 4, 7))
    for x, col in ((4, (168, 176, 186)), (8, (196, 168, 96)), (12, (140, 96, 168))):
        pygame.draw.rect(s, col, (x, 0, 3, 5))
        pygame.draw.rect(s, INK, (x, 0, 3, 5), 1)
    for i, x in enumerate((20, 23, 26)):
        pygame.draw.line(s, WOOD_D, (x, 4), (x + 1, 1 - i % 2))
        s.set_at((x, 0), (60, 50, 44))
    return s


def obj_rack():
    """Drying rack — canvases stacked on edge."""
    s = _surf(16, 26)
    _box(s, (0, 0, 16, 26), (58, 44, 36), None, INK)
    rng = random.Random(13)
    for i, y in enumerate((2, 10, 18)):
        pygame.draw.rect(s, (46, 34, 28), (1, y, 14, 7))
        for x in range(2, 14, 3):
            pygame.draw.rect(
                s, rng.choice(((176, 168, 142), (150, 158, 138), (188, 176, 156))), (x, y + 1, 2, 5)
            )
    return s


def obj_sink():
    s = _surf(16, 16)
    _box(s, (0, 4, 16, 12), STONE, STONE_L, STONE_D)
    pygame.draw.rect(s, (52, 64, 84), (3, 7, 10, 6))
    pygame.draw.rect(s, INK, (3, 7, 10, 6), 1)
    pygame.draw.rect(s, BRASS, (7, 2, 2, 5))
    pygame.draw.rect(s, BRASS, (7, 2, 4, 2))
    return s


def obj_debris():
    """Pulled drawers and scattered paper — the room was turned over."""
    s = _surf(20, 14)
    rng = random.Random(17)
    for _ in range(7):
        x, y = rng.randrange(0, 14), rng.randrange(2, 11)
        pygame.draw.rect(s, PAPER, (x, y, 5, 3))
        pygame.draw.rect(s, PAPER_D, (x, y + 2, 5, 1))
    _box(s, (2, 6, 11, 7), WOOD_D, WOOD, INK)
    pygame.draw.rect(s, BRASS, (6, 9, 3, 1))
    return s


def obj_mirror():
    """The observation glass. You can see yourself in it, which is the point."""
    s = _surf(32, 16)
    _box(s, (0, 0, 32, 16), (44, 52, 74), (72, 84, 116), INK)
    pygame.draw.rect(s, (58, 70, 100), (2, 2, 28, 12))
    for x in range(4, 30, 9):
        pygame.draw.line(s, (86, 100, 136), (x, 3), (x - 2, 13))
    return s


def obj_cooler():
    s = _surf(12, 22)
    _box(s, (1, 8, 10, 14), (206, 208, 212), (232, 234, 238), STONE_D)
    _box(s, (2, 0, 8, 8), (110, 160, 190), (150, 196, 216), (60, 100, 130))
    pygame.draw.rect(s, (60, 70, 90), (4, 13, 4, 2))
    return s


def obj_banner():
    """A hanging exhibition banner. Colour where the walls have none."""
    s = _surf(14, 30)
    pygame.draw.rect(s, BRASS_D, (0, 0, 14, 2))
    _box(s, (1, 2, 12, 26), CARPET, CARPET_L, CARPET_D)
    pygame.draw.rect(s, BRASS, (3, 6, 8, 1))
    pygame.draw.rect(s, PAPER_D, (3, 10, 8, 2))
    pygame.draw.rect(s, PAPER_D, (4, 14, 6, 1))
    pygame.draw.polygon(s, CARPET_D, [(1, 28), (7, 24), (13, 28)])
    return s


def obj_marker(n):
    """A numbered evidence tent. The number is drawn, not typed."""
    s = _surf(10, 12)
    pygame.draw.polygon(s, TAPE, [(1, 11), (5, 2), (9, 11)])
    pygame.draw.polygon(s, (168, 138, 30), [(1, 11), (5, 2), (9, 11)], 1)
    digits = {
        1: [(5, 6), (5, 7), (5, 8), (5, 9), (4, 7)],
        2: [(4, 6), (5, 6), (6, 7), (5, 8), (4, 9), (5, 9), (6, 9)],
        3: [(4, 6), (5, 6), (6, 7), (5, 7), (6, 8), (5, 9), (4, 9)],
        4: [(4, 6), (4, 7), (5, 7), (6, 6), (6, 7), (6, 8), (6, 9)],
        5: [(6, 6), (5, 6), (4, 6), (4, 7), (5, 7), (6, 8), (5, 9), (4, 9)],
    }
    for px, py in digits.get(n, []):
        s.set_at((px, py), INK)
    return s


def obj_easel():
    s = _surf(16, 26)
    pygame.draw.line(s, WOOD_D, (3, 25), (7, 8))
    pygame.draw.line(s, WOOD_D, (12, 25), (8, 8))
    pygame.draw.line(s, WOOD_D, (8, 25), (8, 14))
    _box(s, (1, 6, 14, 11), (222, 216, 198), None, WOOD_D)
    pygame.draw.rect(s, (150, 160, 176), (3, 8, 10, 4))
    pygame.draw.rect(s, (96, 116, 78), (3, 12, 10, 3))
    return s


def obj_bench():
    s = _surf(32, 14)
    _box(s, (0, 2, 32, 6), WOOD, WOOD_L, WOOD_D)
    pygame.draw.rect(s, WOOD_D, (3, 8, 3, 6))
    pygame.draw.rect(s, WOOD_D, (26, 8, 3, 6))
    return s


def obj_fountain():
    s = _surf(48, 40)
    pygame.draw.ellipse(s, STONE_D, (0, 8, 48, 32))
    pygame.draw.ellipse(s, STONE, (2, 10, 44, 28))
    pygame.draw.ellipse(s, (44, 74, 122), (5, 13, 38, 22))
    pygame.draw.ellipse(s, (60, 98, 152), (9, 16, 30, 16))
    _box(s, (20, 4, 8, 20), STONE, STONE_L, STONE_D)
    _box(s, (17, 0, 14, 5), STONE_L, MARBLE_L, STONE_D)
    return s


def obj_vault_terminal():
    """A checkout terminal bolted to the vault wall — the ledger evidence."""
    s = _surf(16, 22)
    _box(s, (0, 4, 16, 18), STONE_D, STONE, INK)
    _box(s, (2, 6, 12, 8), (24, 40, 30), (34, 56, 42), INK)
    rng = random.Random(21)
    for y in range(8, 13, 2):
        w = rng.randrange(5, 10)
        pygame.draw.line(s, (86, 196, 128), (4, y), (4 + w, y))
    for x, y in ((3, 16), (6, 16), (9, 16), (12, 16), (3, 19), (6, 19), (9, 19), (12, 19)):
        pygame.draw.rect(s, STONE_D, (x, y, 2, 2))
    return s


def obj_camera_console():
    """Motor pool gate camera monitor, cycling grainy footage."""
    s = _surf(22, 18)
    _box(s, (0, 0, 22, 18), WOOD_D, WOOD, INK)
    _box(s, (2, 2, 18, 12), (30, 30, 36), (44, 44, 52), INK)
    rng = random.Random(22)
    for y in range(3, 13, 2):
        shade = rng.choice(((70, 70, 78), (54, 54, 62), (86, 86, 94)))
        pygame.draw.line(s, shade, (3, y), (19, y))
    pygame.draw.circle(s, DANGER, (18, 4), 1)
    pygame.draw.rect(s, STONE_D, (8, 14, 6, 3))
    return s


def obj_burner_phone():
    """A cheap prepaid handset, hidden behind a shelf."""
    s = _surf(10, 16)
    _box(s, (1, 1, 8, 14), (34, 34, 40), (48, 48, 56), INK)
    pygame.draw.rect(s, (60, 92, 78), (2, 3, 6, 6))
    pygame.draw.line(s, INK, (2, 6), (8, 4))  # the cracked screen
    for y in (11, 12, 13):
        pygame.draw.rect(s, (24, 24, 30), (3, y, 4, 1))
    return s


def obj_photo_facedown():
    """A printed photo, left face down. All you see is the back."""
    s = _surf(14, 10)
    _box(s, (0, 0, 14, 10), PAPER_D, PAPER, (150, 142, 118))
    pygame.draw.line(s, (150, 142, 118), (2, 8), (5, 6))
    return s


def obj_matchbook():
    """Dropped at the roadside handoff — the Cinder Compact's mark."""
    s = _surf(10, 8)
    _box(s, (0, 0, 10, 8), (24, 22, 28), (40, 38, 46), INK)
    pygame.draw.rect(s, (206, 60, 54), (7, 1, 2, 2))
    pygame.draw.line(s, PAPER_D, (1, 6), (5, 5))
    return s


def obj_kitchen_mess():
    """The Thorne kitchen: a shattered mug, a full one, a chair shoved back."""
    s = _surf(28, 18)
    _box(s, (2, 6, 24, 8), WOOD_L, (176, 132, 92), WOOD_D)
    pygame.draw.rect(s, (216, 220, 224), (4, 3, 5, 5))  # the full mug, cold
    pygame.draw.rect(s, INK, (4, 3, 5, 5), 1)
    rng = random.Random(23)
    for _ in range(6):  # the shattered one, never swept up
        x = 16 + rng.randrange(0, 8)
        y = 15 + rng.randrange(0, 2)
        pygame.draw.rect(s, (206, 210, 214), (x, y, 2, 1))
    _box(s, (20, 1, 6, 6), WOOD_D, WOOD, None)  # the chair, pushed back hard
    return s


def obj_corkboard():
    """The precinct's board: photos, pins, and red string between them. The
    string is the point — it's the one prop that says 'investigation'."""
    s = _surf(46, 26)
    _box(s, (0, 0, 46, 26), (146, 108, 62), (176, 136, 84), (78, 54, 30))
    rng = random.Random(31)
    cards = []
    for cx, cy, w, h in ((4, 4, 9, 7), (18, 3, 10, 8), (33, 5, 9, 7),
                         (7, 15, 10, 7), (24, 16, 12, 6)):
        pygame.draw.rect(s, PAPER, (cx, cy, w, h))
        pygame.draw.rect(s, PAPER_D, (cx, cy + h - 2, w, 2))
        pygame.draw.rect(s, INK, (cx, cy, w, h), 1)
        for _ in range(2):  # a scrawled line or two per card
            ly = cy + 2 + rng.randrange(0, max(1, h - 3))
            pygame.draw.line(s, (128, 122, 108), (cx + 2, ly), (cx + w - 3, ly))
        cards.append((cx + w // 2, cy + h // 2))
    for a, b in zip(cards, cards[1:]):
        pygame.draw.line(s, (168, 46, 44), a, b)
    pygame.draw.line(s, (168, 46, 44), cards[0], cards[-1])
    for px, py in cards:
        s.set_at((px, py), (232, 208, 96))  # brass pin head
    return s


def obj_wallmap():
    """Ashworth's wall map of Harrow's Reach — coastline, roads, a pinned site."""
    s = _surf(40, 28)
    _box(s, (0, 0, 40, 28), (206, 196, 168), (228, 220, 196), (72, 60, 44))
    pygame.draw.rect(s, (156, 176, 158), (2, 2, 36, 24))
    # Water along the bottom, land above it.
    pygame.draw.rect(s, (86, 122, 156), (2, 20, 36, 6))
    pygame.draw.line(s, (66, 98, 130), (2, 20), (38, 20))
    rng = random.Random(37)
    for _ in range(9):  # blocks
        bx, by = rng.randrange(3, 34), rng.randrange(3, 17)
        pygame.draw.rect(s, (132, 152, 136), (bx, by, rng.randrange(3, 6), rng.randrange(2, 4)))
    for x in (11, 22, 31):  # roads
        pygame.draw.line(s, (198, 190, 166), (x, 3), (x, 19))
    pygame.draw.line(s, (198, 190, 166), (3, 12), (37, 12))
    pygame.draw.rect(s, DANGER, (29, 21, 3, 3))  # the pin on Salt Row
    return s


def obj_bollard():
    """A dock bollard with rope looped over it."""
    s = _surf(12, 16)
    _box(s, (3, 4, 6, 12), (62, 58, 66), (94, 90, 100), INK)
    _box(s, (2, 1, 8, 4), (78, 74, 84), (110, 106, 118), INK)
    pygame.draw.arc(s, (156, 132, 88), (0, 7, 12, 8), 3.4, 6.0, 2)
    return s


def obj_munitions_crate():
    """A stencilled weapons case — the shape five of these left behind."""
    s = _surf(20, 15)
    _box(s, (0, 2, 20, 13), (76, 84, 62), (98, 108, 78), (44, 50, 36))
    pygame.draw.rect(s, (44, 50, 36), (0, 6, 20, 1))
    pygame.draw.rect(s, (44, 50, 36), (0, 11, 20, 1))
    for x in (3, 15):  # latches
        pygame.draw.rect(s, (152, 148, 132), (x, 7, 2, 3))
    # Stencil block, unreadable at this size but unmistakably a marking.
    for i, x in enumerate(range(6, 15, 3)):
        pygame.draw.rect(s, (198, 192, 160), (x, 3, 2, 2))
    return s


def build_objects():
    return {
        "plinth": obj_plinth(),
        "plinth_empty": obj_plinth_empty(),
        "painting": obj_painting(32),
        "painting_wide": obj_painting(48),
        "painting_empty": obj_painting(32, empty=True),
        "corot": obj_painting(48, canvas=((156, 168, 148), (96, 106, 62))),
        "desk": obj_desk(),
        "table": obj_table(),
        "chair": obj_chair("down"),
        "chair_up": obj_chair("up"),
        "shelf": obj_shelf(),
        "cabinet": obj_cabinet(),
        "plant": obj_plant(),
        "lamp": obj_lamp(True),
        "sconce": obj_sconce(),
        "dumpster": obj_dumpster(),
        "door": obj_door(),
        "door_open": obj_door(True),
        "outline": obj_body_outline(),
        "easel": obj_easel(),
        "bench": obj_bench(),
        "fountain": obj_fountain(),
        "tree": obj_tree(),
        "bush": obj_bush(),
        "flowers": obj_flowers(),
        "crate": obj_crate(),
        "pallet": obj_pallet(),
        "stanchion": obj_stanchion(),
        "case": obj_case(),
        "workbench": obj_workbench(),
        "rack": obj_rack(),
        "sink": obj_sink(),
        "debris": obj_debris(),
        "mirror": obj_mirror(),
        "cooler": obj_cooler(),
        "banner": obj_banner(),
        "vault_terminal": obj_vault_terminal(),
        "camera_console": obj_camera_console(),
        "burner_phone": obj_burner_phone(),
        "photo_facedown": obj_photo_facedown(),
        "matchbook": obj_matchbook(),
        "kitchen_mess": obj_kitchen_mess(),
        "corkboard": obj_corkboard(),
        "wallmap": obj_wallmap(),
        "bollard": obj_bollard(),
        "munitions_crate": obj_munitions_crate(),
        **{f"marker{i}": obj_marker(i) for i in range(1, 6)},
    }


_cache = None


def objects():
    """Built once. Every prop is a plain surface, so they can all be shared."""
    global _cache
    if _cache is None:
        _cache = build_objects()
    return _cache


# --- lighting ----------------------------------------------------------------


def make_light(radius, colour=(255, 226, 168), strength=190):
    """A round pool of light. Enough bands that the falloff reads as a falloff
    and not as a set of rings — seven looked like a dartboard."""
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    bands = max(12, radius // 2)
    for i in range(bands, 0, -1):
        r = int(radius * i / bands)
        a = int(strength * (1 - (i - 1) / bands) ** 1.7)
        pygame.draw.circle(s, (*colour, a), (radius, radius), r)
    return s


# --- interview portraits -----------------------------------------------------
#
# A 48x48 bust per suspect, in three states. These are drawn rather than
# authored as string art: at this size the head is a handful of rectangles, and
# what actually carries a performance is the eyes, brows and mouth — those get
# placed by hand, pixel by pixel, below. Each character shares one skull and is
# told apart by legend colours plus their own headwear.

EYE_L, EYE_R = 20, 28  # eye centres
BROW_Y, EYE_Y, MOUTH_Y = 15, 18, 26


def _bust_base(lg):
    s = _surf(48, 48)
    skin, skin_d, coat, coat_d, coat_l = lg["s"], lg["S"], lg["c"], lg["C"], lg["k"]

    # Shoulders and collar.
    pygame.draw.rect(s, coat, (3, 35, 42, 13))
    pygame.draw.rect(s, coat_d, (3, 44, 42, 4))
    pygame.draw.rect(s, coat_l, (3, 35, 42, 1))
    pygame.draw.rect(s, INK, (3, 34, 42, 1))
    # Collar notch, so the neck reads as sitting inside a shirt.
    pygame.draw.polygon(s, coat_d, [(18, 35), (24, 42), (30, 35)])
    pygame.draw.polygon(s, INK, [(18, 35), (24, 42), (30, 35)], 1)

    # Neck.
    pygame.draw.rect(s, skin_d, (20, 29, 8, 7))
    pygame.draw.rect(s, INK, (19, 29, 1, 7))
    pygame.draw.rect(s, INK, (28, 29, 1, 7))

    # Skull: a rect with the corners knocked off rather than a true oval —
    # ovals at 24px go lumpy, and the flat planes read better under lamplight.
    pygame.draw.rect(s, skin, (14, 7, 20, 24))
    pygame.draw.rect(s, skin, (13, 11, 22, 15))
    pygame.draw.rect(s, skin_d, (14, 27, 20, 4))  # jaw in shadow
    pygame.draw.rect(s, skin_d, (30, 11, 4, 18))  # lit from the left
    for x, y in ((14, 7), (33, 7), (14, 30), (33, 30)):
        s.set_at((x, y), (0, 0, 0, 0))
    # Ears.
    pygame.draw.rect(s, skin_d, (12, 17, 2, 5))
    pygame.draw.rect(s, skin_d, (34, 17, 2, 5))
    # Outline down both cheeks.
    pygame.draw.rect(s, INK, (12, 8, 1, 23))
    pygame.draw.rect(s, INK, (35, 8, 1, 23))
    pygame.draw.rect(s, INK, (14, 31, 20, 1))

    # Nose.
    pygame.draw.rect(s, skin_d, (23, 20, 2, 4))
    pygame.draw.rect(s, INK, (23, 24, 3, 1))
    return s


def _face(s, lg, mood):
    """Brows, eyes and mouth — the whole performance lives in nine rows."""
    ink, white = INK, (236, 232, 226)
    if mood == "steady":
        for x in (EYE_L - 2, EYE_R - 2):
            pygame.draw.rect(s, ink, (x, BROW_Y, 5, 1))
        for x in (EYE_L - 1, EYE_R - 1):
            pygame.draw.rect(s, white, (x, EYE_Y, 3, 2))
            pygame.draw.rect(s, ink, (x + 1, EYE_Y, 1, 2))
        pygame.draw.rect(s, ink, (21, MOUTH_Y, 7, 1))
    elif mood == "rattled":
        # Inner brows lift; the mouth tightens and pulls down at one corner.
        pygame.draw.rect(s, ink, (EYE_L - 2, BROW_Y + 1, 3, 1))
        pygame.draw.rect(s, ink, (EYE_L + 1, BROW_Y, 2, 1))
        pygame.draw.rect(s, ink, (EYE_R - 1, BROW_Y, 2, 1))
        pygame.draw.rect(s, ink, (EYE_R + 1, BROW_Y + 1, 3, 1))
        for x in (EYE_L - 1, EYE_R - 1):
            pygame.draw.rect(s, white, (x, EYE_Y, 3, 3))
            pygame.draw.rect(s, ink, (x + 1, EYE_Y + 1, 1, 2))
        pygame.draw.rect(s, ink, (21, MOUTH_Y, 6, 1))
        s.set_at((27, MOUTH_Y + 1), ink)
    else:  # cracking
        pygame.draw.rect(s, ink, (EYE_L - 2, BROW_Y + 2, 4, 1))
        pygame.draw.rect(s, ink, (EYE_L + 2, BROW_Y, 2, 1))
        pygame.draw.rect(s, ink, (EYE_R - 2, BROW_Y, 2, 1))
        pygame.draw.rect(s, ink, (EYE_R, BROW_Y + 2, 4, 1))
        for x in (EYE_L - 1, EYE_R - 1):
            pygame.draw.rect(s, white, (x, EYE_Y - 1, 4, 4))
            pygame.draw.rect(s, ink, (x + 1, EYE_Y, 2, 2))
        # Mouth open, jaw slack.
        pygame.draw.rect(s, (58, 30, 34), (21, MOUTH_Y, 7, 3))
        pygame.draw.rect(s, ink, (21, MOUTH_Y, 7, 1))
        # Sweat, running off the temple.
        pygame.draw.rect(s, (150, 205, 226), (36, 14, 1, 3))
        s.set_at((36, 17), (198, 232, 244))
    return s


def _headwear(s, lg, kind):
    band = lg["H"]
    lit = lg["h"]
    if kind == "patrol":  # Thorne — flat field cap, short bill
        pygame.draw.rect(s, band, (13, 2, 22, 8))
        pygame.draw.rect(s, lit, (13, 2, 22, 1))
        pygame.draw.rect(s, INK, (13, 1, 22, 1))
        pygame.draw.rect(s, band, (11, 9, 26, 2))
        pygame.draw.rect(s, INK, (11, 11, 26, 1))
    elif kind == "garrison":  # Doss — folded side cap, no bill
        pygame.draw.polygon(s, band, [(13, 10), (18, 2), (30, 2), (35, 10)])
        pygame.draw.polygon(s, INK, [(13, 10), (18, 2), (30, 2), (35, 10)], 1)
        pygame.draw.line(s, lit, (19, 4), (29, 4))
    elif kind == "peaked":  # Ashworth — officer's cap, badge and wide bill
        pygame.draw.rect(s, band, (12, 1, 24, 7))
        pygame.draw.rect(s, lit, (12, 1, 24, 1))
        pygame.draw.rect(s, (74, 76, 92), (12, 8, 24, 3))  # cap band
        pygame.draw.rect(s, BRASS, (23, 3, 3, 3))  # badge
        pygame.draw.rect(s, BRASS_D, (23, 6, 3, 1))
        # The bill has to stay lighter than the terminal background or the
        # whole cap reads as floating clear of the head.
        pygame.draw.rect(s, (58, 60, 74), (9, 11, 30, 2))  # bill
        pygame.draw.rect(s, (86, 88, 104), (9, 11, 30, 1))
        pygame.draw.rect(s, INK, (9, 13, 30, 1))
    else:  # bricker — knit beanie, ribbed brim
        pygame.draw.rect(s, band, (13, 3, 22, 8))
        pygame.draw.rect(s, band, (15, 1, 18, 3))
        pygame.draw.rect(s, lit, (15, 1, 18, 1))
        pygame.draw.rect(s, INK, (15, 0, 18, 1))
        pygame.draw.rect(s, lit, (12, 9, 24, 3))  # rolled brim
        pygame.draw.rect(s, INK, (12, 12, 24, 1))
        for x in range(13, 36, 3):
            pygame.draw.rect(s, band, (x, 9, 1, 3))
    return s


def build_portrait(legend, hat, mood):
    s = _bust_base(legend)
    _face(s, legend, mood)
    # Sideburns, under the hat brim — without them every head reads as shaved.
    hair = legend["H"]
    for x in (13, 34):
        pygame.draw.rect(s, hair, (x, 13, 2, 5))
    _headwear(s, legend, hat)
    return s


PORTRAIT_HATS = {
    "thorne": "patrol",
    "doss": "garrison",
    "ashworth": "peaked",
    "bricker": "beanie",
}
_PORTRAIT_LEGENDS = {
    "thorne": THORNE,
    "doss": DOSS,
    "ashworth": ASHWORTH,
    "bricker": BRICKER,
}

PORTRAITS = {
    sid: {m: build_portrait(_PORTRAIT_LEGENDS[sid], PORTRAIT_HATS[sid], m)
          for m in ("steady", "rattled", "cracking")}
    for sid in _PORTRAIT_LEGENDS
}
