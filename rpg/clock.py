"""The night itself. Never shown as a HUD readout — the player reads the hour
off how dark it's gotten and off what people tell them, so every value here
exists to drive some other system (light, weather, prompts, schedules), not
to be printed on screen.
"""

START_MIN = 20 * 60          # 20:00
END_MIN = START_MIN + 252    # 00:12, the hour the case fiction points at

# One in-game minute per real minute played (1:1), so idling is never free,
# plus per-action jumps that dominate the budget for anyone actually working
# the case. Tune these together against a real playtest, not in isolation.
DRIP_MIN_PER_SEC = 1 / 60
COST_QUESTION = 3
COST_PRESENT = 2
COST_ENTER_BUILDING = 3
COST_EXAMINE = 1

# Phases the night moves through. Each is keyed by the in-game minute it
# starts at (minutes since START_MIN) and carries everything downstream reads:
# how dark the world gets, what fraction of lamps survive, how weather should
# lean, and how much a suspect's own willingness to move is damped.
PHASES = [
    (0,   {"name": "evening",   "dark_alpha": 132, "tint": (10, 12, 30), "lamp_frac": 1.00, "weather_bias": 0.0,  "damp": 1.00}),
    (90,  {"name": "night",     "dark_alpha": 158, "tint": (8, 10, 28),  "lamp_frac": 1.00, "weather_bias": 0.15, "damp": 0.90}),
    (150, {"name": "late",      "dark_alpha": 184, "tint": (7, 8, 24),   "lamp_frac": 0.75, "weather_bias": 0.35, "damp": 0.75}),
    (210, {"name": "small_hrs", "dark_alpha": 205, "tint": (5, 6, 20),   "lamp_frac": 0.50, "weather_bias": 0.55, "damp": 0.60}),
]


class Clock:
    """Minutes elapsed since START_MIN. Nothing here formats for display —
    that would invite putting it on the HUD, which the design deliberately
    avoids."""

    def __init__(self):
        self.minutes = 0.0

    def tick(self, dt):
        """dt is real seconds elapsed this frame."""
        self.minutes += dt * DRIP_MIN_PER_SEC

    def advance(self, minutes):
        self.minutes += minutes

    @property
    def absolute(self):
        """Minutes since midnight the previous day, for schedule comparisons."""
        return START_MIN + self.minutes

    def past(self, hh, mm=0):
        """True once the clock has reached hh:mm. hh is in 24h wall-clock
        terms but may be e.g. 0 for the post-midnight stretch, which this
        resolves against the START_MIN wraparound correctly."""
        target = hh * 60 + mm
        if target < START_MIN:
            target += 24 * 60
        return self.absolute >= target

    @property
    def phase(self):
        cur = PHASES[0][1]
        for start, data in PHASES:
            if self.minutes >= start:
                cur = data
            else:
                break
        return cur

    @property
    def hhmm(self):
        """Debug/verification use only — never render this to the player."""
        total = int(self.absolute) % (24 * 60)
        return f"{total // 60:02d}:{total % 60:02d}"
