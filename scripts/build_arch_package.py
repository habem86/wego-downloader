#!/usr/bin/env python3
"""Build a pure-Python Arch package and a source archive without root/makepkg."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = '0.1.1'
PACKAGE = 'honda-map-downloader-linux'
PAYLOAD = {
    'honda_maps.py': (f'usr/lib/{PACKAGE}/honda_maps.py', 0o644),
    'honda_maps_gui.py': (f'usr/lib/{PACKAGE}/honda_maps_gui.py', 0o644),
    'honda-maps': ('usr/bin/honda-maps', 0o755),
    'honda-maps-gui': ('usr/bin/honda-maps-gui', 0o755),
    'honda-map-downloader-linux.desktop': ('usr/share/applications/honda-map-downloader-linux.desktop', 0o644),
    'README.md': (f'usr/share/doc/{PACKAGE}/README.md', 0o644),
    'USAGE.md': (f'usr/share/doc/{PACKAGE}/USAGE.md', 0o644),
    'VALIDATION.txt': (f'usr/share/doc/{PACKAGE}/VALIDATION.txt', 0o644),
    'LICENSE': (f'usr/share/licenses/{PACKAGE}/LICENSE', 0o644),
}
SOURCES = sorted(set(PAYLOAD) | {
    'PKGBUILD', 'test_honda_maps.py', 'scripts/build_arch_package.py',
    '.github/workflows/ci.yml', '.github/workflows/release.yml', 'RELEASE_NOTES.md', '.gitignore',
})

def add(archive, name, data, mode, epoch):
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = mode
    member.uid = member.gid = 0
    member.uname = member.gname = 'root'
    member.mtime = epoch
    archive.addfile(member, io.BytesIO(data))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if 'SOURCE_DATE_EPOCH' in os.environ:
        epoch = int(os.environ['SOURCE_DATE_EPOCH'])
    else:
        epoch = int(subprocess.check_output(['git', 'log', '-1', '--format=%ct'], cwd=ROOT, text=True).strip())
    payload = [(dest, (ROOT / src).read_bytes(), mode) for src, (dest, mode) in PAYLOAD.items()]
    size = sum(len(data) for _, data, _ in payload)
    info = f'''pkgname = {PACKAGE}
pkgbase = {PACKAGE}
pkgver = {VERSION}-1
pkgdesc = Experimental native Linux client for Honda bonneville EU NDS map downloads
builddate = {epoch}
packager = wego-downloader compatibility project
size = {size}
arch = any
license = MIT
depend = python>=3.10
depend = tk
optdepend = xdg-utils: register the portal launch protocol
'''.encode()
    package = args.output / f'{PACKAGE}-{VERSION}-1-any.pkg.tar.xz'
    with tarfile.open(package, 'w:xz', format=tarfile.USTAR_FORMAT) as archive:
        add(archive, '.PKGINFO', info, 0o644, epoch)
        for name, data, mode in sorted(payload):
            add(archive, name, data, mode, epoch)
    source = args.output / f'{PACKAGE}-{VERSION}-source.tar.xz'
    with tarfile.open(source, 'w:xz', format=tarfile.USTAR_FORMAT) as archive:
        for name in SOURCES:
            add(archive, f'{PACKAGE}-{VERSION}/{name}', (ROOT / name).read_bytes(), 0o644, epoch)
    checksums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in [package, source])
    (args.output / 'SHA256SUMS').write_text(checksums)
    print(checksums, end='')

if __name__ == '__main__':
    main()
