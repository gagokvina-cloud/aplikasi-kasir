[app]
title = Kasir Warung
package.name = kasirwarung
package.domain = org.kasirwarung
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0.0

# Pastikan python3 ada, dan TIDAK ADA fpdf2
requirements = python3, kivy==2.3.2, pyjnius, pillow

android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk = 25b
android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.requestLegacyExternalStorage = True
orientation = portrait
