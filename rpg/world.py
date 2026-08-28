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
WALKABLE = {"marble_d", "wood", "carpet", "path", "grass", "concrete", "labfloor"}
INTERIOR = {"marble_d", "wood", "carpet", "concrete", "labfloor"}


class Building:
    """One structure on the map, described in a single place.

    Give it its rooms and the corridor that pokes out to the street, and
    everything downstream is derived: the zone tag that lifts the roof when
    you walk in, the wall shell the sealing pass builds around it, the door
    punched back through that shell, the title card the entry cutscene
    shows, and the approach lane that furniture is forbidden to block.

    Before this existed all five of those lived in separate hand-typed
    lists, which is how a tree ended up parked inside the vault doorway and
    sealed the building shut.
    """

    def __init__(self, zone, title, subtitle, rooms, corridor, style="military"):
        self.zone = zone
        self.title = title
        self.subtitle = subtitle
        self.rooms = rooms  # [(x, y, w, h, floor)]
        self.corridor = corridor  # (x, y, w, h, floor)
        self.style = style  # which roof material this building wears

    @property
    def _exits_south(self):
        """True when the corridor leaves from the bottom of the building."""
        cx, cy, cw, ch, _ = self.corridor
        return cy >= max(y + h for _, y, _, h, _ in self.rooms)

    @property
    def door_row(self):
        """The row the sealing pass walls shut and the door punches back open:
        one tile past the far end of the corridor."""
        _, cy, _, ch, _ = self.corridor
        return cy + ch if self._exits_south else cy - 1

    @property
    def door_tiles(self):
        cx, _, cw, _, _ = self.corridor
        return [(x, self.door_row) for x in range(cx, cx + cw)]

    @property
    def approach(self):
        """Every tile that has to stay walkable for the building to be usable:
        the corridor, its door, and the step of street just outside it."""
        cx, cy, cw, ch, _ = self.corridor
        tiles = [(x, y) for x in range(cx, cx + cw) for y in range(cy, cy + ch)]
        tiles += self.door_tiles
        outside = self.door_row + 1 if self._exits_south else self.door_row - 1
        tiles += [(x, outside) for x in range(cx, cx + cw)]
        return tiles


