Experimental native Linux client for Honda bonneville EU map updates, developed against a model year 2024 Civic workflow.

- Graphical Tk interface and command-line client; Python standard library only.
- Czech/European VIN lookup with explicit HERE terms consent, or an official portal launch link.
- Catalog-defined NDS file paths, size/MD5 verification, resumable transfers, and unchanged original license bytes. No USB formatting.
- Arch Linux `any` package, source archive, and SHA-256 checksums attached.
- English installation and usage guides in the repository.

Install on Arch Linux:

```bash
sudo pacman -S --needed python tk
sudo pacman -U ./honda-map-downloader-linux-0.1.0-1-any.pkg.tar.xz
honda-maps-gui
```

Validation: 14 unit tests passed. Live checks covered VIN-to-catalog lookup, sample file hashes, and an HTTP 206 resume from byte 65,536. A complete map download, real FAT32 USB write, graphical display, actual Arch installation, and acceptance by a vehicle have not been validated. This prerelease is intended for further testing.

No VIN, signed launch links, catalogs, map data, or license payloads are included. This is an independent client, not an official HERE/Honda release.
