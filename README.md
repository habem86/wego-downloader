# Honda Map Downloader for Linux

An experimental, independent client for HERE Honda **bonneville EU** map updates, developed for a model year 2024 Civic. It runs natively in Python and requires neither Wine nor macOS. It is not an official HERE/Honda application or a complete replacement for every feature of the original downloader.

The client retrieves a catalog through the Czech/European VIN portal or a `heremapdownloaderv2://` launch link, downloads files to their catalog-defined paths, checks file sizes and MD5 hashes, and resumes interrupted transfers. It preserves the original `PACKAGE.SLIST` license file unchanged. It does not format USB drives.

## Install on Arch Linux

Download `honda-map-downloader-linux-0.1.0-1-any.pkg.tar.xz` from the [v0.1.0 release](https://github.com/habem86/wego-downloader/releases/tag/v0.1.0).

```bash
sudo pacman -S --needed python tk
sudo pacman -U ./honda-map-downloader-linux-0.1.0-1-any.pkg.tar.xz
honda-maps-gui
```

The package uses architecture `any` because it contains Python rather than architecture-specific machine code. Installation on an actual Arch system and execution on other CPU architectures have not yet been verified.

## Use the application

1. Select **VIN — Czech/European portal**, enter your VIN, read the HERE terms, and confirm your own agreement. Alternatively, select **Portal launch link** and paste a link issued by the official portal.
2. Select **Check catalog** to check update availability.
3. Prepare a blank, mounted **32 GB FAT32 USB drive** according to Honda's instructions. Choose the **root directory of the mounted USB**, not `/dev/sdX` or a subdirectory.
4. Select **Download to USB**. The inspected catalog contained approximately 26.47 GB of map data.
5. After completion, safely eject the USB in Linux and follow Honda's in-vehicle update instructions.

VINs, launch links, catalogs, and license files are private. Do not post them in issues or public logs. They are not included in this repository or its release assets.

The client refuses to replace differing existing files unless you explicitly allow replacement. It does not remove old files outside the current catalog, so use a prepared blank drive. Interrupted map downloads can resume from `.honda-part` files. If a link expires, obtain a new one from the portal.

## Run from source

Requires Python 3.10+ and Tk for the graphical interface. There are no PyPI dependencies.

```bash
git clone https://github.com/habem86/wego-downloader.git
cd wego-downloader
python3 honda_maps_gui.py
```

Preview a catalog in the terminal:

```bash
python3 honda_maps.py
```

Download from the terminal; paste the launch link at the interactive prompt:

```bash
python3 honda_maps.py --download --dest /run/media/YOUR_USER/USB
```

See the [usage guide](USAGE.md) for VIN lookup from the terminal, browser integration, and troubleshooting.

## Validation and limitations

- 14 automated tests cover HTTP 206 resume, servers ignoring Range, inconsistent ranges and MD5 failures, existing files, symbolic links, unsafe paths, FAT filename collisions, unchanged license bytes, and consent before VIN lookup.
- Live checks covered VIN lookup, European catalog retrieval, and sample downloads with matching MD5 hashes. A 1.46 MB file successfully resumed at byte 65,536 using HTTP 206.
- **A complete download, writing to a real FAT32 USB drive, and acceptance by a vehicle have not been tested. The graphical window has not been run in this environment.** This is a prerelease for further validation.
- Only European bonneville NDS catalogs with `nds.file` and `nds.drm` relations are supported. Other catalogs are rejected before writing.
- The client does not bypass authorization or license protections. It uses download links issued by the official portal for an eligible vehicle.

See [VALIDATION.txt](VALIDATION.txt) for the recorded checks and coverage limits.

## Test and build

```bash
python3 -m unittest -v test_honda_maps.py
python3 scripts/build_arch_package.py
```

The build creates an Arch package, a source archive, and `SHA256SUMS` in `dist/`. On Arch, you can alternatively run `makepkg -si`.

The MIT license covers this independent client only. It does not cover original HERE/Honda software, map data, licenses, or trademarks.