BUILDINGS = [
    Building("vault", "FORT CALLOW", "SPECIAL WEAPONS VAULT",
             rooms=[(4, 3, 16, 9, "concrete")], corridor=(10, 12, 3, 7, "concrete"),
             style="military"),
    Building("command", "FORT CALLOW", "COMMAND OFFICE",
             rooms=[(44, 3, 16, 9, "carpet")], corridor=(50, 12, 3, 7, "carpet"),
             style="military"),
    Building("precinct", "THIRD PRECINCT", "HOME BASE",
             rooms=[(24, 40, 16, 8, "wood")], corridor=(30, 34, 3, 6, "wood"),
             style="civic"),
    Building("milner", "14 MILNER STREET", "THE THORNE HOUSE",
             rooms=[(4, 30, 9, 11, "wood"), (13, 30, 8, 11, "marble_d")],
             corridor=(7, 41, 3, 5, "wood"), style="house"),
    Building("saltrow", "SALT ROW, DOCK 4", "THE FISHING CABIN",
             rooms=[(43, 30, 14, 10, "wood")], corridor=(48, 40, 3, 5, "wood"),
             style="cabin"),
    # Held two tiles clear of the vault: with the wall shell included, roofs
    # that abut read as one long slab instead of three separate buildings.
    Building("motorpool", "FORT CALLOW", "MOTOR POOL",
             rooms=[(24, 3, 14, 9, "concrete")], corridor=(26, 12, 3, 6, "concrete"),
             style="military"),
    Building("lab", "HARROW'S REACH P.D.", "FORENSICS",
             rooms=[(43, 24, 5, 3, "labfloor")], corridor=(44, 22, 3, 2, "labfloor"),
             style="lab"),
]


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
        self.roofs = self._bake_roofs()

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
        self.zone_grid = [[None] * MAP_W for _ in range(MAP_H)]
        self.zone_names = {b.zone: (b.title, b.subtitle) for b in BUILDINGS}

        def zone_fill(x, y, w, h, kind, zone, over=None):
            self._fill(x, y, w, h, kind, over)
            for ty in range(y, y + h):
                for tx in range(x, x + w):
                    if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                        self.zone_grid[ty][tx] = zone

        # Every building carves itself: rooms first, then the corridor that
        # takes it out to the street.
        for b in BUILDINGS:
            for x, y, w, h, floor in b.rooms:
                zone_fill(x, y, w, h, floor, b.zone)
            cx, cy, cw, ch, floor = b.corridor
            zone_fill(cx, cy, cw, ch, floor, b.zone)

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

        # Doors. Each corridor ends one row short of the path network, so the
        # sealing pass above walls that row shut — punch exactly that row back
        # open. The row is derived from the corridor, so moving a building
        # moves its door with it.
        for b in BUILDINGS:
            for tx, ty in b.door_tiles:
                self.grid[ty][tx] = "path"

        # The lanes furniture may never stand in. Anything with a collision box
        # that lands here would seal a building shut from the outside, which is
        # exactly how a decorative tree once locked the vault.
        self._keep_clear = [
            pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
            for b in BUILDINGS
            for tx, ty in b.approach
        ]

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

        # Kerbs. A road with no edge reads as a grey shape painted on grass;
        # a raised lip along every ground-facing side turns the same tiles
        # into a street.
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.grid[y][x] != "path":
                    continue
                px, py = x * TILE, y * TILE
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < MAP_W and 0 <= ny < MAP_H):
                        continue
                    if self.grid[ny][nx] not in ("grass", "hedge"):
                        continue
                    if dy:  # horizontal kerb, lit on top and shadowed beneath
                        ky = py if dy < 0 else py + TILE - 3
                        pygame.draw.rect(surf, STONE_L, (px, ky, TILE, 2))
                        pygame.draw.rect(surf, STONE_D, (px, ky + 2, TILE, 1))
                    else:
                        kx = px if dx < 0 else px + TILE - 3
                        pygame.draw.rect(surf, STONE_L, (kx, py, 2, TILE))
                        pygame.draw.rect(surf, STONE_D, (kx + 2, py, 1, TILE))
        return surf

    def _bake_roofs(self):
        """One roof surface per building, baked once.

        A building's roof covers its own tiles plus the wall shell around them,
        so from outside you see a closed structure rather than a lit room with
        no lid. `main` draws every roof except the one the player is standing
        under, which is what makes walking through a door feel like entering.
        """
        members = {}
        for y in range(MAP_H):
            for x in range(MAP_W):
                z = self.zone_grid[y][x]
                if z:
                    members.setdefault(z, set()).add((x, y))
        for tiles in members.values():
            shell = set()
            for x, y in tiles:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < MAP_W and 0 <= ny < MAP_H and self.grid[ny][nx] == "wall":
                            shell.add((nx, ny))
            tiles |= shell
        self.zone_tiles = members

        # Two roofs that touch read as one long slab rather than as separate
        # buildings, so they are kept a tile apart.
        zones = list(members)
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                touching = {(x + dx, y + dy) for x, y in members[a]
                            for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & members[b]
                if touching:
                    raise ValueError(
                        f"roofs of {a!r} and {b!r} touch at {sorted(touching)[0]} — "
                        f"leave a tile of ground between them"
                    )

        by_zone = {b.zone: b for b in BUILDINGS}
        roofs = {}
        self.chimneys = []
        for zone, tiles in members.items():
            roofs[zone] = self._bake_exterior(by_zone[zone], tiles)
        return roofs

    # Overhang below the eave, where the roof throws a shadow onto the ground.
    EAVE_DROP = 5
    # How many rows at the bottom of a building are wall rather than roof.
    FACADE_ROWS = 2

    def _dress_facade(self, building, surf, tx, px, wall_top, wall_bottom, door_cols):
        """One door at the middle of the entrance, windows along the rest.

        Every door column getting a door gave the house three front doors in
        a row, so the door goes on the centre column only and the flanking
        ones stay blank wall rather than falling through to a window.
        """
        props = art.objects()
        if tx in door_cols:
            if tx == sorted(door_cols)[len(door_cols) // 2]:
                surf.blit(props[f"door_{building.style}"], (px + 1, wall_bottom - 22))
        elif tx % 3 == 1:
            surf.blit(props[f"window_{building.style}"], (px + 2, wall_top + 8))

    def _bake_exterior(self, building, tiles):
        """Draw one building as a pitched structure rather than a flat lid.

        Each column of the footprint gets its own ridge, halfway down that
        column, so an L-shaped building with a corridor still reads as a roof
        rather than as a rectangle. The back slope sits in shadow, the ridge
        catches the light, the front slope runs down to a dark eave, and the
        whole thing drops a shadow onto the ground below it.
        """
        pal = art.ROOF_STYLES[building.style]
        shingles = art.build_roof_tiles(building.style)
        self._facade = [art.facade_tile(building.style, i) for i in range(3)]
        x0 = min(t[0] for t in tiles)
        y0 = min(t[1] for t in tiles)
        w = max(t[0] for t in tiles) - x0 + 1
        h = max(t[1] for t in tiles) - y0 + 1
        surf = pygame.Surface((w * TILE, h * TILE + self.EAVE_DROP), pygame.SRCALPHA)

        cols = {}
        for x, y in tiles:
            cols.setdefault(x, []).append(y)

        # Ground shadow first, so the roof lands on top of it.
        shadow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for x, ys in cols.items():
            px = (x - x0) * TILE
            shadow.fill((0, 0, 0, 96), (px + 2, (max(ys) - y0 + 1) * TILE, TILE, self.EAVE_DROP))
        surf.blit(shadow, (0, 0))

        door_cols = {x for x, _ in building.door_tiles}
        for x, ys in cols.items():
            top, bottom = min(ys), max(ys)
            # The bottom rows of every column are wall, not roof — that front
            # face is what stops the building reading as paper on the ground.
            wall_from = max(top + 1, bottom - self.FACADE_ROWS + 1)
            roof_rows = [y for y in ys if y < wall_from]
            ridge = (top + max(roof_rows)) // 2 if roof_rows else top
            px = (x - x0) * TILE
            reach = max(1, (max(roof_rows) - top) / 2) if roof_rows else 1

            for y in roof_rows:
                py = (y - y0) * TILE
                slope = "back" if y <= ridge else "front"
                bank = shingles[slope]
                surf.blit(bank[(x * 7 + y * 3) % len(bank)], (px, py))
                # Both slopes fall away from the ridge. Without this the two
                # halves read as flat two-tone bands rather than a pitch.
                fall = abs(y - ridge) / reach
                dim = int((48 if slope == "back" else 34) * fall)
                if dim:
                    shade = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                    shade.fill((8, 8, 14, dim))
                    surf.blit(shade, (px, py))
            if roof_rows:
                ry = (ridge - y0) * TILE
                pygame.draw.rect(surf, pal["cap"], (px, ry, TILE, 3))
                pygame.draw.rect(surf, pal["trim"], (px, ry + 3, TILE, 1))

            # The wall itself, then the eave shadow the roof throws across it.
            for y in range(wall_from, bottom + 1):
                surf.blit(self._facade[(x * 5 + y) % len(self._facade)],
                          (px, (y - y0) * TILE))
            wy = (wall_from - y0) * TILE
            pygame.draw.rect(surf, pal["eave"], (px, wy - 3, TILE, 5))
            shade = pygame.Surface((TILE, 6), pygame.SRCALPHA)
            shade.fill((8, 8, 14, 90))
            surf.blit(shade, (px, wy + 2))
            by = (bottom - y0 + 1) * TILE
            pygame.draw.rect(surf, pal["wall_d"], (px, by - 2, TILE, 2))  # footing

            self._dress_facade(building, surf, x, px, wy, by, door_cols)

        # Gable trim down the outside edges of every column run.
        for x, ys in cols.items():
            px = (x - x0) * TILE
            for edge, ex in (((x - 1) not in cols, px), ((x + 1) not in cols, px + TILE - 1)):
                if edge:
                    for y in ys:
                        py = (y - y0) * TILE
                        pygame.draw.rect(surf, pal["trim"], (ex, py, 1, TILE))

        self._fit_roof(building, surf, cols, x0, y0, pal)
        return surf, x0 * TILE, y0 * TILE

    def _fit_roof(self, building, surf, cols, x0, y0, pal):
        """Chimneys, vents and signage — what tells one roof from another."""
        props = art.objects()
        rx, ry, rw, rh, _ = building.rooms[0]

        if pal.get("chimney"):
            cx, cy = rx + 1, ry + 1
            px, py = (cx - x0) * TILE, (cy - y0) * TILE
            surf.blit(props["chimney"], (px, py - 4))
            # Remembered in world pixels so the smoke can animate above it.
            self.chimneys.append((cx * TILE + 5, cy * TILE - 4, building.zone))

        if pal.get("vents"):
            for i in range(1, 4):
                vx = rx + (rw * i) // 4
                if vx in cols:
                    surf.blit(props["roof_vent"], ((vx - x0) * TILE + 2, (ry + 1 - y0) * TILE))

        if pal.get("sign"):
            # Hung off the eave directly over the doorway.
            dx = building.corridor[0]
            row = min(cols[dx]) if building._exits_south else max(cols[dx])
            surf.blit(props["roof_sign"], ((dx - x0) * TILE - 5, (row - y0) * TILE + 4))

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
            box = pygame.Rect(x + dx, y + dy, w, h)
            if box.collidelist(self._keep_clear) != -1:
                raise ValueError(
                    f"prop {key!r} at tile ({tx},{ty}) blocks a building "
                    f"approach lane — move it clear of the doorway"
                )
            self.blockers.append(box)
        return pygame.Rect(x, y, surf.get_width(), surf.get_height())

    def _look(self, rect, title, body, evidence=None):
        """Register something the player can press E on.

        Two lookable props whose reach overlaps are a silent trap: the game
        returns whichever centre is nearer, so one of them becomes
        unreachable and its evidence uncollectable. That is what an arms
        rack once did to the gate camera, so it is refused outright here.
        """
        reach = rect.inflate(12, 12)
        for other in self.interactables:
            if reach.colliderect(other["rect"]):
                raise ValueError(
                    f"interactable {title!r} overlaps {other['title']!r} — "
                    f"one of them would be unreachable"
                )
        self.interactables.append(
            {"rect": reach, "title": title, "body": body, "evidence": evidence}
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
        # An armoury, not a study: steel racking and locked cabinets, no
        # bookshelves and no reading lamps.
        put("steel_shelf", 5, 4, solid=True)
        put("steel_shelf", 5, 7, solid=True)
        put("gun_locker", 18, 4, solid=True)
        put("gun_locker", 18, 7, solid=True)
        put("ammo_crate", 6, 10, solid=True)
        put("ammo_crate", 8, 10, solid=True)
        put("sandbags", 16, 10, solid=(2, 4, 16, 7))
        for tx in (7, 12, 17):
            put("sconce", tx, 3, oy=6)
            lamp(tx, 4, 70)

        put("munitions_crate", 12, 10, solid=True)
        put("munitions_crate", 14, 4, solid=True)
        # Kept clear of the camera console at (8,5): two lookable props whose
        # rects overlap and the nearer one silently swallows the other.
        rack = put("weapon_rack", 11, 4, solid=True)
        self._look(rack, "The arms rack",
                   "Serial-stencilled slots, every one of them signed for. Two stand "
                   "empty tonight, and the dust in them is a different age.")

        terminal = put("vault_terminal", 15, 8, solid=True)
        self._look(terminal, "Vault checkout terminal", EVIDENCE_BY_ID["vault-ledger"]["found_text"], evidence="vault-ledger")

        camera = put("camera_console", 8, 5, solid=True)
        self._look(camera, "Gate camera terminal", EVIDENCE_BY_ID["gate-camera"]["found_text"], evidence="gate-camera")

        # At his post by the checkout terminal, not blocking the doorway.
        self._npc_spot("doss", 16, 6)

        # ---- Harrow's Reach P.D.: Forensics -----------------------------------
        bench = put("lab_bench", 43, 25, solid=True)
        self._look(bench, "The forensics bench",
                   "Someone has been working the matchbook mark against the Compact's "
                   "last two jobs. The comparison is pinned up half-finished, and the "
                   "burner is still lit.")
        # The room is three rows deep — the roof has to clear the command
        # office above it and Salt Row below — so it gets the three fittings
        # that say "lab" and no more.
        put("specimen_cabinet", 43, 24, solid=True)
        put("microscope", 46, 26, pad=-4)
        put("sconce", 45, 24, oy=4)
        lamp(45, 25, 62)

        # ---- Fort Callow: Motor Pool ------------------------------------------
        # Bricker's shop, and where the truck from the gate footage is parked.
        truck = put("truck", 31, 4, solid=(2, 20, 22, 18))
        self._look(truck, "A 2.5-ton in the end bay",
                   "Motor pool log says it has not moved in a week. The odometer says "
                   "otherwise, and someone has wiped the bed out with solvent - it is "
                   "the only clean thing in the building.")
        put("workbench", 25, 9, solid=True)
        put("shelf", 24, 4, solid=True)
        for tx in (28, 30):
            put("oil_drum", tx, 9, solid=(1, 8, 10, 7))
        put("crate", 34, 9, solid=True)
        put("pallet", 27, 4, solid=True)
        for tx in (24, 29, 34):
            put("sconce", tx, 3, oy=6)
            lamp(tx, 4, 70)

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
        wallmap = put("wallmap", 53, 3, oy=4)
        self._look(wallmap, "Wall map of Harrow's Reach",
                   "The whole district under glass. Someone has pushed a single red pin "
                   "into Salt Row, down by the water, and left it there.")

        # Behind her own desk — a battalion commander receives you, she doesn't
        # meet you at the door.
        self._npc_spot("ashworth", 52, 5)

        # ---- Third Precinct (home base) --------------------------------------
        put("desk", 31, 43, solid=True)
        put("chair_up", 32, 45, solid=(3, 10, 10, 6))
        put("desk", 35, 46, solid=True)
        row("bench", (26, 35), 45, solid=True)
        put("shelf", 25, 42, solid=True)
        put("shelf", 38, 42, solid=True)
        put("cabinet", 34, 41, solid=True)
        put("cooler", 24, 46, solid=True)
        put("banner", 36, 41, oy=4)
        board = put("corkboard", 26, 41, oy=4)
        self._look(board, "The case board",
                   "Five photographs, a duty roster, and a torn-off map corner, strung "
                   "together in red. Your own handwriting on most of it. None of it "
                   "yet says who.")
        for tx in (27, 31, 36):
            put("sconce", tx, 41, oy=8)
            lamp(tx, 42, 74)

        # ---- 14 Milner Street: the Thorne house --------------------------------
        # Kitchen.
        mess = put("kitchen_mess", 6, 36, solid=True)
        self._look(mess, "The kitchen", EVIDENCE_BY_ID["struggle-kitchen"]["found_text"], evidence="struggle-kitchen")
        put("shelf", 4, 32, solid=True)
        put("cooler", 10, 32, solid=True)
        put("stove", 8, 32, solid=True)
        put("table", 5, 39, solid=True)
        put("chair", 9, 38, solid=(3, 10, 10, 6))
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

        # Out on the street rather than in the hallway — he is not in this house,
        # he is hanging around outside it.
        self._npc_spot("bricker", 12, 44)

        # ---- Salt Row, Dock 4: the fishing cabin -------------------------------
        put("table", 45, 33, solid=True)
        put("chair", 47, 35, solid=(3, 10, 10, 6))
        put("bunk", 44, 30, solid=True)
        put("stove", 50, 31, solid=True)
        lamp(50, 32, 52, oy=12)
        put("crate", 55, 37, solid=True)
        put("pallet", 52, 38, solid=True)
        put("lamp", 45, 32, solid=(2, 24, 12, 6))
        lamp(45, 32, 74, oy=26)
        put("lamp", 55, 32, solid=(2, 24, 12, 6))
        lamp(55, 32, 74, oy=26)
        # The dock itself, out front of the cabin.
        for tx in (44, 47, 53, 56):
            put("bollard", tx, 41, solid=(3, 8, 6, 6))

        # Deep in the cabin, backed into the far corner away from the door.
        self._npc_spot("thorne", 53, 35)

        # ---- Harborview Square (the roads between everything) ------------------
        put("fountain", 29, 20, solid=(4, 18, 40, 20))
        row("bench", (26, 36), 26, solid=True)
        # The upper pair sits inboard of the motor pool doorway at x25-27.
        for tx, ty in ((29, 19), (37, 19), (25, 25), (39, 25)):
            put("plant", tx, ty, solid=True)
        for tx in (27, 33, 39):
            put("sconce", tx, 19, oy=8)
            lamp(tx, 20, 80)

        # The matchbook, dropped roadside where the gate footage caught the
        # handoff — between the vault and the square, not inside either.
        matchbook = put("matchbook", 16, 20, pad=-4)
        self._look(matchbook, "A matchbook in the gravel", EVIDENCE_BY_ID["matchbook"]["found_text"], evidence="matchbook")

        # ---- The grounds -----------------------------------------------------
        # Nothing goes on the approach rows to the Fort Callow doors (x10-12 and
        # x50-52): a canopy there reaches down over the corridor mouth and seals
        # the building shut.
        for tx, ty in (
            (5, 15), (22, 15), (34, 15), (42, 15), (60, 15),
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

        # ---- the street itself ------------------------------------------------
        # Utility poles down both sides of the spine, with the wires strung
        # between them. Kept off the roadway so nothing blocks a crossing.
        self.wires = []
        for row, xs in ((17, (14, 21, 36, 45)), (21, (14, 21, 36, 41))):
            last = None
            for tx in xs:
                put("pole", tx, row, solid=(3, 30, 4, 5))
                top = (tx * TILE + 5, row * TILE + 8)
                if last:
                    self.wires.append((last, top))
                last = top

        for tx, ty in ((13, 21), (35, 17), (40, 21)):
            put("bin", tx, ty, solid=(1, 8, 10, 6))
        for tx, ty in ((20, 19), (33, 26), (44, 19)):
            put("drain", tx, ty)
        for tx, ty in ((15, 19), (42, 21)):
            put("hydrant", tx, ty, solid=(1, 8, 6, 5))
        for tx, ty in ((8, 15), (18, 15), (30, 15), (46, 15), (58, 15), (8, 48), (58, 48)):
            put("lamp", tx, ty, solid=(2, 24, 12, 6))
            lamp(tx, ty, 74, oy=26)

    # --- queries -------------------------------------------------------------

    def zone_at(self, x, y):
        """Which building (if any) this world point falls inside — used to
        fire the "entering a building" cutscene at the right doorway."""
        tx, ty = int(x) // TILE, int(y) // TILE
        if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
            return self.zone_grid[ty][tx]
        return None

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

    def interactable_near(self, point, zone=None):
        """The closest thing worth pressing E on, or None.

        Only things sharing the player's building count: with roofs on, a
        terminal you cannot see through a wall should not be reachable either.
        """
        best, best_d = None, INTERACT_RANGE**2
        for it in self.interactables:
            if self.zone_at(it["rect"].centerx, it["rect"].centery) != zone:
                continue
            if it["rect"].collidepoint(point):
                return it
            cx = max(it["rect"].left, min(point[0], it["rect"].right))
            cy = max(it["rect"].top, min(point[1], it["rect"].bottom))
            d = (cx - point[0]) ** 2 + (cy - point[1]) ** 2
            if d < best_d:
                best, best_d = it, d
        return best
