"""Check static website links and media controls without a browser or game data."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []
        self.controls = []
        self.errors = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                self.errors.append(f"Duplicate id: {attrs['id']}")
            self.ids.add(attrs['id'])
        for key in ('href', 'src', 'poster', 'data-still', 'data-gif'):
            if attrs.get(key):
                self.refs.append(attrs[key])
        if 'data-toggle' in attrs:
            self.controls.append(attrs['data-toggle'])
        if tag == 'img' and 'alt' not in attrs:
            self.errors.append('Image is missing alt text')
        if tag == 'video':
            if 'controls' not in attrs:
                self.errors.append('Video must expose playback controls')
            if 'autoplay' in attrs:
                self.errors.append('Showcase videos must not autoplay')


def check(root):
    root = Path(root).resolve()
    errors = []
    pages = {}
    for file in root.rglob('*'):
        if file.is_symlink():
            errors.append(f'Symlink cannot be packaged: {file.relative_to(root)}')
    for file in root.rglob('*.html'):
        page = Page()
        page.feed(file.read_text(encoding='utf-8'))
        pages[file.resolve()] = page
        errors.extend(f'{file.name}: {error}' for error in page.errors)
    if root / 'index.html' not in pages:
        errors.append('Missing index.html')
    for file, page in pages.items():
        for target_id in page.controls:
            if target_id not in page.ids:
                errors.append(f'{file.name}: missing GIF target #{target_id}')
        for ref in page.refs:
            parts = urlsplit(ref)
            if parts.scheme or parts.netloc:
                continue
            if parts.path.startswith('/'):
                errors.append(f'{file.name}: root-relative URL breaks project hosting: {ref}')
                continue
            target = (file.parent / unquote(parts.path)).resolve() if parts.path else file
            if not target.is_relative_to(root):
                errors.append(f'{file.name}: link leaves published directory: {ref}')
            elif not target.is_file():
                errors.append(f'{file.name}: missing asset: {ref}')
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f'{file.name}: missing anchor: {ref}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'website/dist')
    args = parser.parse_args()
    errors = check(args.directory)
    if errors:
        parser.exit(1, '\n'.join(errors) + '\n')
    print('Website checks passed: entrypoint, local assets, anchors and media controls.')


if __name__ == '__main__':
    main()
