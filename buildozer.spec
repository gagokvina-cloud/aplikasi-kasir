[app]

title = Kasir Warung
package.name = kasirwarung
package.domain = org.pondokjati
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,log
version = 1.0.0

requirements = python3,kivy==2.3.0,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True
android.presplash_color = #2c3e50

[buildozer]
log_level = 2
warn_on_root = 0
