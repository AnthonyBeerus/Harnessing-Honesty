"""Create a local source/evidence ZIP and per-file hashes; never overwrite.

Only explicitly selected project directories are included. Credentials, local
environments, Git metadata, caches and worker logs are excluded. This packages
evidence; it does not authenticate a freeze or publish an archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = args.output.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    paths = []
    for name in ('src', 'config', 'docs', 'scripts', 'tests', 'notebooks', 'data'):
        directory = root/name
        if directory.exists():
            paths.extend(p for p in directory.rglob('*') if p.is_file())
    paths.extend(p for p in root.iterdir() if p.is_file() and p.name in (
        'README.md','pyproject.toml','LICENSE','LICENSE.md','.gitignore','AGENTS.md'))
    exclusions = {'__pycache__','.ipynb_checkpoints','.pytest_cache','.venv','.git'}
    paths = sorted(set(p for p in paths if not exclusions.intersection(p.relative_to(root).parts)
        and p.suffix not in ('.pyc','.log') and not p.name.startswith('.env')), key=str)
    manifest = {'purpose':'Local reproducibility evidence; not a public release or freeze authentication',
                'files':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for p in paths:
            archive.write(p,p.relative_to(root).as_posix())
        archive.writestr('EVIDENCE_MANIFEST.json',json.dumps(manifest,indent=2))
    sidecar = destination.with_suffix('.manifest.json')
    if sidecar.exists():
        raise FileExistsError(sidecar)
    sidecar.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'{len(paths)} files; {destination.stat().st_size:,} bytes: {destination}')


if __name__ == '__main__':
    main()
