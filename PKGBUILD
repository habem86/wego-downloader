pkgname=honda-map-downloader-linux
pkgver=0.1.0
pkgrel=1
pkgdesc='Experimental native Linux client for Honda bonneville EU NDS map downloads'
arch=('any')
license=('MIT')
depends=('python>=3.10' 'tk')
optdepends=('xdg-utils: register the portal launch protocol')
source=('honda_maps.py' 'honda_maps_gui.py' 'honda-maps' 'honda-maps-gui' 'honda-map-downloader-linux.desktop' 'README.md' 'USAGE.md' 'LICENSE')
sha256sums=('03a92312993b4af02d17fd02dec6fc5517086be46adfe4411f9dbce652357a88' '4a557f74100af9828fdda64ebe69adbf21f56825e2db3f13bbfa5683f6185f69' 'e6bebe54109a33485f59dec6861a2e12796c89a4cee66ca6a37f04abb0a9ed4d' '95ad05198d9c61e29ea405913b5a8617964093318b4004bffd8629b5bc9c565e' '0b4bf0840586cc7e6721482fb7409da8248b22fcbb43c154b9019682251c5492' '0d5fc144b1d25819c10c9b258b10ee5b98692bc78c973958078d4e58d1ca96a8' '5a49273973c00a7bf33833b012405cc904c325922940eda4d4ecc692896c4289' '8e2e777fe1722d941d34c4e695451e512bd0d23ca8992c7c17e672af92f4cc9e')
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
