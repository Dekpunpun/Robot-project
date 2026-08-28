"""Harrow's Reach, the night the vault came up five cases short.

The map is carved rather than typed. Rooms and corridors are cut into a field
of void, then anything still void that touches an interior tile becomes wall.
That way the city's five buildings are always sealed and the layout can be
moved around without recounting a single row of ASCII.
"""

import pygame

import art
from case import CASE, EVIDENCE_BY_ID
from settings import *

MAP_W, MAP_H = 64, 54

# Floors you can stand on. Everything else stops you.
WALKABLE = {"marble_d", "wood", "carpet", "path", "grass"}
INTERIOR = {"marble_d", "wood", "carpet"}


class World:
    def __init__(self):
        self.grid = [["void"] * MAP_W for _ in range(MAP_H)]
        self.tiles = art.build_tiles()
        self.objects = []  # (surface, x, y, sort_y)
        self.blockers = []  # pygame.Rect, world space
        self.interactables = []
        self.lights = []
        self.npc_spots = {}  # sid -> {"x", "y", "rect", "blocker"}
        self._build()
        self._furnish()
        self.floor = self._bake_floor()

    # --- carving -------------------------------------------------------------

    def _fill(self, x, y, w, h, kind, over=None):
        """Paint a rectangle. `over` limits which tile kinds may be replaced,
        which is how the grass flows around walls and the paths sit on the
        grass without eating either."""
        for ty in range(y, y + h):
            for tx in range(x, x + w):
                if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                    if over is not None and self.grid[ty][tx] not in over:
                        continue
                    self.grid[ty][tx] = kind

    def _build(self):
        # Buildings.
        self._fill(4, 3, 16, 9, "marble_d")  # Fort Callow - Special Weapons Vault
        self._fill(44, 3, 16, 9, "carpet")  # Fort Callow - Command Office
        self._fill(24, 40, 16, 8, "wood")  # Third Precinct
        self._fill(4, 30, 9, 11, "wood")  # 14 Milner Street - kitchen
        self._fill(13, 30, 8, 11, "marble_d")  # 14 Milner Street - garage
        self._fill(43, 30, 14, 10, "wood")  # Salt Row - Dock 4, the fishing cabin

        # Corridors — each pokes one building out to a doorway in the yard.
        self._fill(10, 12, 3, 7, "marble_d")  # vault -> yard
        self._fill(50, 12, 3, 7, "carpet")  # command office -> yard
        self._fill(30, 34, 3, 6, "wood")  # precinct -> yard
        self._fill(7, 41, 3, 5, "wood")  # Milner Street -> yard
        self._fill(48, 40, 3, 5, "wood")  # Salt Row -> yard

        # Seal the city: any void touching a floor becomes wall.
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

        # Paths, laid over the grass — never over a wall, or the shell would
        # develop holes the auto-walling has already finished checking for.
        # A wide spine along the top, linking the vault and command office...
        self._fill(9, 18, 45, 3, "path", over={"grass"})
        # ...down the middle to the precinct...
        self._fill(29, 18, 4, 17, "path", over={"grass"})
        # ...down the left to Milner Street...
        self._fill(9, 18, 4, 28, "path", over={"grass"})
        # ...and down the right to Salt Row.
        self._fill(49, 18, 4, 27, "path", over={"grass"})
        # Harborview Square: a plaza where all five roads meet.
        self._fill(24, 18, 18, 9, "path", over={"grass"})

        # A hedge along the boundary so the grounds have an edge.
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] == "grass" and (x <= 2 or y <= 2 or x >= MAP_W - 3 or y >= MAP_H - 3):
                    self.grid[y][x] = "hedge"

        # Doors. Each corridor above ends one row short of the path network,
        # so the sealing pass above walls that row shut — reopen exactly that
        # row on each of the five, same trick as the wall it just punched.
        for tx in (10, 11, 12):
            self.grid[19][tx] = "path"  # vault -> yard
        for tx in (50, 51, 52):
            self.grid[19][tx] = "path"  # command office -> yard
        for tx in (30, 31, 32):
            self.grid[33][tx] = "path"  # precinct -> yard
        for tx in (7, 8, 9):
            self.grid[46][tx] = "path"  # Milner Street -> yard
        for tx in (48, 49, 50):
            self.grid[45][tx] = "path"  # Salt Row -> yard

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

    def _npc_spot(self, sid, tx, ty, ox=8, oy=20):
        """Reserve a standing spot for one of the four suspects. `main.py`
        builds the NPC instance and its interactable from this."""
        x, y = tx * TILE + ox, ty * TILE + oy
        self.npc_spots[sid] = {
            "x": x,
            "y": y,
            "rect": pygame.Rect(x - 12, y - 26, 24, 26).inflate(16, 16),
            "blocker": pygame.Rect(x - 7, y - 10, 14, 10),
        }

    def _furnish(self):
        self.props = art.objects()

        def put(key, tx, ty, ox=0, oy=0, solid=None, pad=0):
            return self._obj(key, tx, ty, ox, oy, solid, pad)

        def lamp(tx, ty, r=64, ox=8, oy=18):
            self.lights.append((tx * TILE + ox, ty * TILE + oy, r))

        def row(key, txs, ty, **kw):
            for tx in txs:
                put(key, tx, ty, **kw)

        # ---- Fort Callow: Special Weapons Vault ------------------------------
        row("shelf", (5, 5), 4, solid=True)
        put("shelf", 5, 7, solid=True)
        put("cabinet", 18, 4, solid=True)
        put("cabinet", 18, 7, solid=True)
        put("crate", 6, 10, solid=True)
        put("crate", 8, 10, solid=True)
        for tx in (7, 12, 17):
            put("sconce", tx, 3, oy=6)
            lamp(tx, 4, 70)
        put("lamp", 6, 9, solid=(2, 24, 12, 6))
        lamp(6, 9, 74, oy=26)

        terminal = put("vault_terminal", 15, 8, solid=True)
        self._look(terminal, "Vault checkout terminal", EVIDENCE_BY_ID["vault-ledger"]["found_text"], evidence="vault-ledger")

        camera = put("camera_console", 8, 5, solid=True)
        self._look(camera, "Gate camera terminal", EVIDENCE_BY_ID["gate-camera"]["found_text"], evidence="gate-camera")

        self._npc_spot("doss", 15, 10)

        # ---- Fort Callow: Command Office --------------------------------------
        put("desk", 51, 6, solid=True)
        put("chair", 52, 8, solid=(3, 10, 10, 6))
        put("cabinet", 46, 5, solid=True)
        put("cabinet", 46, 8, solid=True)
        put("plant", 57, 9, solid=True)
        put("cooler", 57, 5, solid=True)
        for tx in (47, 51, 56):
            put("sconce", tx, 3, oy=6)
            lamp(tx, 4, 70)
        put("banner", 45, 4, oy=-2)
        put("banner", 58, 4, oy=-2)

        self._npc_spot("ashworth", 51, 10)

        # ---- Third Precinct (home base) --------------------------------------
        put("desk", 31, 43, solid=True)
        row("bench", (26, 35), 45, solid=True)
        put("shelf", 25, 42, solid=True)
        put("shelf", 38, 42, solid=True)
        put("banner", 27, 41, oy=4)
        put("banner", 36, 41, oy=4)
        for tx in (27, 31, 36):
            put("sconce", tx, 41, oy=8)
            lamp(tx, 42, 74)

        # ---- 14 Milner Street: the Thorne house --------------------------------
        # Kitchen.
        mess = put("kitchen_mess", 6, 36, solid=True)
        self._look(mess, "The kitchen", EVIDENCE_BY_ID["struggle-kitchen"]["found_text"], evidence="struggle-kitchen")
        put("shelf", 4, 32, solid=True)
        put("cooler", 10, 32, solid=True)
        put("sconce", 8, 30, oy=6)
        lamp(8, 31, 64)

        # Garage.
        put("crate", 15, 32, solid=True)
        put("crate", 18, 32, solid=True)
        put("pallet", 16, 38, solid=True)
        phone = put("burner_phone", 19, 34, pad=-4)
        self._look(phone, "Behind the paint shelf", EVIDENCE_BY_ID["burner-phone"]["found_text"], evidence="burner-phone")
        photo = put("photo_facedown", 19, 36, pad=-4)
        self._look(photo, "A photo, face down", EVIDENCE_BY_ID["proof-of-life-photo"]["found_text"], evidence="proof-of-life-photo")
        put("lamp", 14, 38, solid=(2, 24, 12, 6))
        lamp(14, 38, 68, oy=26)

        self._npc_spot("bricker", 8, 43)  # loitering by the street, not inside

        # ---- Salt Row, Dock 4: the fishing cabin -------------------------------
        put("table", 46, 33, solid=True)
        put("chair", 48, 35, solid=(3, 10, 10, 6))
        put("crate", 44, 37, solid=True)
        put("crate", 55, 37, solid=True)
        put("pallet", 53, 32, solid=True)
        put("lamp", 45, 32, solid=(2, 24, 12, 6))
        lamp(45, 32, 74, oy=26)
        put("lamp", 55, 32, solid=(2, 24, 12, 6))
        lamp(55, 32, 74, oy=26)

        self._npc_spot("thorne", 49, 36)

        # ---- Harborview Square (the roads between everything) ------------------
        put("fountain", 29, 20, solid=(4, 18, 40, 20))
        row("bench", (26, 36), 26, solid=True)
        for tx, ty in ((25, 19), (39, 19), (25, 25), (39, 25)):
            put("plant", tx, ty, solid=True)
        for tx in (27, 33, 39):
            put("sconce", tx, 19, oy=8)
            lamp(tx, 20, 80)

        # The matchbook, dropped roadside where the gate footage caught the
        # handoff — between the vault and the square, not inside either.
        matchbook = put("matchbook", 16, 20, pad=-4)
        self._look(matchbook, "A matchbook in the gravel", EVIDENCE_BY_ID["matchbook"]["found_text"], evidence="matchbook")

        # ---- The grounds -----------------------------------------------------
        for tx, ty in (
            (5, 15), (10, 15), (22, 15), (34, 15), (42, 15), (52, 15), (60, 15),
            (5, 46), (11, 48), (16, 44), (26, 50), (40, 46), (60, 30),
            (33, 16), (43, 40), (43, 46), (20, 44),
            (3, 40), (13, 41), (18, 48), (25, 46), (5, 50), (16, 50),
            (46, 45), (54, 45), (60, 46), (60, 24),
        ):
            put("tree", tx, ty, solid=(6, 26, 14, 10))
        for tx, ty in (
            (7, 24), (13, 24), (20, 24), (36, 24), (44, 19), (56, 24),
            (14, 47), (24, 48), (39, 49), (42, 33), (42, 24),
            (18, 50), (26, 51), (38, 51), (12, 50),
        ):
            put("bush", tx, ty, solid=(2, 6, 12, 8))
        for tx, ty in ((10, 50), (14, 49), (23, 50), (36, 50), (41, 50), (8, 47)):
            put("flowers", tx, ty)
        for tx, ty in ((8, 15), (18, 15), (30, 15), (46, 15), (58, 15), (8, 48), (58, 48)):
            put("lamp", tx, ty, solid=(2, 24, 12, 6))
            lamp(tx, ty, 74, oy=26)

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
