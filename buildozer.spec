name: Build APK Kasir Warung

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
      - name: Checkout Kode Repository
        uses: actions/checkout@v4

      - name: Siapkan Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Instal Dependensi Sistem & Buildozer
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev automake lld
          echo "Cython<3.0" > /tmp/constraints.txt
          python -m pip install --upgrade pip setuptools wheel packaging
          pip install "Cython<3.0" buildozer==1.5.0

      - name: Validasi Struktur & Bersihkan buildozer.spec
        run: |
          test -f main.py || (echo "ERROR: main.py tidak ditemukan di root repository!" && exit 1)
          test -f buildozer.spec || (echo "ERROR: buildozer.spec tidak ditemukan di root repository!" && exit 1)
          sed -i 's/^requirements = .*/requirements = python3,kivy==2.3.0,pyjnius/g' buildozer.spec
          sed -i 's/^android.archs = .*/android.archs = arm64-v8a/g' buildozer.spec

      - name: Build APK Android
        env:
          PIP_CONSTRAINT: /tmp/constraints.txt
        run: |
          yes | buildozer -v android debug

      - name: Upload File APK Hasil Build
        uses: actions/upload-artifact@v4
        with:
          name: kasirwarung-apk
          path: bin/*.apk
