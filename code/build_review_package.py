"""Build and verify a local review bundle from an explicit file allowlist.

This is not a public release builder: manuscripts and derived pilot tables are
included for the owner to review. Raw third-party data and downloaded full texts
are excluded. No remote repository or sharing action is performed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PATTERNS = (
    'README_先读我.md', 'PACKAGE_SCOPE.md', 'REPRODUCIBLE_RUNBOOK.md', 'LICENSE',
    'CITATION.cff', '.gitignore',
    'DATASETS_AND_LINKS.csv', 'progress_checkpoint_2026-09-14.md',
    'progress_checkpoint_2026-09-15.md', 'requirements*.txt',
    'code/*.py', 'tests/*.py', 'configs/*.json', 'protocol/*.md', 'protocol/*.json',
    'protocol/*.csv', 'outputs/*.json', 'outputs/*.csv', 'outputs/*.md',
    'outputs/gates/*.json', 'outputs/gates/*.md', 'outputs/unit_tests.txt',
    'sources/source_ledger.csv',
    'submission/*.md', 'submission/*.tex', 'submission/*.pdf', 'submission/*.ps1',
    'submission/Highlights.txt',
    'manuscript/*.md', 'manuscript/*.tex', 'manuscript/*.pdf', 'manuscript/*.json',
    'manuscript/*.csl', 'manuscript/*.ps1',
    'paper_figures/figure_specs/*', 'paper_figures/src/*', 'paper_figures/reviews/*',
    'paper_figures/output/*.svg', 'paper_figures/output/*.pdf', 'paper_figures/output/*.png', 'paper_figures/output/*.csv',
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = root / args.manifest
    if not args.verify_only:
        files = sorted({p.resolve() for pattern in PATTERNS for p in root.glob(pattern) if p.is_file()})
        if any(not p.is_relative_to(root) for p in files):
            raise ValueError('included file resolves outside the project')
        lines = ['# Internal review manifest; raw third-party archives excluded', '']
        lines.extend(f'{digest(p)}  {p.relative_to(root).as_posix()}' for p in files)
        manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    records = []
    for line in manifest.read_text(encoding='utf-8-sig').splitlines():
        if not line or line.startswith('#'):
            continue
        expected, name = line.split('  ', 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path) != expected:
            raise ValueError(f'manifest mismatch: {name}')
        records.append((name, expected))
    print(f'manifest_entries={len(records)}; mismatches=0')
    if args.archive:
        archive = args.archive.resolve()
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix(archive.suffix + '.tmp')
        with ZipFile(temporary, 'w', ZIP_DEFLATED, compresslevel=6) as z:
            for name, _ in records:
                z.write(root / name, name)
            z.write(manifest, manifest.name)
        with ZipFile(temporary) as z:
            if z.testzip() is not None:
                raise ValueError('ZIP CRC check failed')
            for name, expected in records:
                if hashlib.sha256(z.read(name)).hexdigest() != expected:
                    raise ValueError(f'ZIP hash mismatch: {name}')
        temporary.replace(archive)
        archive.with_suffix(archive.suffix + '.sha256').write_text(
            f'{digest(archive)}  {archive.name}\n', encoding='utf-8')
        print(f'archive={archive}; bytes={archive.stat().st_size}; verified_entries={len(records) + 1}')


if __name__ == '__main__':
    main()


