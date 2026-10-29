Fix the USB directory layout to match the original downloader for Honda bonneville EU release `1`.

**Do not use v0.1.0's USB-root layout for an in-car update.** It omitted the enclosing release folder. Version 0.1.1 writes catalog entries under `HereMapsV1`, including `PACKAGE.SLIST`, and preserves nested paths such as `NavDB.CZE_1109/U1109`.

- Combine the catalog folder prefix (`parameters.path`, default `HereMapsV`) with each distribution release key (`1` in the inspected catalog).
- Reject unsafe prefixes, accidental selection of `HereMapsV1` as the USB root, and legacy root-level map data before downloading. No automatic moves or deletions.
- Update the graphical destination hint and English installation/migration guides.
- Add seven layout regression tests; 21 tests pass locally.

Install on Arch Linux:

```bash
sudo pacman -S --needed python tk
sudo pacman -U ./honda-map-downloader-linux-0.1.1-1-any.pkg.tar.xz
honda-maps-gui
```

Choose the mounted USB root. `HereMapsV1` is created automatically. To reuse a v0.1.0 download, follow the migration notes in USAGE.md, or use a separate prepared blank drive.

The vehicle-created MapDownload_PortalSite.url and unrelated USB-root items such as LOST.DIR are left untouched.

This remains an experimental prerelease. Full-map transfer, a real FAT32 USB write, graphical display, Arch installation, and vehicle acceptance are not yet validated. No VIN, signed links, catalogs, map data, or license payloads are included.
