pkgname=honda-map-downloader-linux
pkgver=0.2.0
pkgrel=1
pkgdesc='Experimental native Linux client for Honda bonneville EU NDS map downloads'
arch=('any')
license=('MIT')
depends=('python>=3.10' 'tk')
optdepends=('xdg-utils: register the portal launch protocol')
source=('honda_maps.py' 'honda_maps_gui.py' 'honda-maps' 'honda-maps-gui' 'honda-map-downloader-linux.desktop' 'README.md' 'USAGE.md' 'LICENSE' 'interface.png')
sha256sums=('2fb4d71348c41eaf2b50e5a1e9cb4285aa580191a078b03c3b2e2e5cea23ed23' '4a3ecec1236d2547e0edb194869602e6f12ccee200ba7e1ef49cebec4e194c3d' 'e6bebe54109a33485f59dec6861a2e12796c89a4cee66ca6a37f04abb0a9ed4d' '95ad05198d9c61e29ea405913b5a8617964093318b4004bffd8629b5bc9c565e' '0b4bf0840586cc7e6721482fb7409da8248b22fcbb43c154b9019682251c5492' '26b074f2f6fdb0406ccee1c727d762167d956c802cc71e1c222b5e3c2def3d9a' 'c51462a431596bc18afe658b6d44774e12ed37736a6d74a9c6fbe8c16d96b59a' '8e2e777fe1722d941d34c4e695451e512bd0d23ca8992c7c17e672af92f4cc9e' '89b2cd4b6fd5f54a781a7d6942173ae55b8bf2df34d6c8c1179befa49a4a9de9')
package() {
  install -Dm644 honda_maps.py "$pkgdir/usr/lib/$pkgname/honda_maps.py"
  install -Dm644 honda_maps_gui.py "$pkgdir/usr/lib/$pkgname/honda_maps_gui.py"
  install -Dm755 honda-maps "$pkgdir/usr/bin/honda-maps"
  install -Dm755 honda-maps-gui "$pkgdir/usr/bin/honda-maps-gui"
  install -Dm644 honda-map-downloader-linux.desktop "$pkgdir/usr/share/applications/honda-map-downloader-linux.desktop"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
  install -Dm644 USAGE.md "$pkgdir/usr/share/doc/$pkgname/USAGE.md"
  install -Dm644 interface.png "$pkgdir/usr/share/doc/$pkgname/interface.png"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
