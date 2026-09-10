"""Attach hash-identified scene context to offline soundtrack auditions."""
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / 'assets/music/track-locations.json'


def track_context(midi_sha256, catalog=CATALOG):
    data = json.loads(catalog.read_text(encoding='utf-8'))
    matches = [t for t in data['tracks'] if t['midi_sha256'] == midi_sha256]
    if len(matches) != 1:
        return None  # Never select a title from a filename or an ambiguous digest.
    track = matches[0]
    return {key: track[key] for key in (
        'id', 'title', 'scene', 'listening_focus', 'label_status',
        'runtime_scene_verified')}


def listening_notes(context, backend):
    palette = {'soundfont': 'Instrumental / Sampled', 'ds': 'DS-inspired',
               'chip': 'Chip'}.get(backend, backend)
    if context is None:
        return (f'# Unidentified track — {palette}\n\n'
                'No unique MIDI hash match in the scene catalog. Identify the '
                'actual screen before judging scene fit.\n')
    title = context['title']
    status = ('The full source sequence matches a community-tagged reference. '
              'All in-game uses have not been verified.'
              if context['label_status'] == 'exact_sequence_match_to_community_tag'
              else 'Scene identity is unconfirmed; do not infer it from the filename.')
    return (f'# {title} — {palette}\n\n'
            f'Disc ID: `{context["id"]}`\n\n'
            f'{context["scene"]}\n\n'
            f'**Listen for:** {context["listening_focus"]}\n\n'
            f'{status}\n\n'
            'These are proposed arrangement goals, not a completed listening verdict.\n\n'
            'Feedback: scene fit / lead character / bass and percussion / loop fatigue.\n')
