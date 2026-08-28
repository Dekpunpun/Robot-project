"""Generate the application icon from the game's own art.

Run this only when the sprite changes:  python3 rpg/make_icon.py
It writes icon.png, and (on macOS) icon.icns. icon.ico needs Pillow.
"""

import os
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

pygame.init()
pygame.display.set_mode((64, 64))

import art
from settings import ACCENT, INK, NIGHT, NIGHT_2

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 1024


def build():
    """A 32x32 pixel image, scaled up hard so the icon stays visibly 8-bit."""
    src = 32
    s = pygame.Surface((src, src))
    s.fill(NIGHT)
    for y in range(0, src, 2):
        pygame.draw.line(s, NIGHT_2, (0, y), (src, y))
    pygame.draw.rect(s, INK, (0, 0, src, src), 2)
    pygame.draw.rect(s, ACCENT, (2, 2, src - 4, src - 4), 1)

    sprite = art.build_actor(
        art.DET_DOWN, art.DET_UP, art.DET_SIDE, art.LEGS_FRONT, art.LEGS_SIDE, art.DET
    )["down"][0]
    # A lamp pool behind him, the same trick the game uses in the rooms.
    glow = art.make_light(11, strength=70)
    s.blit(glow, (16 - 11, 20 - 11), special_flags=pygame.BLEND_RGBA_ADD)
    s.blit(sprite, ((src - sprite.get_width()) // 2, src - sprite.get_height() - 3))
    return pygame.transform.scale(s, (SIZE, SIZE))


icon = build()
png = os.path.join(HERE, "icon.png")
pygame.image.save(icon, png)
print("wrote", png)

if sys.platform == "darwin":
    iconset = os.path.join(HERE, "icon.iconset")
    os.makedirs(iconset, exist_ok=True)
    for px in (16, 32, 64, 128, 256, 512, 1024):
        scaled = pygame.transform.scale(icon, (px, px))
        pygame.image.save(scaled, os.path.join(iconset, f"icon_{px}x{px}.png"))
        if px <= 512:
            pygame.image.save(scaled, os.path.join(iconset, f"icon_{px // 2}x{px // 2}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(HERE, "icon.icns")], check=True)
    print("wrote", os.path.join(HERE, "icon.icns"))

try:
    from PIL import Image

    Image.open(png).save(
        os.path.join(HERE, "icon.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote", os.path.join(HERE, "icon.ico"))
except ImportError:
    print("Pillow not installed - skipping icon.ico (needed only for Windows builds)")
