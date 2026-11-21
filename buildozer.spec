[app]

# Judul aplikasi di launcher Android
title = Kasir Warung

# Nama paket unik (huruf kecil, tanpa spasi)
package.name = kasirwarung

# Domain paket
package.domain = org.pondokjati

# Folder tempat main.py berada
source.dir = .

# Ekstensi file yang ikut dikemas ke dalam APK
source.include_exts = py,png,jpg,kv,atlas,json,log

# Versi aplikasi
version = 1.0.0

# Library Python ringan & 100% kompatibel dengan python-for-android
requirements = python3,kivy,pyjnius

# Orientasi layar
orientation = portrait

# Mode layar penuh (0 = tampilkan status bar HP)
fullscreen = 0

# Izin Android untuk Bluetooth Thermal, Penyimpanan PDF & Internet (WA)
android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Target API Android 33 (Android 13)
android.api = 33

# Minimum versi Android 7.0 (API 24)
android.minapi = 24

# Versi NDK stabil
android.ndk = 25b

# Arsitektur CPU 64-bit modern (cepat & standar Play Store/Android 10+)
android.archs = arm64-v8a

# Backup data
android.allow_backup = True

# Terima lisensi Android SDK otomatis
android.accept_sdk_license = True

# Warna background saat loading awal
android.presplash_color = #2c3e50

[buildozer]

# Level log detail
log_level = 2

# Matikan peringatan root
warn_on_root = 0
