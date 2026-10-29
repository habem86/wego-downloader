pkgname=honda-map-downloader-linux
pkgver=0.1.1
pkgrel=1
pkgdesc='Experimental native Linux client for Honda bonneville EU NDS map downloads'
arch=('any')
license=('MIT')
depends=('python>=3.10' 'tk')
optdepends=('xdg-utils: register the portal launch protocol')
source=('honda_maps.py' 'honda_maps_gui.py' 'honda-maps' 'honda-maps-gui' 'honda-map-downloader-linux.desktop' 'README.md' 'USAGE.md' 'LICENSE')
sha256sums=('2fb4d71348c41eaf2b50e5a1e9cb4285aa580191a078b03c3b2e2e5cea23ed23' 'b0b41543b0e81902fae65399c089f43831bb8c1a48146a111492930be3aeec80' 'e6bebe54109a33485f59dec6861a2e12796c89a4cee66ca6a37f04abb0a9ed4d' '95ad05198d9c61e29ea405913b5a8617964093318b4004bffd8629b5bc9c565e' '0b4bf0840586cc7e6721482fb7409da8248b22fcbb43c154b9019682251c5492' '47e6d4082006a862d3f5b6fc04c520bfa7ed4c6ec6db216aa09ae5602887f5ff' 'a62eaf725017163b105c4bc334e0e2387b648c59823461a76c5786c285dbfa41' '8e2e777fe1722d941d34c4e695451e512bd0d23ca8992c7c17e672af92f4cc9e')
package() {
  install -Dm644 honda_maps.py "$pkgdir/usr/lib/$pkgname/honda_maps.py"
  install -Dm644 honda_maps_gui.py "$pkgdir/usr/lib/$pkgname/honda_maps_gui.py"
  install -Dm755 honda-maps "$pkgdir/usr/bin/honda-maps"
  install -Dm755 honda-maps-gui "$pkgdir/usr/bin/honda-maps-gui"
  install -Dm644 honda-map-downloader-linux.desktop "$pkgdir/usr/share/applications/honda-map-downloader-linux.desktop"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 USAGE.md "$pkgdir/usr/share/doc/$pkgname/USAGE.md"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
