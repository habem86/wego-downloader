#!/usr/bin/env python3
"""Unofficial native Linux client for HERE Honda bonneville NDS catalogs.
Python 3.10+, standard library only. No drive formatting or license modification.
"""
import argparse
import hashlib
from http.client import HTTPException
from http.cookiejar import CookieJar
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, urlencode
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor

BLOCK = 1024 * 1024

class DownloadError(Exception):
    pass

def digest(path):
    h = hashlib.md5()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(BLOCK), b''):
            h.update(block)
    return h.hexdigest()

def https_url(value):
    if not isinstance(value, str):
        raise DownloadError('Missing URL.')
    p = urlsplit(value.strip())
    if p.scheme == 'heremapdownloaderv2':
        p = p._replace(scheme='https')
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise DownloadError('An HTTPS or heremapdownloaderv2 URL is required.')
    return urlunsplit(p)

def request(url, offset=0):
    headers = {'User-Agent': 'HondaMapsLinux/0.1', 'Accept-Encoding': 'identity'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    r = urlopen(Request(url, headers=headers), timeout=60)
    if urlsplit(r.geturl()).scheme != 'https':
        r.close()
        raise DownloadError('Insecure HTTP redirect rejected.')
    return r

def link_from_vin(vin, accepted=False):
    if not accepted:
        raise DownloadError('Read https://legal.here.com/en-gb/terms and explicitly accept the HERE terms before submitting a VIN.')
    vin = vin.strip().upper()
    if not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', vin):
        raise DownloadError('VIN must contain 17 valid letters/digits.')
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    base = 'https://www.navigation.com'
    home = base + '/web/WFS/Shop-HondaEMEA-Site/en_GB/-/EUR/ViewHASDKHomepage-Home?HASDKProgramID=bonneville'
    def read(url, data=None):
        req = Request(url, data=data, headers={'User-Agent': 'HondaMapsLinux/0.1', 'Referer': home})
        with opener.open(req, timeout=60) as response:
            if urlsplit(response.geturl()).scheme != 'https':
                raise DownloadError('Insecure portal redirect rejected.')
            content = response.read(4 * BLOCK + 1)
        if len(content) > 4 * BLOCK:
            raise DownloadError('Portal response too large.')
        return content.decode('utf-8', errors='replace')
    read(base + '/language-selection/en_US/HondaEMEA/USD?CountryCode=CZ&Language=en_GB')
    form_page = read(home)
    class Portal(HTMLParser):
        def __init__(self):
            super().__init__(); self.form = False; self.action = None; self.fields = {}; self.links = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'form' and attrs.get('id') == 'hasdk-homepage':
                self.form = True; self.action = attrs.get('action')
            if self.form and tag == 'input' and attrs.get('type') == 'hidden' and attrs.get('name'):
                self.fields[attrs['name']] = attrs.get('value', '')
            if tag == 'a' and attrs.get('href', '').startswith('heremapdownloaderv2:'):
                self.links.append(attrs['href'])
        def handle_endtag(self, tag):
            if tag == 'form': self.form = False
    form = Portal(); form.feed(form_page)
    expected = base + '/web/WFS/Shop-HondaEMEA-Site/en_GB/-/EUR/ViewHASDKHomepage-Start'
    if form.action != expected:
        raise DownloadError('Expected Czech/European VIN form not found. Use a launch link from the portal instead.')
    fields = dict(form.fields, VIN=vin, DBVersion='', termsConditions='on', TermsConditionrequired='true')
    result = Portal(); result.feed(read(expected, urlencode(fields).encode()))
    if not result.links:
        raise DownloadError('Portal did not issue a download link. Check VIN, vehicle Online Services, eligibility, or try the portal in a browser.')
    links = set(result.links)
    if len(links) != 1:
        raise DownloadError('Portal offered multiple links; choose the update in a browser.')
    return links.pop()

def catalog_from_url(url):
    with request(https_url(url)) as r:
        data = r.read(16 * BLOCK + 1)
    if len(data) > 16 * BLOCK:
        raise DownloadError('Catalog exceeds 16 MiB.')
    return json.loads(data)

def plan(catalog):
    if not isinstance(catalog, dict):
        raise DownloadError('Catalog must be a JSON object.')
    params = catalog.get('parameters', {})
    if params.get('program') != 'bonneville' or params.get('market') != 'EU':
        raise DownloadError('This client supports only Honda bonneville EU NDS catalogs.')
    groups = catalog.get('distribution')
    if not isinstance(groups, dict):
        raise DownloadError('Missing distribution object.')
    files, seen = [], set()
    for group in groups.values():
        if not isinstance(group, dict) or not isinstance(group.get('links'), list):
            raise DownloadError('Unsupported distribution group.')
        for link in group['links']:
            if not isinstance(link, dict) or link.get('rel') not in ('nds.file', 'nds.drm'):
                raise DownloadError('Unsupported relation in catalog; nothing was written.')
            name = link.get('otherAttributes', {}).get('local-id')
            if not isinstance(name, str) or not name or '\\' in name or ':' in name:
                raise DownloadError('Invalid local-id.')
            parts = name.split('/')
            if any(p in ('', '.', '..') or any(ord(c) < 32 for c in p) for p in parts):
                raise DownloadError('Unsafe local-id.')
            if name.casefold() in seen:
                raise DownloadError('Duplicate destination in catalog.')
            seen.add(name.casefold())
            item = {'name': name, 'url': https_url(link.get('href')), 'size': None, 'md5': None}
            if link['rel'] == 'nds.file':
                size, checksum = link.get('length'), link.get('hash')
                if type(size) is not int or not 0 <= size < 2**32:
                    raise DownloadError('Missing/invalid size or file exceeds FAT32 limit.')
                if not isinstance(checksum, str) or not re.fullmatch(r'md5:[0-9a-fA-F]{32}', checksum):
                    raise DownloadError('Missing or unsupported checksum.')
                item.update(size=size, md5=checksum[4:].lower())
            elif name != 'PACKAGE.SLIST':
                raise DownloadError('Unsupported license destination.')
            files.append(item)
    if not files or not any(x['name'] == 'PACKAGE.SLIST' for x in files):
        raise DownloadError('Catalog has no license file.')
    files.sort(key=lambda item: item["md5"] is None)  # License is the final file.
    return params, files

def target_path(root, name):
    path = root.joinpath(*PurePosixPath(name).parts)
    node = path
    while node != root:
        if node.is_symlink():
            raise DownloadError('Symlink in destination path.')
        node = node.parent
    if path.exists() and not path.is_file():
        raise DownloadError('Destination conflicts with a directory or special file.')
    return path

def valid(item, path):
    return (item['md5'] is not None and path.is_file()
            and path.stat().st_size == item['size'] and digest(path) == item['md5'])

def transfer(item, path, overwrite=False):
    if path.exists() and valid(item, path):
        return 'verified; skipped'
    if path.exists() and not overwrite:
        raise DownloadError('Existing file differs or has no checksum. Use --overwrite only after checking the destination.')
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + '.honda-part')
    if part.is_symlink() or (part.exists() and not part.is_file()):
        raise DownloadError('Unsafe partial file.')
    # Resume map content only; licenses have no checksum and are fetched fresh.
    for attempt in range(4):
        try:
            offset = part.stat().st_size if part.exists() and item['md5'] else 0
            if item['size'] is not None and offset >= item['size']:
                if offset == item['size'] and digest(part) == item['md5']:
                    os.replace(part, path)
                    return 'verified'
                part.unlink()
                offset = 0
            with request(item['url'], offset) as response:
                status = response.status
                if status == 206:
                    m = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                    if not m or int(m[1]) != offset or (item['size'] is not None and int(m[3]) != item['size']):
                        raise DownloadError('Server returned an inconsistent byte range.')
                    append = offset > 0
                elif status == 200:
                    append = False  # Range unsupported: restart instead of appending.
                    offset = 0
                else:
                    raise DownloadError('Unexpected download response.')
                written = offset
                limit = item['size'] if item['size'] is not None else 16 * BLOCK
                with part.open('ab' if append else 'wb') as f:
                    while True:
                        data = response.read(BLOCK)
                        if not data:
                            break
                        written += len(data)
                        if written > limit:
                            raise DownloadError('Downloaded data exceeds expected size.')
                        f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            if item['md5']:
                if not valid(item, part):
                    if part.stat().st_size == item['size']:
                        part.unlink()
                    raise DownloadError('File size/checksum verification failed.')
            elif part.stat().st_size == 0:
                raise DownloadError('Empty license response.')
            os.replace(part, path)
            return 'verified' if item['md5'] else 'license saved unchanged (no catalog checksum)'
        except HTTPError as e:
            if e.code in (401, 403, 410):
                raise DownloadError('Link expired or access denied. Generate a new link on the Honda portal.') from None
            if e.code == 416 and part.exists():
                part.unlink()
            if attempt == 3:
                raise DownloadError(f'HTTP error {e.code}; partial map file retained.') from None
        except (OSError, URLError, HTTPException, DownloadError) as e:
            if attempt == 3:
                # Do not print network exceptions: they may contain signed URLs.
                if isinstance(e, DownloadError):
                    raise
                raise DownloadError('Network or file error; check connection, free space and permissions. Partial map file retained.') from None
        time.sleep(min(2 ** attempt, 8))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group()
    src.add_argument('--link-file', type=Path, help='Text file containing the portal launch URL.')
    src.add_argument('--vin-file', type=Path, help='Private text file containing VIN; uses Czech/European portal.')
    parser.add_argument('--accept-here-terms', action='store_true', help='Confirm you read and agree to https://legal.here.com/en-gb/terms (required for VIN lookup).')
    src.add_argument('--catalog', type=Path, help='Previously saved signed JSON catalog (keep private).')
    parser.add_argument('--dest', type=Path, help='Root of an already mounted FAT32 USB; never a /dev device.')
    parser.add_argument('--download', action='store_true', help='Download after displaying the plan.')
    parser.add_argument('--overwrite', action='store_true', help='Replace differing files with the same catalog paths.')
    args = parser.parse_args()
    if args.catalog:
        raw = args.catalog.read_bytes()
        if len(raw) > 16 * BLOCK:
            raise DownloadError('Catalog exceeds 16 MiB.')
        catalog = json.loads(raw)
    elif args.vin_file:
        catalog = catalog_from_url(link_from_vin(args.vin_file.read_text(), args.accept_here_terms))
    else:
        link = args.link_file.read_text().strip() if args.link_file else input('Paste the Honda portal launch link (kept out of shell history): ').strip()
        catalog = catalog_from_url(link)
    params, files = plan(catalog)
    size = sum(x['size'] or 0 for x in files)
    print(f"Honda bonneville EU | {len(files)} files | {size / 1e9:.2f} GB + license")
    print('Metadata and small downloads tested; complete USB/car validation is still required.')
    if not args.download:
        print('Preview only. Add --download --dest /path/to/mounted/USB to write files.')
        return
    if not args.dest:
        parser.error('--download requires --dest')
    root = args.dest.expanduser().resolve(strict=True)
    if not root.is_dir() or str(root).startswith(('/dev/', '/proc/', '/sys/')) or root == Path('/'):
        raise DownloadError('Choose a mounted writable USB directory.')
    targets = [(x, target_path(root, x['name'])) for x in files]
    # Validate all existing targets before starting; never silently replace data.
    need = 0
    for item, path in targets:
        if path.exists() and not args.overwrite and not valid(item, path):
            raise DownloadError('Conflicting existing content; use a blank USB or explicitly enable --overwrite.')
        if not valid(item, path):
            need += item['size'] or 16 * BLOCK
    if shutil.disk_usage(root).free < need + 64 * BLOCK:
        raise DownloadError('Not enough free space (including safety margin).')
    print(f'Destination: {root}\nNo partitioning, formatting, deletion or automatic eject will be performed.')
    for n, (item, path) in enumerate(targets, 1):
        print(f"[{n}/{len(files)}] {item['name']}", flush=True)
        print('  ' + transfer(item, path, args.overwrite), flush=True)
    os.sync()
    print('All catalog files downloaded. Safely eject the USB before taking it to the car.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped. Partial map files can be resumed.', file=sys.stderr)
        sys.exit(130)
    except (DownloadError, OSError, ValueError, KeyError, TypeError):
        # Display controlled messages only; never dump signed URLs or catalog data.
        e = sys.exc_info()[1]
        print('Error: ' + (str(e) if isinstance(e, DownloadError) else 'Invalid input, unavailable network or inaccessible files.'), file=sys.stderr)
        sys.exit(1)
