"""The Thorne Museum, at four in the morning.

The map is carved rather than typed. Rooms and corridors are cut into a field
of void, then anything still void that touches an interior tile becomes wall.
That way the building is always sealed and the floor plan can be moved around
without recounting a single row of ASCII.
"""

import pygame

import art
from case import CASE
from settings import *

MAP_W, MAP_H = 64, 54

# Floors you can stand on. Everything else stops you.
WALKABLE = {"marble", "marble_d", "wood", "carpet", "path", "grass"}
INTERIOR = {"marble", "marble_d", "wood", "carpet"}


class World:
    def __init__(self):
        self.grid = [["void"] * MAP_W for _ in range(MAP_H)]
        self.tiles = art.build_tiles()
        self.objects = []  # (surface, x, y, sort_y)
        self.blockers = []  # pygame.Rect, world space
        self.interactables = []
        self.lights = []
        self._build()
        self._furnish()
        self.floor = self._bake_floor()

    # --- carving -------------------------------------------------------------

    def _fill(self, x, y, w, h, kind, over=None):
        """Paint a rectangle. `over` limits which tile kinds may be replaced,
        which is how the lawn flows around walls and the paths sit on the lawn
        without eating either."""
        for ty in range(y, y + h):
            for tx in range(x, x + w):
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    if over is not None and self.grid[ty][tx] not in over:
                        continue
                    self.grid[ty][tx] = kind

    def _build(self):
        # Rooms.
        self._fill(6, 3, 22, 14, "wood")  # Conservation Lab B
        self._fill(36, 3, 20, 13, "wood")  # Registrar's archive
        self._fill(22, 22, 20, 16, "marble")  # Atrium
        self._fill(2, 21, 17, 14, "carpet")  # West gallery
        self._fill(45, 23, 14, 12, "marble_d")  # Interview room
        self._fill(26, 41, 12, 6, "marble")  # Entrance hall

        # Corridors.
        self._fill(25, 17, 3, 5, "marble")  # lab -> atrium
        self._fill(38, 16, 3, 6, "marble")  # archive -> atrium
        self._fill(19, 28, 3, 3, "marble")  # gallery <-> atrium
        self._fill(42, 27, 3, 3, "marble")  # atrium <-> interview
        self._fill(30, 38, 4, 3, "marble")  # atrium <-> entrance
        self._fill(50, 35, 3, 9, "marble_d")  # interview -> service exit

        # Seal the building: any void touching a floor becomes wall.
        walls = []
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] != "void":
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < MAP_W and 0 <= ny < MAP_H and self.grid[ny][nx] in INTERIOR:
                            walls.append((x, y))
                            break
                    else:
                        continue
                    break
        for x, y in walls:
            self.grid[y][x] = "wall"

        # Grounds. Fills only what is still void, so it flows around the walls.
        self._fill(1, 1, MAP_W - 2, MAP_H - 2, "grass", over={"void"})

        # Paths, laid over the lawn — never over a wall, or the shell would
        # develop holes the auto-walling has already finished checking for.
        self._fill(44, 45, 15, 7, "path", over={"grass"})
        self._fill(29, 47, 6, 5, "path", over={"grass"})
        self._fill(29, 49, 30, 2, "path", over={"grass"})
        self._fill(20, 49, 9, 2, "path", over={"grass"})

        # A runner from the front doors to the fountain, so the walk in has a
        # line to follow.
        self._fill(31, 29, 2, 9, "carpet")

        # Two doors punched through the shell.
        for tx in (31, 32):
            self.grid[47][tx] = "marble"
        for tx in (51, 52):
            self.grid[44][tx] = "path"

        # A hedge along the boundary so the lawn has an edge.
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] == "grass" and (x <= 2 or y <= 2 or x >= MAP_W - 3 or y >= MAP_H - 3):
                    self.grid[y][x] = "hedge"

    def _bake_floor(self):
        """Draw the whole map once. It never changes, so it never redraws."""
        surf = pygame.Surface((MAP_W * TILE, MAP_H * TILE))
        for y in range(MAP_H):
            for x in range(MAP_W):
                kind = self.grid[y][x]
                if kind == "wall":
                    below = self.grid[y + 1][x] if y + 1 < MAP_H else "void"
                    if below in ("wall", "void"):
                        variants = self.tiles["wall_top"]
                    elif below == "carpet":
                        variants = self.tiles["wainscot"]
                    else:
                        variants = self.tiles["wall"]
                elif kind == "marble":
                    # A checker, so the atrium reads as a floor and not a fill.
                    variants = self.tiles["marble" if (x + y) % 2 == 0 else "marble_d"]
                else:
                    variants = self.tiles.get(kind, self.tiles["void"])
                surf.blit(variants[(x * 7 + y * 3) % len(variants)], (x * TILE, y * TILE))
        return surf

    # --- furniture -----------------------------------------------------------

    def _obj(self, key, tx, ty, ox=0, oy=0, solid=None, sort_pad=0):
        """Place a prop. `solid` is a rect in pixels relative to its top-left."""
        surf = self.props[key] if isinstance(key, str) else key
        x, y = tx * TILE + ox, ty * TILE + oy
        self.objects.append((surf, x, y, y + surf.get_height() + sort_pad))
        if solid is True:
            solid = (0, surf.get_height() // 2, surf.get_width(), surf.get_height() // 2)
        if solid:
            dx, dy, w, h = solid
            self.blockers.append(pygame.Rect(x + dx, y + dy, w, h))
        return pygame.Rect(x, y, surf.get_width(), surf.get_height())

    def _look(self, rect, title, body, evidence=None):
        self.interactables.append(
            {"rect": rect.inflate(12, 12), "title": title, "body": body, "evidence": evidence}
        )

    def _furnish(self):
        self.props = art.objects()

        def put(key, tx, ty, ox=0, oy=0, solid=None, pad=0):
            return self._obj(key, tx, ty, ox, oy, solid, pad)

        def lamp(tx, ty, r=64, ox=8, oy=18):
            self.lights.append((tx * TILE + ox, ty * TILE + oy, r))

        def row(key, txs, ty, **kw):
            for tx in txs:
                put(key, tx, ty, **kw)

        # ---- Conservation Lab B: the crime scene ----------------------------
        # The room was turned over, so half of it is on the floor.
        row("workbench", (6, 9, 12), 3, solid=True)
        row("rack", (16, 18, 20), 3, solid=True)
        put("sink", 23, 3, solid=True)
        put("easel", 25, 3, solid=True)
        row("shelf", (6, 6), 7, solid=True)
        put("shelf", 6, 10, solid=True)
        put("shelf", 6, 13, solid=True)
        put("cabinet", 26, 6, solid=True)
        put("cabinet", 26, 9, solid=True)
        put("workbench", 24, 13, solid=True)
        row("crate", (9, 11), 15, solid=True)
        put("pallet", 13, 15, solid=True)
        put("easel", 20, 12, solid=True)
        put("debris", 15, 6)
        put("debris", 21, 14)
        put("debris", 9, 12)
        put("debris", 18, 9)
        for tx in (8, 14, 20, 26):
            put("sconce", tx, 2, oy=6)
            lamp(tx, 3, 74)
        put("lamp", 7, 12, solid=(2, 24, 12, 6))
        lamp(7, 12, 76, oy=26)
        put("lamp", 25, 10, solid=(2, 24, 12, 6))
        lamp(25, 10, 76, oy=26)

        outline = put("outline", 11, 8, pad=-24)
        put("marker1", 10, 7, pad=-6)
        self._look(
            outline,
            "The outline",
            "Tape on the concrete where Marguerite Vance was found, face down beside the "
            "drying racks. One blow, left temple. She never got up.",
        )

        plinth = put("plinth_empty", 15, 8, solid=(3, 20, 10, 8))
        put("marker2", 17, 10, pad=-6)
        self._look(
            plinth,
            "Stripped plinth",
            "A display plinth with its marble base torn off. The base is in an evidence "
            "bag downtown, with her blood on one corner.",
        )

        phone = put("cabinet", 19, 6, solid=True)
        put("marker3", 21, 8, pad=-6)
        self._look(phone, "Lab extension", CASE["evidence"][1]["found_text"], evidence="phone-call")

        window = pygame.Rect(9 * TILE, 2 * TILE + 4, 3 * TILE, 14)
        put("marker4", 10, 4, pad=-6)
        self._look(
            window,
            "The forced window",
            "Levered open. The splintering is on the inside face and the paint is broken "
            "outward. Whoever did this was standing in the room.",
        )

        # ---- Registrar's archive --------------------------------------------
        for r in (3, 7, 11):
            row("shelf", (37, 39, 41, 43, 45, 47), r, solid=True)
        row("cabinet", (51, 53), 3, solid=True)
        put("desk", 51, 8, solid=True)
        put("chair", 52, 10, solid=(3, 10, 10, 6))
        put("crate", 54, 13, solid=True)
        put("crate", 37, 14, solid=True)
        put("cooler", 55, 7, solid=True)
        for tx in (39, 45, 51):
            put("sconce", tx, 2, oy=6)
            lamp(tx, 3, 74)
        put("lamp", 54, 11, solid=(2, 24, 12, 6))
        lamp(54, 11, 76, oy=26)

        ledger = put("cabinet", 49, 12, solid=True)
        put("marker5", 51, 14, pad=-6)
        self._look(
            ledger, "Acquisition ledgers", CASE["evidence"][4]["found_text"], evidence="bank-transfer"
        )

        # ---- The atrium ------------------------------------------------------
        put("fountain", 29, 26, solid=(4, 18, 40, 20))
        row("banner", (23, 27, 36, 40), 21, oy=2)
        for tx in (25, 30, 34, 39):
            put("sconce", tx, 21, oy=8)
            lamp(tx, 22, 84)
        row("bench", (24, 27), 33, solid=True)
        row("bench", (36, 39), 33, solid=True)
        row("bench", (24, 39), 24, solid=True)
        for tx, ty in ((23, 22), (40, 22), (23, 36), (40, 36)):
            put("plant", tx, ty, solid=True)
        put("case", 25, 29, solid=(0, 12, 32, 10))
        put("case", 37, 29, solid=(0, 12, 32, 10))
        put("stanchion", 27, 25)
        put("stanchion", 36, 25)
        put("cooler", 41, 30, solid=True)

        desk = put("desk", 31, 22, solid=True)
        self._look(desk, "Security terminal", CASE["evidence"][0]["found_text"], evidence="badge-log")

        # ---- West gallery ----------------------------------------------------
        row("painting", (3, 6, 9), 20, oy=6)
        corot = put("corot", 12, 20, oy=6)
        self._look(corot, "Corot landscape", CASE["evidence"][3]["found_text"], evidence="forgery-report")
        put("painting", 16, 20, oy=6)
        put("banner", 2, 21, oy=-4)
        put("banner", 18, 21, oy=-4)
        put("painting_empty", 2, 25, oy=2)
        for tx, ty in ((5, 24), (10, 24), (15, 24), (5, 30), (10, 30), (15, 30)):
            put("plinth", tx, ty, solid=(3, 20, 10, 8))
            put("stanchion", tx, ty + 2)
        put("case", 4, 27, solid=(0, 12, 32, 10))
        put("case", 12, 27, solid=(0, 12, 32, 10))
        put("bench", 4, 33, solid=True)
        put("bench", 12, 33, solid=True)
        put("plant", 2, 33, solid=True)
        put("plant", 17, 33, solid=True)
        for tx in (4, 10, 16):
            put("sconce", tx, 20, oy=1)
            lamp(tx, 21, 80)

        # ---- Interview room --------------------------------------------------
        put("mirror", 48, 22, oy=6)
        put("table", 49, 28, solid=(0, 6, 48, 14))
        put("chair", 51, 31, solid=(3, 10, 10, 6))
        put("lamp", 46, 24, solid=(2, 24, 12, 6))
        lamp(46, 24, 92, oy=26)
        put("cabinet", 57, 24, solid=True)
        put("cabinet", 57, 27, solid=True)
        put("cooler", 46, 32, solid=True)
        put("plant", 57, 32, solid=True)
        put("sconce", 53, 22, oy=8)
        lamp(53, 23, 76)

        # ---- Entrance hall ---------------------------------------------------
        put("desk", 31, 41, solid=True)
        row("bench", (27, 34), 44, solid=True)
        put("plant", 26, 41, solid=True)
        put("plant", 37, 41, solid=True)
        put("banner", 29, 40, oy=4)
        put("banner", 35, 40, oy=4)
        for tx in (27, 36):
            put("sconce", tx, 40, oy=8)
            lamp(tx, 41, 76)

        # ---- Loading dock ----------------------------------------------------
        dump = put("dumpster", 46, 46, solid=(0, 8, 32, 14))
        self._look(dump, "Dumpster", CASE["evidence"][2]["found_text"], evidence="glove")
        put("dumpster", 55, 46, solid=(0, 8, 32, 14))
        row("crate", (45, 46), 49, solid=True)
        put("crate", 45, 50, solid=True)
        put("pallet", 53, 49, solid=True)
        put("pallet", 56, 50, solid=True)
        put("crate", 57, 48, solid=True)
        put("lamp", 44, 45, solid=(2, 24, 12, 6))
        lamp(44, 45, 84, oy=26)
        put("lamp", 58, 45, solid=(2, 24, 12, 6))
        lamp(58, 45, 84, oy=26)

        # ---- The grounds -----------------------------------------------------
        for tx, ty in (
            (4, 18), (9, 18), (20, 18), (31, 18), (43, 18), (52, 18), (60, 18),
            (4, 42), (9, 45), (16, 41), (21, 46), (40, 42), (60, 30),
            (33, 19), (43, 36), (43, 41), (20, 40),
            (3, 36), (8, 38), (13, 37), (18, 44), (25, 42), (5, 48), (16, 50),
            (46, 41), (54, 41), (60, 46), (60, 24),
        ):
            put("tree", tx, ty, solid=(6, 26, 14, 10))
        for tx, ty in (
            (6, 20), (12, 20), (24, 20), (36, 20), (48, 19), (56, 20),
            (7, 40), (13, 43), (24, 44), (39, 45), (42, 33), (42, 22),
            (18, 48), (26, 49), (38, 49), (12, 50),
        ):
            put("bush", tx, ty, solid=(2, 6, 12, 8))
        for tx, ty in ((10, 48), (14, 47), (23, 48), (36, 48), (41, 48), (8, 43), (44, 40)):
            put("flowers", tx, ty)
        put("bench", 27, 48, solid=True)
        put("bench", 34, 48, solid=True)
        for tx, ty in ((28, 47), (35, 47), (29, 51), (35, 51), (46, 49), (56, 49)):
            put("lamp", tx, ty, solid=(2, 24, 12, 6))
            lamp(tx, ty, 78, oy=26)

    # --- queries -------------------------------------------------------------

    def solid_at(self, rect):
        """True if this world rect overlaps a wall or a blocking prop."""
        x0, y0 = rect.left // TILE, rect.top // TILE
        x1, y1 = (rect.right - 1) // TILE, (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if not (0 <= tx < MAP_W and 0 <= ty < MAP_H):
                    return True
                if self.grid[ty][tx] not in WALKABLE:
                    return True
        return rect.collidelist(self.blockers) != -1

    def interactable_near(self, point):
        """The closest thing worth pressing E on, or None."""
        best, best_d = None, INTERACT_RANGE**2
        for it in self.interactables:
            if it["rect"].collidepoint(point):
                return it
            cx = max(it["rect"].left, min(point[0], it["rect"].right))
            cy = max(it["rect"].top, min(point[1], it["rect"].bottom))
            d = (cx - point[0]) ** 2 + (cy - point[1]) ** 2
            if d < best_d:
                best, best_d = it, d
        return best
