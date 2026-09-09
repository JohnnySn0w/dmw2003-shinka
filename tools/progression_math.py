"""Readable positive-input formulas reconstructed from the PAL reward overlay.

These explain the original game; the runtime still executes its own routines.
See docs/progression.md for addresses, thresholds and validation limits.
"""
ROOKIE_GROWTH = dict(Kotemon=8, Kumamon=10, Monmon=6, Agumon=9,
                    Veemon=8, Guilmon=7, Renamon=7, Patamon=9)


def rookie_threshold(level, growth):
    """Minimum cumulative EXP to enter a level (the guest compares strictly >)."""
    if not 1 <= level <= 99 or growth not in (6, 7, 8, 9, 10):
        raise ValueError('Unsupported rookie level or growth coefficient')
    if level == 1:
        return 0
    band = 0 if level < 5 else 50 if level < 20 else 800 if level < 40 else 3000
    return (growth * (level ** 3 + 5 * level - 6)) // 10 + band + 1


def dv_threshold(level, natural_limit=100):
    """Minimum cumulative DV EXP to enter a skill level."""
    if not 1 <= level <= 99 or not 1 <= natural_limit <= 100:
        raise ValueError('Unsupported skill level or natural limit')
    return 10 * min(level - 1, natural_limit - 1) + 50 * max(0, level - natural_limit)


def dv_award(base, rookie_level, participants=1, skill_level=1, natural_limit=100):
    """Original final DV award, before Shinka's independent multiplier."""
    if base < 0 or not 1 <= rookie_level <= 99 or not 1 <= participants <= 9:
        raise ValueError('Unsupported DV award input')
    raw = (10 * base) // min(rookie_level, 50)
    if participants == 2:
        raw = raw * 6 // 10
    elif participants > 2:
        raw //= participants
    return max(1, min(raw, 10 if skill_level < natural_limit else 50))
