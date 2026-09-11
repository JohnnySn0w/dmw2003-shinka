"""Guard authored live instrument routes against the owned export's identity."""
from pathlib import Path

from music_export import require

ROUTING = Path(__file__).resolve().parents[1] / 'assets/music/live-routing.json'


def bank_overrides(name, metadata, profile):
    require(profile.get('schema') == 1 and isinstance(profile.get('banks'), dict),
            'Unsupported live routing profile')
    bank = profile['banks'].get(name)
    if bank is None:
        return {}
    require(bank.get('inputs') == metadata['inputs'], f'Live routing source mismatch: {name}')
    routes = bank.get('samples')
    require(isinstance(routes, dict) and routes, f'Empty live routing profile: {name}')
    samples = {str(sample['id']) for sample in metadata['bank']['samples']}
    for sample, route in routes.items():
        require(sample in samples, f'Unknown live routing sample: {name}/{sample}')
        owners = sorted({program['program'] for program in metadata['bank']['programs']
                         if any(str(tone['sample']) == sample for tone in program['tones'])})
        require(owners and route.get('programs') == owners,
                f'Live routing owner mismatch: {name}/{sample}')
        require(route.get('soundfont') in ('piano', 'strings', 'clarinet', 'bass')
                and route.get('chip') in ('wave', 'pulse', 'square', 'triangle'),
                f'Unsupported pitched live route: {name}/{sample}')
        require(isinstance(route.get('reason'), str) and route['reason'].strip(),
                f'Missing live routing rationale: {name}/{sample}')
    return routes
