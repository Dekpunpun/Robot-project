"""Window, timing and colour constants.

Everything is authored at 1x — 16 pixel tiles, 16 wide characters — and the
whole frame is scaled up once at blit time with nearest-neighbour. That keeps
every edge on the pixel grid no matter what the window is doing.
"""

import os
import sys


def asset(name):
    """Path to a bundled file.

    PyInstaller unpacks data files into a temporary folder and points
    `sys._MEIPASS` at it, so a frozen build cannot look next to this source
    file the way a normal run does.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


TILE = 16

# Internal resolution, in tiles. The window is this times SCALE.
VIEW_W, VIEW_H = 24, 15
SCREEN_W, SCREEN_H = VIEW_W * TILE, VIEW_H * TILE

SCALE = 3
FPS = 60

TITLE = "The Vesper Manifest"

# --- palette -----------------------------------------------------------------
# A night museum: cold stone and warm lamplight, with the detective's coat the
# only saturated thing on screen.

INK = (24, 18, 30)  # outline black; nothing is ever pure #000
SHADOW = (38, 32, 52)

NIGHT = (16, 18, 34)
NIGHT_2 = (26, 28, 50)

GRASS = (58, 104, 66)
GRASS_D = (42, 82, 54)
GRASS_L = (86, 138, 78)

HEDGE = (36, 70, 48)
HEDGE_L = (56, 98, 62)

STONE = (108, 106, 122)
STONE_D = (78, 76, 94)
STONE_L = (140, 138, 154)

MARBLE = (198, 194, 186)
MARBLE_D = (166, 160, 154)
MARBLE_L = (224, 220, 210)

WOOD = (124, 84, 54)
WOOD_D = (92, 60, 38)
WOOD_L = (154, 110, 72)

CARPET = (118, 40, 44)
CARPET_D = (86, 26, 32)
CARPET_L = (150, 60, 58)

WALL = (74, 72, 96)
WALL_D = (52, 50, 72)
WALL_L = (104, 102, 128)

LAMP = (255, 214, 130)
LAMP_D = (206, 158, 74)
GLOW = (255, 232, 170)

BRASS = (188, 148, 70)
BRASS_D = (138, 102, 44)

TAPE = (232, 196, 62)
BLOOD = (128, 34, 38)

PAPER = (232, 226, 206)
PAPER_D = (196, 188, 164)

UI_BG = (22, 20, 36)
UI_BG_2 = (34, 32, 56)
UI_LINE = (92, 90, 132)
UI_HI = (128, 126, 176)
UI_TEXT = (233, 231, 214)
UI_DIM = (152, 160, 204)
UI_FAINT = (98, 106, 155)
ACCENT = (255, 204, 51)
DANGER = (228, 69, 58)
COOL = (79, 195, 247)
GREEN = (106, 212, 106)

# --- gameplay ----------------------------------------------------------------

WALK_SPEED = 62.0  # pixels per second, world space
RUN_SPEED = 108.0
INTERACT_RANGE = 22  # pixels from the player's feet
