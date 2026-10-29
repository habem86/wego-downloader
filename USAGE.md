# Usage guide

## Requirements

- Python 3.10 or newer.
- Tk for the graphical interface (`sudo pacman -S --needed python tk` on Arch).
- An eligible Honda vehicle using the European bonneville NDS update program. Development checks used a model year 2024 Civic; other vehicles have not been validated.
- A blank, mounted 32 GB USB drive prepared as FAT32, following Honda's instructions.

The client uses only the Python standard library. It does not partition or format drives, remove old map data, or automatically eject media.

## Graphical interface

Run `honda-maps-gui` after installing the Arch package, or `python3 honda_maps_gui.py` from the source directory.

### Retrieve a catalog using a VIN

1. Select **VIN — Czech/European portal**.
2. Enter the 17-character VIN. This lookup uses the official Honda/HERE portal with Czech Republic selected and English as the page language.
3. Read the linked HERE Terms of Use. If you agree, check the consent box. The client will not submit a VIN without this confirmation.
4. Select **Check catalog**. The client obtains a launch link from the portal and retrieves its signed catalog.

If the portal cannot find the vehicle, check the VIN and the vehicle's Online Services status. The portal states that Online Services must be signed in for lookup. Other eligibility, login, or portal errors may need to be resolved in a browser.

### Use a portal launch link

1. Open the [official Honda portal](https://www.navigation.com/web/WFS/Shop-HondaEMEA-Site/en_GB/-/EUR/ViewHASDKHomepage-Start).
2. Select the correct country and vehicle, enter the requested details, and complete the normal portal flow.
3. Copy the address of the **Download** button beginning with `heremapdownloaderv2://`.
4. In the client, select **Portal launch link**, paste the address, and select **Check catalog**.

A signed launch link grants access to vehicle-specific update data. Keep it private. Do not post it in a GitHub issue.

### Download to USB

1. Prepare and mount a blank FAT32 USB drive according to Honda's instructions.
2. Select **Choose folder…** and choose the **root of the mounted USB drive**. Do not choose a `/dev` device or create an extra enclosing folder.
3. Select **Download to USB** and confirm the destination.
4. The client creates `HereMapsV1` for release `1`; map files and `PACKAGE.SLIST` go inside it. Do not select an existing `HereMapsV1` directory as the destination.
5. Wait until the client reports that all catalog files have downloaded. Map files are checked against catalog sizes and MD5 hashes. The original `PACKAGE.SLIST` license is saved last, unchanged; the catalog does not provide a checksum for that entry.
6. Safely eject the drive using Linux and follow Honda's update instructions in the vehicle.

The inspected catalog contained 26,468,657,197 bytes of map data plus the license. A future catalog may differ. The client checks free space with a margin before starting.

## Upgrading from v0.1.0

Version 0.1.0 incorrectly wrote `NavDB.*`, `VRContext.Data`, and `PACKAGE.SLIST` directly into the USB root. Do not use that layout for an in-car update. Version 0.1.1 uses the release folder, matching the observed original layout: `HereMapsV1/NavDB.*`, `HereMapsV1/VRContext.Data`, and `HereMapsV1/PACKAGE.SLIST` for release `1`.

Use a prepared blank USB, or carefully relocate only the earlier client's catalog files and matching `.honda-part` files into `HereMapsV1` before resuming. Leave unrelated root files and folders in place. The client will not move or delete them automatically. If unsure which files belong to the old download, use a separate blank drive.

Already-correct map files inside the release folder are checked by size and MD5 and can be reused. An existing license has no catalog checksum and requires explicit overwrite permission to be refreshed. Do not select `HereMapsV1` as the destination: choose its parent USB root.

The default folder prefix is `HereMapsV`; a catalog's `parameters.path` can override it, and the distribution release key is appended. Unsafe prefixes and release identifiers are rejected before writing.

The vehicle-created `MapDownload_PortalSite.url` is not part of this fix. Leave it and unrelated items such as `LOST.DIR` in the USB root; the client does not modify them.

## Stop and resume

Use **Stop** in the window or press Ctrl+C in the terminal. Completed map files with matching size and MD5 are skipped on the next run. Partial map data is kept in `.honda-part` files beside its destination.

When resuming, the client verifies the server's byte range. If the server ignores Range and returns the full file, that file is restarted rather than incorrectly appended. A complete file with an incorrect MD5 is discarded and retried.

If a signed link expires, obtain a fresh link or perform a fresh VIN lookup, then select the same destination. Existing files with matching hashes can still be reused.

Existing differing files, including a pre-existing license without a catalog checksum, are refused by default. Only enable **Allow replacing files with the same catalog paths** after checking the destination. Files outside the catalog are not removed.

## Terminal interface

Preview a catalog, entering the launch link at the prompt:

```bash
honda-maps
```

Download to the mounted USB:

```bash
honda-maps --download --dest /run/media/YOUR_USER/USB
```

Use a private text file containing the launch link:

```bash
honda-maps --link-file /path/to/private-launch-link.txt
```

Use a private text file containing the VIN:

```bash
honda-maps --vin-file /path/to/private-vin.txt --accept-here-terms
```

The `--accept-here-terms` switch confirms that you have read and agree to [HERE's terms](https://legal.here.com/en-gb/terms). Add `--download --dest /path/to/mounted/USB` to start downloading.

Other options:

- `--catalog /path/to/private-catalog.json`: use a previously saved signed catalog.
- `--overwrite`: explicitly allow replacing differing files at catalog paths.
- `--help`: display the available options.

When running from source, replace `honda-maps` with `python3 honda_maps.py`.

## Browser integration on Linux

After installing the Arch package, optionally register this application as the handler for portal launch links:

```bash
xdg-mime default honda-map-downloader-linux.desktop x-scheme-handler/heremapdownloaderv2
```

This changes the default handler for that URI scheme for your user. The browser may ask for confirmation before opening the external application.

## Verify a release download

Place the downloaded release archives and `SHA256SUMS` in the same directory, then run:

```bash
sha256sum -c SHA256SUMS
```

The checksum file lists both the package and source archive; download both to verify the entire list. The repository also includes a PKGBUILD for building the package locally with `makepkg -si` on Arch.

## Known limits

This prerelease supports only Honda bonneville EU catalogs using `nds.file` and `nds.drm`. It does not implement other catalog formats or all features of the official application.

Sample downloads, resume behavior, and catalog lookup have been tested. The full update, a real FAT32 USB write, the graphical window, package installation on Arch, and acceptance by a vehicle have not been validated in this environment. See [VALIDATION.txt](VALIDATION.txt).

Only links issued by the official portal are used. License bytes are not interpreted, altered, or bypassed. The application and its documentation are independent of HERE and Honda.
