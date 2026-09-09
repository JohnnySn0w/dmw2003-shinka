"""Directional hints for the verified PAL evolution requirements.

Offline companion to the native chart hints in src/evolution_chart.c. Callers
supply names only for forms they are allowed to reveal. Numeric requirements
stay in the internal record and never enter the hint text.
"""
from dataclasses import dataclass
import hashlib
import struct
from configure_exp import OVERLAY_SHA256

ROOKIES = ('Kotemon', 'Kumamon', 'Monmon', 'Agumon', 'Veemon', 'Guilmon', 'Renamon', 'Patamon')
TABLE = 0x80087A3C - 0x80082CB0
ROWS = 44

DIRECTIONS = {
    1: 'Develop greater strength.',
    2: 'Build your physical defenses.',
    3: 'Strengthen your spirit.',
    4: 'Cultivate your wisdom.',
    5: 'Develop your speed.',
    6: 'Develop your charisma.',  # Supported vocabulary; no current table uses it.
    7: 'Grow stronger alongside your partner.',
    8: 'Train your affinity with fire.',
    9: 'Train your affinity with water.',
    10: 'Train your affinity with ice.',
    11: 'Train your affinity with wind.',
    12: 'Train your affinity with thunder.',
    13: 'Train your affinity with machines.',
    14: 'Train your affinity with darkness.',
}


@dataclass(frozen=True)
class Requirement:
    destination: int
    forms: tuple  # (form ID, required skill level), never rendered directly
    extra_type: int
    extra_value: int


def read_requirements(overlay):
    """Read all eight rookie tables, rejecting unsupported disc revisions."""
    if hashlib.sha256(overlay).hexdigest() != OVERLAY_SHA256:
        raise ValueError('Unsupported reward overlay')
    result = {}
    for rookie_index, rookie in enumerate(ROOKIES):
        entries = []
        for row in range(ROWS):
            offset = TABLE + (rookie_index * ROWS + row) * 16
            to, reserved, a, al, b, bl, kind, value = struct.unpack_from('<8H', overlay, offset)
            if reserved != 0 or kind not in (0, *DIRECTIONS):
                raise ValueError('Unrecognized evolution requirement')
            forms = tuple((form, level) for form, level in ((a, al), (b, bl)) if form)
            entries.append(Requirement(to, forms, kind, value))
        result[rookie] = entries
    return result


def hints(requirement, revealed_names):
    """Describe directions without thresholds, progress meters or hidden names.

The caller filters out unlocked destinations. Revealed names are a view policy,
not a complete ID-to-name dictionary. Two-form prerequisites describe training
both forms; they do not imply the player must use the DNA attack in battle.
"""
    result = []
    hidden = False
    for form, _level in requirement.forms:
        name = revealed_names.get(form)
        if name:
            result.append(f'Deepen your mastery of {name}.')
        else:
            hidden = True
    if hidden:
        result.append('Explore other evolution paths.')
    if requirement.extra_type:
        try:
            result.append(DIRECTIONS[requirement.extra_type])
        except KeyError as error:
            raise ValueError('Unknown hint direction') from error
    return list(dict.fromkeys(result))
