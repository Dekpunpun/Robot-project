"""The detective, and the man waiting for her."""

import pygame

import art
from settings import *


class Player:
    """Position is the point between the boots, which is also the sort key."""

    W, H = 16, 23
    FOOT = pygame.Rect(0, 0, 10, 6)

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.facing = "down"
        self.frame = 0.0
        self.moving = False
        self.frames = art.build_actor(
            art.DET_DOWN, art.DET_UP, art.DET_SIDE, art.LEGS_FRONT, art.LEGS_SIDE, art.DET
        )

    @property
    def feet(self):
        r = self.FOOT.copy()
        r.center = (int(self.x), int(self.y) - 3)
        return r

    def update(self, dt, dx, dy, world, running=False):
        speed = (RUN_SPEED if running else WALK_SPEED) * dt
        if dx and dy:  # keep diagonals the same speed as the straights
            speed *= 0.7071
        self.moving = bool(dx or dy)

        if dy:
            self.facing = "down" if dy > 0 else "up"
        if dx:
            self.facing = "right" if dx > 0 else "left"

        # Axes are resolved separately so a wall never stops the other one.
        if dx:
            self.x += dx * speed
            if world.solid_at(self.feet):
                self.x -= dx * speed
        if dy:
            self.y += dy * speed
            if world.solid_at(self.feet):
                self.y -= dy * speed

        if self.moving:
            self.frame = (self.frame + dt * (9 if running else 6.5)) % 4
        else:
            self.frame = 0.0

    def draw(self, surf, camera):
        img = self.frames[self.facing][int(self.frame)]
        x = int(self.x) - self.W // 2 - camera[0]
        y = int(self.y) - self.H - camera[1]
        # A flat shadow so the sprite is planted on the floor rather than
        # floating above it.
        shadow = pygame.Surface((12, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), (0, 0, 12, 5))
        surf.blit(shadow, (int(self.x) - 6 - camera[0], int(self.y) - 4 - camera[1]))
        surf.blit(img, (x, y))

    @property
    def sort_y(self):
        return self.y


class NPC:
    """One of the four people the detective can question. None of them walk
    anywhere; they're found standing wherever the case puts them."""

    def __init__(self, sid, x, y, calm, broken):
        self.id = sid
        self.x, self.y = x, y
        self.calm = calm
        self.broken = broken
        self.mood = "steady"
        self.shake = 0.0

    def hit(self):
        self.shake = 0.32

    def update(self, dt):
        self.shake = max(0.0, self.shake - dt)

    @property
    def rect(self):
        return pygame.Rect(self.x - 10, self.y - 20, 20, 24)

    @property
    def sort_y(self):
        return self.y

    def draw(self, surf, camera, tick):
        img = self.broken if self.mood == "cracking" else self.calm
        ox = 0
        if self.shake > 0:
            ox = 1 if (tick // 2) % 2 else -1
        # He breathes: a one-pixel bob, faster once he is rattled.
        rate = 34 if self.mood == "steady" else 16
        bob = 1 if (tick // rate) % 2 else 0
        surf.blit(
            img,
            (int(self.x) - img.get_width() // 2 - camera[0] + ox,
             int(self.y) - img.get_height() - camera[1] + bob),
        )
