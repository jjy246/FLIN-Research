#!/usr/bin/env python3
"""Validate internal relative Markdown links and expected cross-platform assets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    'flin_desktop.py', 'requirements.txt', 'start_windows.bat',
    'start_macos.command', 'start_linux.sh', 'scripts/build_native.py',
    'docs/FLIN_THEORY.md', 'docs/USER_GUIDE.md', 'docs/PLATFORM_SUPPORT.md',
    '.github/workflows/native-builds.yml', '.github/workflows/python-ci.yml',
)
issues = []
for item in REQUIRED:
    if not (ROOT / item).is_file():
        issues.append(f'Missing expected asset: {item}')
for document in [ROOT / 'README.md', ROOT / 'CONTRIBUTING.md', ROOT / 'LICENSING.md', ROOT / 'SECURITY.md', *sorted((ROOT / 'docs').glob('*.md'))]:
    for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        url = match.group(1).split('#', 1)[0].strip()
        if not url or url.startswith(('http:', 'https:', 'mailto:')):
            continue
        if not (document.parent / url).exists():
            issues.append(f'{document.relative_to(ROOT)}: missing link {url}')
for issue in issues:
    print('ERROR:', issue)
print(f'FLIN repository validation: {len(issues)} error(s)')
raise SystemExit(1 if issues else 0)
