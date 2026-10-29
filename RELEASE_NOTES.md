A redesigned, minimal native interface for the Honda bonneville EU downloader.

- Warm paper and charcoal, restrained color accents, system sans/monospace typography, square controls, and three numbered sections: SOURCE, DESTINATION, TRANSFER.
- Separate VIN and launch-link inputs. Signed links are masked by default and are not exposed when switching to VIN mode.
- Mounted-drive free-space feedback, a clear HereMapsV1 destination hint, and a primary Download to USB action.
- Real completed-file progress and clear catalog-ready, loading, error, stopped, and completed states. No invented byte percentages or ETA.
- Activity switches to a scrollable log within the same panel. Errors remain visible without opening it. Inputs are locked during a transfer; Stop remains available.
- Existing map paths, MD5 checks, resumable transfers, unchanged license handling, and USB-root protections are preserved. No new runtime dependencies: Python and Tk only.

Install or upgrade on Arch Linux:

```bash
sudo pacman -S --needed python tk
sudo pacman -U ./honda-map-downloader-linux-0.2.0-1-any.pkg.tar.xz
honda-maps-gui
```

See the repository README for a real screenshot and USAGE.md for the English guide.

Validation: 21 downloader tests and 11 GUI behavior tests passed locally. The interface was rendered and visually checked with Tk 8.6 and Tk 9 on virtual X displays. A complete map transfer, real FAT32 USB write, installation on an actual Arch desktop, and vehicle acceptance remain unvalidated. This remains an experimental prerelease.

No VIN, signed launch links, catalogs, map data, or license payloads are included. The vehicle-created .url file and unrelated USB-root items remain untouched.
