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

# Library Python yang dibutuhkan (Kivy 2.3.0 + pyjnius untuk Bluetooth)
requirements = python3,kivy==2.3.0,pyjnius

# Orientasi layar (portrait = tegak seperti HP biasa, landscape = mendatar)
orientation = portrait

# Mode layar penuh (0 = tampilkan status bar baterai/jam HP, 1 = fullscreen)
fullscreen = 0

# Izin Android untuk Bluetooth Thermal, Penyimpanan PDF & Internet (WA)
android.permissions = INTERNET, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Target API Android (API 33 / Android 13)
android.api = 33

# Minimum versi Android yang didukung (API 24 = Android 7.0)
android.minapi = 24

# Versi NDK yang kompatibel
android.ndk = 25b

# Arsitektur CPU HP Android modern (64-bit)
android.archs = arm64-v8a

# Izinkan akses folder Download publik untuk simpan PDF
android.allow_backup = True

# Terima lisensi Android SDK otomatis tanpa prompt interaktif
android.accept_sdk_license = True

# Warna background saat loading awal
android.presplash_color = #2c3e50

[buildozer]

# Level log detail
log_level = 2

# Matikan peringatan root
warn_on_root = 0
