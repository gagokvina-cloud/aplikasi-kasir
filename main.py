# main.py - Aplikasi Kasir Warung Android (Kivy)
# Bersih & 100% Pure Python (Hanya butuh: python3,kivy,pyjnius)

import os
import json
import copy
import socket
import urllib.parse
import webbrowser
import datetime
from collections import defaultdict

from kivy.app import App
from kivy.utils import platform, get_color_from_hex
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup

# Native Android Bluetooth API
ANDROID_BT_AVAILABLE = False
if platform == "android":
    try:
        from jnius import autoclass
        from android.permissions import request_permissions, Permission
        BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
        UUID = autoclass("java.util.UUID")
        ANDROID_BT_AVAILABLE = True
    except Exception:
        ANDROID_BT_AVAILABLE = False

# Warna Tema
C_PRIMARY = get_color_from_hex("#2c3e50")
C_AKSEN = get_color_from_hex("#3498db")
C_SUKSES = get_color_from_hex("#27ae60")
C_BATAL = get_color_from_hex("#e74c3c")
C_WARNING = get_color_from_hex("#f39c12")
C_ORANGE = get_color_from_hex("#e67e22")
C_WA = get_color_from_hex("#128C7E")
C_WHITE = (1, 1, 1, 1)

FILE_DATABASE = "database_warung.json"
FILE_AUDIT = "audit_role.log"
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

DATA_AWAL = {
    "users": {
        "owner": {"password": "owner", "role": "owner", "nama": "Owner Warung"},
        "coba": {"password": "1234", "role": "kasir", "nama": "Kasir Coba"}
    },
    "menu": {
        "1": {"nama": "Nasi Liwet Solo", "harga": 20000, "hpp": 8000, "stok": 30, "kategori": "Makanan"},
        "2": {"nama": "Pempek Palembang", "harga": 25000, "hpp": 10000, "stok": 25, "kategori": "Makanan"},
        "3": {"nama": "Nasi Pecel", "harga": 15000, "hpp": 6000, "stok": 30, "kategori": "Makanan"},
        "4": {"nama": "Es Teh Manis", "harga": 5000, "hpp": 1500, "stok": 50, "kategori": "Minuman"},
        "5": {"nama": "Es Jeruk", "harga": 7000, "hpp": 2000, "stok": 40, "kategori": "Minuman"}
    },
    "customers": {},
    "kategori_menu": ["Makanan", "Minuman", "Snack", "Cemilan"],
    "posisi_duduk": [
        "Take-Away", "Deretan Depan", "Tengah Depan Bar",
        "Depan Band", "Seberang Tenan", "Belakang", "Lesehan"
    ],
    "riwayat_transaksi": [],
    "riwayat_kasir": [],
    "pesanan_belum_bayar": [],
    "profil_toko": {
        "nama": "NASI LIWET PONDOK JATI",
        "alamat": "Jl. Raya Pondok Jati No. 123",
        "kota": "Sidoarjo",
        "telepon": "0812-3456-7890",
        "footer": "Terima Kasih Atas Kunjungan Anda"
    },
    "biaya_operasional": {
        "sewa": 0, "listrik": 0, "air": 0, "gas": 0,
        "karyawan": 0, "transportasi": 0, "lainnya": 0
    },
    "diskon_karyawan_default": 10,
    "pengaturan_printer": {
        "bluetooth_name": "",
        "bluetooth_mac": "",
        "bluetooth_channel": 1,
        "lebar_struk": 32,
        "cutting_paper": True,
        "cashdrawer": False
    }
}


def simpan_teks_ke_pdf_murni(teks_laporan, path_output):
    """Generator PDF 1.4 standar murni Python tanpa library eksternal (bebas error C-compile)"""
    lines = teks_laporan.splitlines()
    per_halaman = 48
    halaman_list = [lines[i:i + per_halaman] for i in range(0, max(1, len(lines)), per_halaman)]

    objects = []
    # Obj 1: Catalog, Obj 2: Pages, Obj 3: Font Courier
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    page_obj_nums = []
    next_obj = 4
    page_entries = []

    for hal in halaman_list:
        page_num = next_obj
        content_num = next_obj + 1
        next_obj += 2
        page_obj_nums.append(page_num)

        stream_cmds = ["BT", "/F1 10 Tf", "40 790 Td", "14 TL"]
        for idx, baris in enumerate(hal):
            aman = baris.encode("latin-1", errors="replace").decode("latin-1")
            aman = aman.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if idx == 0:
                stream_cmds.append(f"({aman}) Tj")
            else:
                stream_cmds.append(f"T* ({aman}) Tj")
        stream_cmds.append("ET")
        stream_data = "\n".join(stream_cmds)

        page_entries.append((
            page_num,
            f"{page_num} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>\nendobj\n",
            content_num,
            f"{content_num} 0 obj\n<< /Length {len(stream_data)} >>\nstream\n{stream_data}\nendstream\nendobj\n"
        ))

    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_nums)} >>\nendobj\n")
    objects.append("3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    for _, p_str, _, c_str in page_entries:
        objects.append(p_str)
        objects.append(c_str)

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_str in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj_str.encode("latin-1"))

    xref_pos = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf_bytes.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    pdf_bytes.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    with open(path_output, "wb") as f:
        f.write(pdf_bytes)


def normalisasi_no_wa(nomor):
    digits = "".join(ch for ch in str(nomor) if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("0"):
        return "62" + digits[1:]
    if digits.startswith("8"):
        return "62" + digits
    return digits


def kirim_struk_whatsapp(no_wa, teks_struk):
    wa_num = normalisasi_no_wa(no_wa)
    if not wa_num:
        tampilkan_pesan("No. WA Kosong", "Masukkan No. WhatsApp customer terlebih dahulu!")
        return
    encoded = urllib.parse.quote(teks_struk)
    url = f"https://wa.me/{wa_num}?text={encoded}"
    try:
        webbrowser.open(url)
    except Exception as e:
        tampilkan_pesan("Gagal Membuka WA", f"Pastikan WhatsApp terinstal di HP Anda:\n{e}")


def catat_audit(role, username, aksi, detail=""):
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baris = f"[{waktu}] [{role}/{username}] {aksi}: {detail}\n" if detail else f"[{waktu}] [{role}/{username}] {aksi}\n"
    try:
        with open(FILE_AUDIT, "a", encoding="utf-8") as f:
            f.write(baris)
    except Exception:
        pass


def tampilkan_pesan(judul, pesan):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    scroll = ScrollView(size_hint=(1, 1))
    lbl = Label(
        text=pesan,
        size_hint_y=None,
        halign="left",
        valign="top",
        color=C_WHITE,
        font_size=dp(14)
    )
    lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
    scroll.add_widget(lbl)
    box.add_widget(scroll)

    btn = Button(text="OK", size_hint_y=None, height=dp(42), background_color=C_AKSEN, bold=True)
    popup = Popup(title=judul, content=box, size_hint=(0.88, 0.55))
    btn.bind(on_release=popup.dismiss)
    box.add_widget(btn)
    popup.open()


class BluetoothPrinterManager:
    def __init__(self):
        self.bt_socket = None
        self.out_stream = None
        self.connected_mac = None

    def minta_izin(self):
        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                request_permissions([
                    Permission.BLUETOOTH,
                    Permission.BLUETOOTH_ADMIN,
                    "android.permission.BLUETOOTH_CONNECT",
                    "android.permission.BLUETOOTH_SCAN",
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE
                ])
            except Exception:
                pass

    def scan_paired_devices(self):
        devices = []
        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                if adapter is None or not adapter.isEnabled():
                    return []
                paired = adapter.getBondedDevices().toArray()
                for dev in paired:
                    nama = dev.getName() or "Printer BT"
                    mac = dev.getAddress()
                    devices.append((nama, mac))
            except Exception:
                pass
        return devices

    def is_connected(self):
        if self.bt_socket is not None:
            try:
                if hasattr(self.bt_socket, "isConnected"):
                    return self.bt_socket.isConnected()
                return True
            except Exception:
                return False
        return False

    def disconnect(self):
        try:
            if self.out_stream:
                self.out_stream.close()
            if self.bt_socket:
                self.bt_socket.close()
        except Exception:
            pass
        self.out_stream = None
        self.bt_socket = None
        self.connected_mac = None

    def connect(self, mac, channel=1):
        if not mac:
            return False, "MAC Address printer belum dipilih."
        if self.is_connected() and self.connected_mac == mac:
            return True, "Sudah terhubung"
        self.disconnect()

        if platform == "android" and ANDROID_BT_AVAILABLE:
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                if adapter is None:
                    return False, "Perangkat tidak mendukung Bluetooth."
                if not adapter.isEnabled():
                    return False, "Bluetooth HP mati! Nyalakan Bluetooth terlebih dahulu."

                adapter.cancelDiscovery()
                device = adapter.getRemoteDevice(mac)
                uuid_obj = UUID.fromString(SPP_UUID)
                try:
                    sock = device.createRfcommSocketToServiceRecord(uuid_obj)
                    sock.connect()
                except Exception:
                    create_method = device.getClass().getMethod("createRfcommSocket", autoclass("java.lang.Integer").TYPE)
                    sock = create_method.invoke(device, int(channel))
                    sock.connect()

                self.bt_socket = sock
                self.out_stream = sock.getOutputStream()
                self.connected_mac = mac
                return True, f"Terhubung ke {device.getName() or mac}"
            except Exception as e:
                self.disconnect()
                return False, f"Gagal koneksi Bluetooth Android: {e}"

        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.settimeout(8)
            sock.connect((mac, int(channel)))
            self.bt_socket = sock
            self.connected_mac = mac
            return True, f"Terhubung ke {mac}"
        except Exception as e:
            self.disconnect()
            return False, f"Gagal koneksi socket: {e}"

    def kirim_data(self, teks, mac, channel=1, cutting=True, cashdrawer=False):
        ok, msg = self.connect(mac, channel)
        if not ok:
            return False, msg

        try:
            payload = bytearray()
            payload.extend(b"\x1B\x40")
            for line in teks.split("\n"):
                payload.extend((line + "\n").encode("utf-8", errors="replace"))
            if cutting:
                payload.extend(b"\n\n\x1D\x56\x00")
            if cashdrawer:
                payload.extend(b"\x1B\x70\x00\x19\xFA")

            if platform == "android" and self.out_stream is not None:
                self.out_stream.write(bytes(payload))
                self.out_stream.flush()
            else:
                self.bt_socket.send(bytes(payload))
            return True, "Berhasil dicetak!"
        except Exception as e:
            self.disconnect()
            return False, f"Koneksi terputus: {e}"


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))

        header = BoxLayout(orientation="vertical", size_hint_y=0.25)
        self.lbl_nama_warung = Label(text="NASI LIWET PONDOK JATI", font_size=dp(22), bold=True, color=C_WHITE)
        header.add_widget(self.lbl_nama_warung)
        header.add_widget(Label(text="Sistem Kasir Android (Multi-Role)", font_size=dp(14), color=(0.8, 0.8, 0.8, 1)))
        root.add_widget(header)

        form = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=0.6)
        self.inp_user = TextInput(hint_text="Username (cth: owner / coba)", multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))
        self.inp_pass = TextInput(hint_text="Password", password=True, multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))
        self.inp_modal = TextInput(hint_text="Modal Awal Kas (Rp)", text="500000", input_filter="int", multiline=False, font_size=dp(16), size_hint_y=None, height=dp(46))

        form.add_widget(Label(text="Username:", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_user)
        form.add_widget(Label(text="Password:", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_pass)
        form.add_widget(Label(text="Modal Awal (Shift Baru):", size_hint_y=None, height=dp(22), halign="left"))
        form.add_widget(self.inp_modal)

        btn_login = Button(text="LOGIN MASUK", size_hint_y=None, height=dp(50), background_color=C_SUKSES, bold=True, font_size=dp(16))
        btn_login.bind(on_release=self.proses_login)
        form.add_widget(btn_login)

        btn_ganti_pw = Button(text="Ganti Password", size_hint_y=None, height=dp(40), background_color=C_WARNING, font_size=dp(14))
        btn_ganti_pw.bind(on_release=self.dialog_ganti_password)
        form.add_widget(btn_ganti_pw)

        root.add_widget(form)
        root.add_widget(Label(text="Default -> owner/owner | coba/1234", font_size=dp(12), size_hint_y=0.1, color=(0.7, 0.7, 0.7, 1)))
        self.add_widget(root)

    def on_pre_enter(self):
        app = App.get_running_app()
        if app and hasattr(app, "db"):
            self.lbl_nama_warung.text = app.db["profil_toko"].get("nama", "WARUNG")

    def proses_login(self, *args):
        app = App.get_running_app()
        uname = self.inp_user.text.strip()
        pwd = self.inp_pass.text.strip()

        if not uname or not pwd:
            tampilkan_pesan("Peringatan", "Username dan Password wajib diisi!")
            return

        users = app.db.get("users", {})
        if uname not in users:
            catat_audit("unknown", uname, "LOGIN_FAIL", f"user tidak ditemukan: {uname}")
            tampilkan_pesan("Login Gagal", "Username tidak terdaftar!")
            return

        user_data = users[uname]
        role = user_data.get("role", "kasir")

        if user_data.get("password") != pwd:
            catat_audit(role, uname, "LOGIN_FAIL", f"password salah: {uname}")
            tampilkan_pesan("Login Gagal", "Password salah!")
            return

        try:
            modal = int(self.inp_modal.text.strip() or 0)
        except ValueError:
            modal = 0

        app.user_aktif = uname
        app.role_aktif = role
        app.modal_awal = modal
        app.saldo_kas += modal

        app.db["riwayat_kasir"].append({
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "nama": uname,
            "role": role,
            "modal_awal": modal,
            "saldo_kas": app.saldo_kas,
            "status": "Mulai Shift"
        })
        app.simpan_database()
        catat_audit(role, uname, "LOGIN_OK", f"role={role}")

        mac = app.db["pengaturan_printer"].get("bluetooth_mac", "")
        if mac:
            app.bt_manager.connect(mac, app.db["pengaturan_printer"].get("bluetooth_channel", 1))

        self.inp_pass.text = ""
        app.root.current = "main"
        app.main_screen.on_enter_session()

    def dialog_ganti_password(self, *args):
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        u_in = TextInput(hint_text="Username", multiline=False, size_hint_y=None, height=dp(42))
        old_in = TextInput(hint_text="Password Lama", password=True, multiline=False, size_hint_y=None, height=dp(42))
        new_in = TextInput(hint_text="Password Baru", password=True, multiline=False, size_hint_y=None, height=dp(42))
        box.add_widget(u_in)
        box.add_widget(old_in)
        box.add_widget(new_in)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_ok = Button(text="Simpan", background_color=C_SUKSES, bold=True)
        btn_batal = Button(text="Batal", background_color=C_BATAL)
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_batal)
        box.add_widget(btn_row)

        popup = Popup(title="Ganti Password", content=box, size_hint=(0.88, 0.52))
        btn_batal.bind(on_release=popup.dismiss)

        def simpan(*_):
            u = u_in.text.strip()
            old_p = old_in.text.strip()
            new_p = new_in.text.strip()
            users = app.db.get("users", {})
            if u not in users or users[u]["password"] != old_p:
                tampilkan_pesan("Error", "Username atau password lama salah!")
                return
            if not new_p:
                tampilkan_pesan("Error", "Password baru tidak boleh kosong!")
                return
            users[u]["password"] = new_p
            app.simpan_database()
            catat_audit(users[u]["role"], u, "PASSWORD_CHANGE", f"user={u}")
            popup.dismiss()
            tampilkan_pesan("Sukses", f"Password untuk '{u}' berhasil diperbarui!")

        btn_ok.bind(on_release=simpan)
        popup.open()


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keranjang = []
        self.meja_val = 0
        self.kategori_aktif = "Semua"
        self.idx_pesanan_ditemukan = -1
        self.paired_map = {}

        self.layout_utama = BoxLayout(orientation="vertical")

        # Banner Nama Warung Real-Time
        self.lbl_banner_warung = Label(
            text="NASI LIWET PONDOK JATI",
            size_hint_y=None,
            height=dp(34),
            bold=True,
            font_size=dp(17),
            color=(1, 0.9, 0.3, 1)
        )
        self.layout_utama.add_widget(self.lbl_banner_warung)

        # Top Bar Info Kasir & Status Bluetooth
        self.topbar = BoxLayout(size_hint_y=None, height=dp(42), padding=[dp(8), dp(2)], spacing=dp(6))
        self.lbl_status = Label(text="Kasir: -", bold=True, font_size=dp(12), halign="left")
        self.lbl_bt_badge = Label(text="BT: Offline", bold=True, font_size=dp(11), color=(1, 0.4, 0.4, 1))
        btn_logout = Button(text="Logout", size_hint_x=None, width=dp(68), background_color=C_BATAL, font_size=dp(12), bold=True)
        btn_logout.bind(on_release=self.logout_user)
        self.topbar.add_widget(self.lbl_status)
        self.topbar.add_widget(self.lbl_bt_badge)
        self.topbar.add_widget(btn_logout)
        self.layout_utama.add_widget(self.topbar)

        # Navigasi Menu Horizontal
        nav_scroll = ScrollView(size_hint_y=None, height=dp(44), do_scroll_y=False)
        self.nav_bar = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(4), padding=[dp(4), dp(2)])
        self.nav_bar.bind(minimum_width=self.nav_bar.setter("width"))
        nav_scroll.add_widget(self.nav_bar)
        self.layout_utama.add_widget(nav_scroll)

        # Area Konten Dinamis
        self.area_konten = BoxLayout(orientation="vertical", padding=dp(6))
        self.layout_utama.add_widget(self.area_konten)

        self.add_widget(self.layout_utama)

    def refresh_nama_warung_display(self):
        app = App.get_running_app()
        nama_baru = app.db["profil_toko"].get("nama", "WARUNG")
        self.lbl_banner_warung.text = nama_baru.upper()
        app.login_screen.lbl_nama_warung.text = nama_baru.upper()
        app.title = nama_baru

    def update_bt_badge(self):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        if app.bt_manager.is_connected():
            nama = cfg.get("bluetooth_name") or cfg.get("bluetooth_mac")
            self.lbl_bt_badge.text = f"BT: {nama[:12]}"
            self.lbl_bt_badge.color = (0.3, 1, 0.4, 1)
        elif cfg.get("bluetooth_mac"):
            self.lbl_bt_badge.text = "BT: Siap (Auto)"
            self.lbl_bt_badge.color = (1, 0.85, 0.2, 1)
        else:
            self.lbl_bt_badge.text = "BT: Belum Set"
            self.lbl_bt_badge.color = (1, 0.4, 0.4, 1)

    def on_enter_session(self):
        app = App.get_running_app()
        self.refresh_nama_warung_display()
        self.lbl_status.text = f"{app.user_aktif} ({app.role_aktif.upper()}) | Rp {app.saldo_kas:,}"
        self.update_bt_badge()
        self.bangun_navigasi()
        self.tampilkan_kasir()

    def bangun_navigasi(self):
        app = App.get_running_app()
        self.nav_bar.clear_widgets()

        menus = [
            ("Kasir", self.tampilkan_kasir),
            ("Pelanggan", self.tampilkan_pelanggan),
            ("Printer BT", self.tampilkan_printer)
        ]
        if app.role_aktif == "owner":
            menus.extend([
                ("Profil Warung", self.tampilkan_profil_warung),
                ("Edit Menu", self.tampilkan_edit_menu),
                ("Biaya Ops", self.tampilkan_promosi_ops),
                ("Laporan", self.tampilkan_laporan),
                ("User & Role", self.tampilkan_manajemen_user)
            ])

        for label, callback in menus:
            btn = Button(text=label, size_hint_x=None, width=dp(110), background_color=C_AKSEN, font_size=dp(13), bold=True)
            btn.bind(on_release=lambda inst, cb=callback: cb())
            self.nav_bar.add_widget(btn)

    def logout_user(self, *args):
        app = App.get_running_app()
        app.bt_manager.disconnect()
        catat_audit(app.role_aktif, app.user_aktif, "LOGOUT", f"saldo_akhir={app.saldo_kas}")
        app.db["riwayat_kasir"].append({
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "nama": app.user_aktif,
            "role": app.role_aktif,
            "saldo_akhir": app.saldo_kas,
            "status": "Logout"
        })
        app.user_aktif = None
        app.role_aktif = None
        app.simpan_database()
        app.root.current = "login"

    # ===================== 1. HALAMAN KASIR =====================
    def tampilkan_kasir(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        main_scroll = ScrollView()
        container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7), padding=dp(4))
        container.bind(minimum_height=container.setter("height"))

        # Data Customer (Nama & No WA) + Pilih dari DB
        row_cust = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        self.inp_cust_nama = TextInput(hint_text="Nama Customer (opsional)", multiline=False, font_size=dp(13))
        self.inp_cust_wa = TextInput(hint_text="No. WA (08xx)", input_filter="int", multiline=False, font_size=dp(13))
        btn_pilih_cust = Button(text="DB WA", size_hint_x=None, width=dp(62), background_color=C_WA, bold=True, font_size=dp(12))
        btn_pilih_cust.bind(on_release=self.dialog_pilih_customer)
        row_cust.add_widget(self.inp_cust_nama)
        row_cust.add_widget(self.inp_cust_wa)
        row_cust.add_widget(btn_pilih_cust)
        container.add_widget(row_cust)

        # Pesanan Belum Bayar
        row_psn = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        self.inp_cari_psn = TextInput(hint_text="Cari nama pesanan pending...", multiline=False, font_size=dp(13))
        btn_cari_psn = Button(text="Muat", size_hint_x=None, width=dp(58), background_color=C_AKSEN, font_size=dp(12))
        btn_cari_psn.bind(on_release=self.muat_pesanan_pending)
        btn_list_psn = Button(text=f"Pending ({len(app.db['pesanan_belum_bayar'])})", size_hint_x=None, width=dp(92), background_color=C_ORANGE, font_size=dp(12))
        btn_list_psn.bind(on_release=self.lihat_semua_pending)
        row_psn.add_widget(self.inp_cari_psn)
        row_psn.add_widget(btn_cari_psn)
        row_psn.add_widget(btn_list_psn)
        container.add_widget(row_psn)

        # Meja & Posisi
        row_meja = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        btn_min_meja = Button(text="-", size_hint_x=None, width=dp(36), background_color=C_WARNING, bold=True)
        self.lbl_meja = Label(text=f"Meja: {self.meja_val}", size_hint_x=None, width=dp(72), bold=True)
        btn_plus_meja = Button(text="+", size_hint_x=None, width=dp(36), background_color=C_SUKSES, bold=True)
        btn_min_meja.bind(on_release=lambda *_: self.ubah_meja(-1))
        btn_plus_meja.bind(on_release=lambda *_: self.ubah_meja(1))

        self.spn_posisi = Spinner(text=app.db["posisi_duduk"][0], values=app.db["posisi_duduk"], font_size=dp(13))
        row_meja.add_widget(btn_min_meja)
        row_meja.add_widget(self.lbl_meja)
        row_meja.add_widget(btn_plus_meja)
        row_meja.add_widget(self.spn_posisi)
        container.add_widget(row_meja)

        # Filter Kategori
        row_kat = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        row_kat.add_widget(Label(text="Kategori:", size_hint_x=None, width=dp(70), font_size=dp(13)))
        self.spn_kat = Spinner(text=self.kategori_aktif, values=["Semua"] + app.db["kategori_menu"], font_size=dp(13))
        self.spn_kat.bind(text=self.ganti_kategori)
        row_kat.add_widget(self.spn_kat)
        container.add_widget(row_kat)

        # Grid Menu
        self.grid_menu = GridLayout(cols=2, spacing=dp(6), size_hint_y=None)
        self.grid_menu.bind(minimum_height=self.grid_menu.setter("height"))
        container.add_widget(self.grid_menu)
        self.render_tombol_menu()

        # Keranjang
        container.add_widget(Label(text="KERANJANG BELANJA", bold=True, size_hint_y=None, height=dp(26), font_size=dp(14)))
        self.box_keranjang = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.box_keranjang.bind(minimum_height=self.box_keranjang.setter("height"))
        container.add_widget(self.box_keranjang)

        # Diskon
        row_disk = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.inp_diskon = TextInput(hint_text="Diskon Manual (Rp)", text="0", input_filter="int", multiline=False, font_size=dp(13))
        self.inp_diskon.bind(text=lambda *_: self.hitung_total())
        self.chk_karyawan = CheckBox(size_hint_x=None, width=dp(36))
        self.chk_karyawan.bind(active=lambda *_: self.hitung_total())
        row_disk.add_widget(self.inp_diskon)
        row_disk.add_widget(self.chk_karyawan)
        row_disk.add_widget(Label(text=f"Karyawan ({app.db['diskon_karyawan_default']}%)", size_hint_x=None, width=dp(120), font_size=dp(12)))
        container.add_widget(row_disk)

        # Total & Metode Bayar (Tunai vs QRIS)
        self.lbl_total = Label(text="TOTAL: Rp 0", font_size=dp(19), bold=True, color=(0.2, 0.9, 0.4, 1), size_hint_y=None, height=dp(34))
        container.add_widget(self.lbl_total)

        row_bayar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.spn_metode = Spinner(text="Tunai", values=["Tunai", "QRIS"], size_hint_x=0.38, font_size=dp(14), bold=True)
        self.inp_tunai = TextInput(hint_text="Uang Tunai (Rp)", input_filter="int", multiline=False, font_size=dp(14))
        self.spn_metode.bind(text=self.saat_metode_berubah)
        row_bayar.add_widget(self.spn_metode)
        row_bayar.add_widget(self.inp_tunai)
        container.add_widget(row_bayar)

        # Tombol Aksi
        row_aksi = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        btn_bayar = Button(text="BAYAR & CETAK", background_color=C_SUKSES, bold=True, font_size=dp(12))
        btn_bayar.bind(on_release=self.proses_bayar)
        btn_prev = Button(text="PREVIEW", size_hint_x=None, width=dp(72), background_color=C_AKSEN, bold=True, font_size=dp(12))
        btn_prev.bind(on_release=self.preview_keranjang_sekarang)
        btn_simpan_psn = Button(text="PENDING", size_hint_x=None, width=dp(72), background_color=C_ORANGE, bold=True, font_size=dp(12))
        btn_simpan_psn.bind(on_release=self.simpan_pending)
        btn_reset = Button(text="RESET", size_hint_x=None, width=dp(58), background_color=C_BATAL, font_size=dp(12))
        btn_reset.bind(on_release=lambda *_: self.reset_transaksi())

        row_aksi.add_widget(btn_bayar)
        row_aksi.add_widget(btn_prev)
        row_aksi.add_widget(btn_simpan_psn)
        row_aksi.add_widget(btn_reset)
        container.add_widget(row_aksi)

        main_scroll.add_widget(container)
        self.area_konten.add_widget(main_scroll)
        self.refresh_keranjang()

    def dialog_pilih_customer(self, *args):
        app = App.get_running_app()
        custs = app.db.get("customers", {})
        if not custs:
            tampilkan_pesan("Database Pelanggan", "Belum ada data pelanggan tersimpan.\nIsi Nama & No. WA saat transaksi untuk menyimpan otomatis.")
            return

        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        scroll = ScrollView()
        lst = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        lst.bind(minimum_height=lst.setter("height"))

        popup = Popup(title="Pilih Customer Tersimpan", content=box, size_hint=(0.88, 0.7))

        for wa_key, info in custs.items():
            btn = Button(
                text=f"{info['nama']} - {info['no_wa']}",
                size_hint_y=None,
                height=dp(42),
                background_color=C_PRIMARY,
                font_size=dp(13)
            )
            def pilih(inst, n=info["nama"], w=info["no_wa"]):
                self.inp_cust_nama.text = n
                self.inp_cust_wa.text = w
                popup.dismiss()
            btn.bind(on_release=pilih)
            lst.add_widget(btn)

        scroll.add_widget(lst)
        box.add_widget(scroll)
        btn_tutup = Button(text="Tutup", size_hint_y=None, height=dp(40), background_color=C_BATAL)
        btn_tutup.bind(on_release=popup.dismiss)
        box.add_widget(btn_tutup)
        popup.open()

    def saat_metode_berubah(self, spinner, text):
        _, _, total_akhir = self.hitung_total()
        if text == "QRIS":
            self.inp_tunai.text = str(total_akhir)
            self.inp_tunai.disabled = True
        else:
            self.inp_tunai.disabled = False
            self.inp_tunai.text = ""

    def preview_keranjang_sekarang(self, *args):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang masih kosong!")
            return
        app = App.get_running_app()
        sub, disk, total_akhir = self.hitung_total()
        metode = self.spn_metode.text
        try:
            bayar = int(self.inp_tunai.text.strip() or total_akhir) if metode == "Tunai" else total_akhir
        except ValueError:
            bayar = total_akhir
        data_nota = {
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "meja": str(self.meja_val),
            "posisi": self.spn_posisi.text,
            "customer_nama": self.inp_cust_nama.text.strip(),
            "customer_wa": self.inp_cust_wa.text.strip(),
            "keranjang": copy.deepcopy(self.keranjang),
            "total": total_akhir,
            "total_awal": sub,
            "diskon": disk,
            "metode": metode,
            "dibayar": bayar,
            "kembalian": max(0, bayar - total_akhir),
            "kasir": app.user_aktif
        }
        self.preview_dan_cetak_struk(self.format_struk(data_nota), no_wa=data_nota["customer_wa"], judul="Preview Struk Transaksi")

    def ubah_meja(self, delta):
        self.meja_val = max(0, min(999, self.meja_val + delta))
        self.lbl_meja.text = f"Meja: {self.meja_val}"

    def ganti_kategori(self, spinner, text):
        self.kategori_aktif = text
        self.render_tombol_menu()

    def render_tombol_menu(self):
        app = App.get_running_app()
        self.grid_menu.clear_widgets()
        for kode, item in app.db["menu"].items():
            if self.kategori_aktif != "Semua" and item.get("kategori") != self.kategori_aktif:
                continue
            stok = int(item.get("stok", 0))
            warna_btn = C_PRIMARY if stok > 0 else C_BATAL
            btn = Button(
                text=f"{item['nama']}\nRp {item['harga']:,} | Stok: {stok}",
                size_hint_y=None,
                height=dp(60),
                background_color=warna_btn,
                font_size=dp(12),
                halign="center"
            )
            btn.bind(on_release=lambda inst, k=kode: self.tambah_item(k))
            self.grid_menu.add_widget(btn)

    def tambah_item(self, kode):
        app = App.get_running_app()
        m = app.db["menu"][kode]
        stok_tersedia = int(m.get("stok", 0))

        qty_di_keranjang = 0
        for item in self.keranjang:
            if item.get("kode") == kode or item["nama"] == m["nama"]:
                qty_di_keranjang = item["jumlah"]
                break

        if qty_di_keranjang + 1 > stok_tersedia:
            tampilkan_pesan("Stok Habis / Kurang", f"Stok '{m['nama']}' hanya tersisa {stok_tersedia} porsi.")
            return

        for item in self.keranjang:
            if item.get("kode") == kode or item["nama"] == m["nama"]:
                item["jumlah"] += 1
                item["subtotal"] = item["harga"] * item["jumlah"]
                self.refresh_keranjang()
                return

        self.keranjang.append({
            "kode": kode,
            "nama": m["nama"],
            "harga": m["harga"],
            "hpp": m.get("hpp", 0),
            "jumlah": 1,
            "subtotal": m["harga"],
            "kategori": m.get("kategori", "Makanan")
        })
        self.refresh_keranjang()

    def refresh_keranjang(self):
        self.box_keranjang.clear_widgets()
        if not self.keranjang:
            self.box_keranjang.add_widget(Label(text="Keranjang masih kosong", size_hint_y=None, height=dp(30), color=(0.7, 0.7, 0.7, 1)))
        else:
            for idx, item in enumerate(self.keranjang):
                row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
                row.add_widget(Label(text=f"{item['nama']} x{item['jumlah']}", halign="left", font_size=dp(13)))
                row.add_widget(Label(text=f"Rp {item['subtotal']:,}", size_hint_x=None, width=dp(95), font_size=dp(13)))

                b_min = Button(text="-", size_hint_x=None, width=dp(34), background_color=C_WARNING)
                b_plus = Button(text="+", size_hint_x=None, width=dp(34), background_color=C_SUKSES)
                b_del = Button(text="X", size_hint_x=None, width=dp(34), background_color=C_BATAL)

                b_min.bind(on_release=lambda inst, i=idx: self.ubah_qty(i, -1))
                b_plus.bind(on_release=lambda inst, i=idx: self.ubah_qty(i, 1))
                b_del.bind(on_release=lambda inst, i=idx: self.hapus_item(i))

                row.add_widget(b_min)
                row.add_widget(b_plus)
                row.add_widget(b_del)
                self.box_keranjang.add_widget(row)
        self.hitung_total()

    def ubah_qty(self, idx, delta):
        app = App.get_running_app()
        item = self.keranjang[idx]
        if delta > 0:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                stok_tersedia = int(app.db["menu"][kode].get("stok", 0))
                if item["jumlah"] + 1 > stok_tersedia:
                    tampilkan_pesan("Stok Kurang", f"Stok maksimal untuk '{item['nama']}' adalah {stok_tersedia}.")
                    return

        item["jumlah"] += delta
        if item["jumlah"] <= 0:
            self.keranjang.pop(idx)
        else:
            item["subtotal"] = item["harga"] * item["jumlah"]
        self.refresh_keranjang()

    def hapus_item(self, idx):
        self.keranjang.pop(idx)
        self.refresh_keranjang()

    def hitung_total(self):
        app = App.get_running_app()
        subtotal = sum(i["subtotal"] for i in self.keranjang)
        try:
            disk_manual = int(self.inp_diskon.text.strip() or 0)
        except ValueError:
            disk_manual = 0

        disk_karyawan = 0
        if self.chk_karyawan.active:
            disk_karyawan = int(subtotal * (app.db["diskon_karyawan_default"] / 100))

        total_diskon = min(subtotal, disk_manual + disk_karyawan)
        total_akhir = max(0, subtotal - total_diskon)
        self.lbl_total.text = f"TOTAL: Rp {total_akhir:,} (Diskon: Rp {total_diskon:,})"
        if hasattr(self, "spn_metode") and self.spn_metode.text == "QRIS":
            self.inp_tunai.text = str(total_akhir)
        return subtotal, total_diskon, total_akhir

    def reset_transaksi(self):
        self.keranjang = []
        self.meja_val = 0
        self.lbl_meja.text = "Meja: 0"
        self.inp_diskon.text = "0"
        self.spn_metode.text = "Tunai"
        self.inp_tunai.disabled = False
        self.inp_tunai.text = ""
        self.inp_cust_nama.text = ""
        self.inp_cust_wa.text = ""
        self.chk_karyawan.active = False
        self.idx_pesanan_ditemukan = -1
        self.refresh_keranjang()

    def simpan_customer_ke_db(self, nama, no_wa):
        app = App.get_running_app()
        wa_norm = normalisasi_no_wa(no_wa)
        if not wa_norm and not nama:
            return
        key = wa_norm if wa_norm else nama.lower()
        existing = app.db["customers"].get(key, {})
        app.db["customers"][key] = {
            "nama": nama if nama else existing.get("nama", "Pelanggan"),
            "no_wa": no_wa.strip() if no_wa.strip() else existing.get("no_wa", ""),
            "total_kunjungan": existing.get("total_kunjungan", 0) + 1,
            "terakhir_belanja": datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        }

    def simpan_pending(self):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang masih kosong!")
            return
        app = App.get_running_app()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        inp_nama = TextInput(text=self.inp_cust_nama.text.strip(), hint_text="Masukkan Nama Pemesan", multiline=False, size_hint_y=None, height=dp(44))
        box.add_widget(inp_nama)
        btn_ok = Button(text="Simpan Pesanan", size_hint_y=None, height=dp(44), background_color=C_SUKSES, bold=True)
        box.add_widget(btn_ok)
        popup = Popup(title="Simpan Pesanan Belum Bayar", content=box, size_hint=(0.85, 0.35))

        def do_save(*_):
            nama = inp_nama.text.strip()
            if not nama:
                tampilkan_pesan("Error", "Nama pemesan wajib diisi!")
                return
            sub, disk, tot = self.hitung_total()
            app.db["pesanan_belum_bayar"].append({
                "nama_pemesan": nama,
                "customer_wa": self.inp_cust_wa.text.strip(),
                "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
                "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                "meja": str(self.meja_val),
                "posisi": self.spn_posisi.text,
                "keranjang": copy.deepcopy(self.keranjang),
                "total": tot,
                "total_awal": sub,
                "diskon": disk,
                "kasir": app.user_aktif
            })
            app.simpan_database()
            popup.dismiss()
            self.reset_transaksi()
            self.tampilkan_kasir()
            tampilkan_pesan("Sukses", f"Pesanan '{nama}' disimpan!")

        btn_ok.bind(on_release=do_save)
        popup.open()

    def muat_pesanan_pending(self, *args):
        app = App.get_running_app()
        cari = self.inp_cari_psn.text.strip().lower()
        if not cari:
            tampilkan_pesan("Peringatan", "Masukkan nama pemesan!")
            return
        for idx, psn in enumerate(app.db["pesanan_belum_bayar"]):
            if psn["nama_pemesan"].lower() == cari:
                self.keranjang = copy.deepcopy(psn["keranjang"])
                self.inp_cust_nama.text = psn["nama_pemesan"]
                self.inp_cust_wa.text = psn.get("customer_wa", "")
                self.meja_val = int(psn.get("meja", 0))
                self.lbl_meja.text = f"Meja: {self.meja_val}"
                self.spn_posisi.text = psn.get("posisi", "Take-Away")
                self.inp_diskon.text = str(psn.get("diskon", 0))
                self.idx_pesanan_ditemukan = idx
                self.refresh_keranjang()
                tampilkan_pesan("Ditemukan", f"Pesanan '{psn['nama_pemesan']}' dimuat.")
                return
        tampilkan_pesan("Info", f"Pesanan '{cari}' tidak ditemukan.")

    def lihat_semua_pending(self, *args):
        app = App.get_running_app()
        psn_list = app.db["pesanan_belum_bayar"]
        if not psn_list:
            tampilkan_pesan("Info", "Tidak ada pesanan pending.")
            return
        teks = "\n".join([f"{i}. {p['nama_pemesan']} | Meja {p['meja']} | Rp {p['total']:,}" for i, p in enumerate(psn_list, 1)])
        tampilkan_pesan("Daftar Pesanan Pending", teks)

    def proses_bayar(self, *args):
        if not self.keranjang:
            tampilkan_pesan("Peringatan", "Keranjang belanja kosong!")
            return

        app = App.get_running_app()
        for item in self.keranjang:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                stok_kini = int(app.db["menu"][kode].get("stok", 0))
                if item["jumlah"] > stok_kini:
                    tampilkan_pesan("Stok Tidak Cukup", f"Stok '{item['nama']}' tersisa {stok_kini}, tidak cukup untuk {item['jumlah']} porsi.")
                    return

        sub, disk, total_akhir = self.hitung_total()
        metode = self.spn_metode.text

        if metode == "Tunai":
            try:
                bayar = int(self.inp_tunai.text.strip() or 0)
            except ValueError:
                tampilkan_pesan("Error", "Nominal tunai tidak valid!")
                return
            if bayar < total_akhir:
                tampilkan_pesan("Uang Kurang", f"Total: Rp {total_akhir:,}\nUang Anda: Rp {bayar:,}")
                return
            kembalian = bayar - total_akhir
        else:
            bayar = total_akhir
            kembalian = 0

        for item in self.keranjang:
            kode = item.get("kode")
            if kode and kode in app.db["menu"]:
                app.db["menu"][kode]["stok"] = max(0, int(app.db["menu"][kode].get("stok", 0)) - item["jumlah"])

        cust_nama = self.inp_cust_nama.text.strip()
        cust_wa = self.inp_cust_wa.text.strip()
        self.simpan_customer_ke_db(cust_nama, cust_wa)

        if 0 <= self.idx_pesanan_ditemukan < len(app.db["pesanan_belum_bayar"]):
            app.db["pesanan_belum_bayar"].pop(self.idx_pesanan_ditemukan)
            self.idx_pesanan_ditemukan = -1

        data_nota = {
            "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
            "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
            "meja": str(self.meja_val),
            "posisi": self.spn_posisi.text,
            "customer_nama": cust_nama,
            "customer_wa": cust_wa,
            "keranjang": copy.deepcopy(self.keranjang),
            "total": total_akhir,
            "total_awal": sub,
            "diskon": disk,
            "metode": metode,
            "dibayar": bayar,
            "kembalian": kembalian,
            "kasir": app.user_aktif
        }
        app.db["riwayat_transaksi"].append(data_nota)
        app.saldo_kas += total_akhir
        app.simpan_database()

        self.lbl_status.text = f"{app.user_aktif} ({app.role_aktif.upper()}) | Rp {app.saldo_kas:,}"
        self.render_tombol_menu()
        struk = self.format_struk(data_nota)

        cfg = app.db["pengaturan_printer"]
        if cfg.get("bluetooth_mac"):
            self.kirim_bluetooth(struk, silent_success=True)

        self.preview_dan_cetak_struk(struk, no_wa=cust_wa, judul="Struk Transaksi Berhasil")
        self.reset_transaksi()

    def format_struk(self, nota):
        app = App.get_running_app()
        lebar = int(app.db["pengaturan_printer"].get("lebar_struk", 32))
        profil = app.db["profil_toko"]
        garis = "=" * lebar
        tipis = "-" * lebar

        nama_toko = profil.get("nama", "WARUNG").upper()
        alamat_toko = profil.get("alamat", "")
        kota_toko = profil.get("kota", "")
        telp_toko = profil.get("telepon", "")
        footer_toko = profil.get("footer", "Terima Kasih")

        teks = f"{nama_toko:^{lebar}}\n"
        if alamat_toko:
            teks += f"{alamat_toko:^{lebar}}\n"
        if kota_toko:
            teks += f"{kota_toko:^{lebar}}\n"
        if telp_toko:
            teks += f"{'Telp: ' + telp_toko:^{lebar}}\n"
        teks += garis + "\n"
        teks += f"Tgl  : {nota['tanggal']} {nota['waktu'][:5]}\n"
        teks += f"Kasir: {nota['kasir']} | Meja: {nota['meja']}\n"
        if nota.get("customer_nama"):
            teks += f"Cust : {nota['customer_nama']}\n"
        teks += tipis + "\n"

        for item in nota["keranjang"]:
            teks += f"{item['nama'][:lebar]}\n"
            teks += f"  {item['jumlah']} x {item['harga']:,} = Rp {item['subtotal']:,}\n"

        teks += tipis + "\n"
        teks += f"SUBTOTAL : Rp {nota['total_awal']:,}\n"
        if nota["diskon"] > 0:
            teks += f"DISKON   : Rp ({nota['diskon']:,})\n"
        teks += f"TOTAL    : Rp {nota['total']:,}\n"
        teks += f"METODE   : {nota['metode']}\n"
        if nota["metode"] == "Tunai":
            teks += f"TUNAI    : Rp {nota['dibayar']:,}\n"
            teks += f"KEMBALI  : Rp {nota['kembalian']:,}\n"
        teks += garis + "\n"
        teks += f"{footer_toko:^{lebar}}\n"
        return teks

    def preview_dan_cetak_struk(self, teks_struk, no_wa="", judul="Preview Struk"):
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scroll = ScrollView()
        lbl = Label(text=teks_struk, font_size=dp(13), size_hint_y=None, halign="left", valign="top")
        lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        scroll.add_widget(lbl)
        box.add_widget(scroll)

        row_wa = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        inp_wa_popup = TextInput(text=no_wa, hint_text="No. WA Customer (08xxx)", input_filter="int", multiline=False, font_size=dp(13))
        row_wa.add_widget(inp_wa_popup)
        box.add_widget(row_wa)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        btn_cetak = Button(text="Cetak BT", background_color=C_SUKSES, bold=True, font_size=dp(13))
        btn_wa = Button(text="Kirim WA", background_color=C_WA, bold=True, font_size=dp(13))
        btn_tutup = Button(text="Tutup", size_hint_x=None, width=dp(70), background_color=C_BATAL, font_size=dp(13))
        btn_row.add_widget(btn_cetak)
        btn_row.add_widget(btn_wa)
        btn_row.add_widget(btn_tutup)
        box.add_widget(btn_row)

        popup = Popup(title=judul, content=box, size_hint=(0.92, 0.82))
        btn_cetak.bind(on_release=lambda *_: self.kirim_bluetooth(teks_struk))
        btn_wa.bind(on_release=lambda *_: kirim_struk_whatsapp(inp_wa_popup.text.strip(), teks_struk))
        btn_tutup.bind(on_release=popup.dismiss)
        popup.open()

    def kirim_bluetooth(self, teks, silent_success=False):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        mac = cfg.get("bluetooth_mac", "").strip()
        channel = int(cfg.get("bluetooth_channel", 1))
        cutting = cfg.get("cutting_paper", True)
        cashdrawer = cfg.get("cashdrawer", False)

        if not mac:
            if not silent_success:
                tampilkan_pesan("Printer Belum Dipilih", "Buka menu 'Printer BT' lalu pilih perangkat Bluetooth yang sudah ter-pair.")
            return

        sukses, pesan = app.bt_manager.kirim_data(teks, mac, channel, cutting, cashdrawer)
        self.update_bt_badge()
        if sukses:
            if not silent_success:
                tampilkan_pesan("Sukses", pesan)
        else:
            tampilkan_pesan("Info Printer", pesan)

    # ===================== 2. DATABASE PELANGGAN =====================
    def tampilkan_pelanggan(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="DATABASE PELANGGAN & WHATSAPP", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_nama = TextInput(hint_text="Nama Customer", multiline=False, size_hint_y=None, height=dp(42))
        inp_wa = TextInput(hint_text="No. WhatsApp (cth: 08123456789)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        box.add_widget(inp_nama)
        box.add_widget(inp_wa)

        def tambah_cust(*_):
            n = inp_nama.text.strip()
            w = inp_wa.text.strip()
            if not n or not w:
                tampilkan_pesan("Error", "Nama dan No. WA wajib diisi!")
                return
            self.simpan_customer_ke_db(n, w)
            app.simpan_database()
            tampilkan_pesan("Sukses", f"Pelanggan '{n}' ({w}) tersimpan!")
            self.tampilkan_pelanggan()

        btn_save = Button(text="SIMPAN DATA PELANGGAN", size_hint_y=None, height=dp(44), background_color=C_SUKSES, bold=True)
        btn_save.bind(on_release=tambah_cust)
        box.add_widget(btn_save)

        custs = app.db.get("customers", {})
        box.add_widget(Label(text=f"DAFTAR PELANGGAN ({len(custs)}):", bold=True, size_hint_y=None, height=dp(28)))
        for k, info in custs.items():
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            row.add_widget(Label(
                text=f"{info['nama']} | WA: {info['no_wa']} ({info.get('total_kunjungan', 1)}x)",
                font_size=dp(12), halign="left"
            ))
            btn_chat = Button(text="Chat WA", size_hint_x=None, width=dp(72), background_color=C_WA, font_size=dp(12))
            btn_chat.bind(on_release=lambda inst, w=info["no_wa"]: kirim_struk_whatsapp(w, f"Halo kak, salam dari {app.db['profil_toko']['nama']}!"))
            row.add_widget(btn_chat)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 3. PROFIL WARUNG & PREVIEW STRUK (OWNER) =====================
    def tampilkan_profil_warung(self):
        app = App.get_running_app()
        profil = app.db["profil_toko"]
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="PENGATURAN NAMA WARUNG & STRUK", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_nama = TextInput(text=profil.get("nama", ""), hint_text="Nama Warung (Display & Header Struk)", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_alamat = TextInput(text=profil.get("alamat", ""), hint_text="Alamat Warung", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_kota = TextInput(text=profil.get("kota", ""), hint_text="Kota / Kabupaten", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_telp = TextInput(text=profil.get("telepon", ""), hint_text="No. Telepon / WA", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))
        inp_footer = TextInput(text=profil.get("footer", ""), hint_text="Pesan Footer Bawah Struk", multiline=False, size_hint_y=None, height=dp(44), font_size=dp(14))

        for lbl_txt, widget in [
            ("Nama Warung:", inp_nama),
            ("Alamat:", inp_alamat),
            ("Kota:", inp_kota),
            ("Telepon / WA:", inp_telp),
            ("Footer Struk:", inp_footer)
        ]:
            box.add_widget(Label(text=lbl_txt, size_hint_y=None, height=dp(20), halign="left", font_size=dp(12)))
            box.add_widget(widget)

        def terapkan_form_ke_db():
            nama_baru = inp_nama.text.strip()
            if not nama_baru:
                tampilkan_pesan("Peringatan", "Nama Warung tidak boleh kosong!")
                return False
            profil["nama"] = nama_baru
            profil["alamat"] = inp_alamat.text.strip()
            profil["kota"] = inp_kota.text.strip()
            profil["telepon"] = inp_telp.text.strip()
            profil["footer"] = inp_footer.text.strip()
            app.simpan_database()
            self.refresh_nama_warung_display()
            return True

        def simpan_profil(*_):
            if terapkan_form_ke_db():
                catat_audit(app.role_aktif, app.user_aktif, "PROFIL_UPDATE", f"nama={profil['nama']}")
                tampilkan_pesan("Sukses", f"Nama warung diubah menjadi:\n{profil['nama'].upper()}\n\nLayar utama dan struk otomatis diperbarui.")

        def preview_profil_struk(*_):
            if not terapkan_form_ke_db():
                return
            contoh_nota = {
                "tanggal": datetime.datetime.now().strftime("%d-%m-%Y"),
                "waktu": datetime.datetime.now().strftime("%H:%M:%S"),
                "meja": "3",
                "posisi": "Lesehan",
                "customer_nama": "Budi",
                "keranjang": [
                    {"nama": "Nasi Liwet Solo", "harga": 20000, "jumlah": 2, "subtotal": 40000},
                    {"nama": "Es Teh Manis", "harga": 5000, "jumlah": 2, "subtotal": 10000}
                ],
                "total": 50000,
                "total_awal": 50000,
                "diskon": 0,
                "metode": "QRIS",
                "dibayar": 50000,
                "kembalian": 0,
                "kasir": app.user_aktif or "owner"
            }
            teks = self.format_struk(contoh_nota)
            self.preview_dan_cetak_struk(teks, judul=f"Preview Struk - {profil['nama'].upper()}")

        row_btn = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_simpan = Button(text="SIMPAN NAMA WARUNG", background_color=C_SUKSES, bold=True, font_size=dp(12))
        btn_simpan.bind(on_release=simpan_profil)

        btn_preview = Button(text="PREVIEW & CETAK STRUK", background_color=C_AKSEN, bold=True, font_size=dp(12))
        btn_preview.bind(on_release=preview_profil_struk)

        row_btn.add_widget(btn_simpan)
        row_btn.add_widget(btn_preview)
        box.add_widget(row_btn)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 4. SETTING PRINTER BT =====================
    def tampilkan_printer(self):
        app = App.get_running_app()
        cfg = app.db["pengaturan_printer"]
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(8))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="INSTALASI PRINTER BLUETOOTH", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        lbl_step1 = Label(
            text="1. Pastikan Printer sudah di-Pair di Pengaturan Bluetooth HP.\n2. Tekan Scan lalu pilih nama printer:",
            font_size=dp(12), size_hint_y=None, height=dp(38), halign="left"
        )
        lbl_step1.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        box.add_widget(lbl_step1)

        row_scan = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        default_label = f"{cfg['bluetooth_name']} ({cfg['bluetooth_mac']})" if cfg.get("bluetooth_mac") else "Pilih Printer Bluetooth..."
        self.spn_bt_devices = Spinner(text=default_label, values=[], font_size=dp(13))
        btn_scan = Button(text="Scan BT", size_hint_x=None, width=dp(85), background_color=C_AKSEN, bold=True)
        row_scan.add_widget(self.spn_bt_devices)
        row_scan.add_widget(btn_scan)
        box.add_widget(row_scan)

        inp_mac = TextInput(text=cfg.get("bluetooth_mac", ""), hint_text="MAC Address (otomatis terisi saat pilih di atas)", multiline=False, size_hint_y=None, height=dp(42))
        spn_lebar = Spinner(text=str(cfg.get("lebar_struk", 32)), values=["32", "42", "48"], size_hint_y=None, height=dp(42))

        def jalankan_scan(*_):
            app.bt_manager.minta_izin()
            devices = app.bt_manager.scan_paired_devices()
            self.paired_map = {}
            if not devices:
                tampilkan_pesan(
                    "Perangkat Tidak Ditemukan",
                    "Tidak ada perangkat Bluetooth ter-pair yang terbaca.\n\nPastikan:\n1. Bluetooth HP menyala\n2. Printer sudah di-Pair di Pengaturan HP\n3. Izin Perangkat Terdekat diizinkan."
                )
                return
            pilihan = []
            for nama, mac in devices:
                label = f"{nama} ({mac})"
                self.paired_map[label] = (nama, mac)
                pilihan.append(label)
            self.spn_bt_devices.values = pilihan
            self.spn_bt_devices.text = pilihan[0]

        def saat_printer_dipilih(spinner, text):
            if text in self.paired_map:
                nama, mac = self.paired_map[text]
                inp_mac.text = mac
                cfg["bluetooth_name"] = nama
                cfg["bluetooth_mac"] = mac
                app.simpan_database()
                ok, msg = app.bt_manager.connect(mac, cfg.get("bluetooth_channel", 1))
                self.update_bt_badge()
                tampilkan_pesan("Status Koneksi", msg)

        btn_scan.bind(on_release=jalankan_scan)
        self.spn_bt_devices.bind(text=saat_printer_dipilih)

        box.add_widget(Label(text="MAC Address Aktif:", size_hint_y=None, height=dp(22)))
        box.add_widget(inp_mac)
        box.add_widget(Label(text="Lebar Kertas (58mm = 32 | 80mm = 42):", size_hint_y=None, height=dp(22)))
        box.add_widget(spn_lebar)

        def simpan_dan_sambungkan(*_):
            mac_val = inp_mac.text.strip().upper()
            cfg["bluetooth_mac"] = mac_val
            if not cfg.get("bluetooth_name"):
                cfg["bluetooth_name"] = "Printer Thermal"
            cfg["lebar_struk"] = int(spn_lebar.text)
            app.simpan_database()
            ok, msg = app.bt_manager.connect(mac_val, cfg.get("bluetooth_channel", 1))
            self.update_bt_badge()
            tampilkan_pesan("Simpan & Koneksi", f"Pengaturan disimpan.\nStatus: {msg}")

        btn_save = Button(text="SIMPAN & SAMBUNGKAN SEKARANG", size_hint_y=None, height=dp(48), background_color=C_SUKSES, bold=True)
        btn_save.bind(on_release=simpan_dan_sambungkan)

        btn_test = Button(text="TEST CETAK STRUK", size_hint_y=None, height=dp(48), background_color=C_WARNING, bold=True)
        btn_test.bind(on_release=lambda *_: self.kirim_bluetooth(f"=== {app.db['profil_toko']['nama'].upper()} ===\nKoneksi Bluetooth Berhasil!\n\n"))

        box.add_widget(btn_save)
        box.add_widget(btn_test)
        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)
        jalankan_scan()

    # ===================== 5. EDIT MENU & STOK (OWNER) =====================
    def tampilkan_edit_menu(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="KELOLA MENU, HPP & STOK", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_kode = TextInput(hint_text="Kode Menu (cth: 6)", multiline=False, size_hint_y=None, height=dp(42))
        inp_nama = TextInput(hint_text="Nama Menu", multiline=False, size_hint_y=None, height=dp(42))
        inp_harga = TextInput(hint_text="Harga Jual (Rp)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        inp_hpp = TextInput(hint_text="HPP / Modal (Rp)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        inp_stok = TextInput(hint_text="Jumlah Stok Tersedia (Porsi)", input_filter="int", multiline=False, size_hint_y=None, height=dp(42))
        spn_kat = Spinner(text=app.db["kategori_menu"][0], values=app.db["kategori_menu"], size_hint_y=None, height=dp(42))

        for w in [inp_kode, inp_nama, inp_harga, inp_hpp, inp_stok, spn_kat]:
            box.add_widget(w)

        def simpan_menu(*_):
            k = inp_kode.text.strip()
            n = inp_nama.text.strip()
            if not k or not n:
                tampilkan_pesan("Error", "Kode dan Nama menu wajib diisi!")
                return
            h = int(inp_harga.text or 0)
            hpp = int(inp_hpp.text or 0)
            stok = int(inp_stok.text or 0)
            app.db["menu"][k] = {"nama": n, "harga": h, "hpp": hpp, "stok": stok, "kategori": spn_kat.text}
            app.simpan_database()
            tampilkan_pesan("Sukses", f"Menu '{n}' (Stok: {stok}) tersimpan!")
            self.tampilkan_edit_menu()

        btn_simpan = Button(text="SIMPAN / UPDATE MENU & STOK", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_simpan.bind(on_release=simpan_menu)
        box.add_widget(btn_simpan)

        box.add_widget(Label(text="DAFTAR MENU & STOK SAAT INI:", bold=True, size_hint_y=None, height=dp(30)))
        for k, v in app.db["menu"].items():
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
            row.add_widget(Label(
                text=f"[{k}] {v['nama']} | Jual: {v['harga']:,} | HPP: {v.get('hpp', 0):,} | Stok: {v.get('stok', 0)}",
                font_size=dp(11), halign="left"
            ))
            btn_edit = Button(text="Isi", size_hint_x=None, width=dp(45), background_color=C_AKSEN, font_size=dp(11))
            btn_hapus = Button(text="Hapus", size_hint_x=None, width=dp(55), background_color=C_BATAL, font_size=dp(11))

            def isi_form(kode_e=k, data_e=v):
                inp_kode.text = kode_e
                inp_nama.text = data_e["nama"]
                inp_harga.text = str(data_e["harga"])
                inp_hpp.text = str(data_e.get("hpp", 0))
                inp_stok.text = str(data_e.get("stok", 0))
                spn_kat.text = data_e.get("kategori", "Makanan")

            def hapus(kode_del=k):
                del app.db["menu"][kode_del]
                app.simpan_database()
                self.tampilkan_edit_menu()

            btn_edit.bind(on_release=lambda inst, ke=k, de=v: isi_form(ke, de))
            btn_hapus.bind(on_release=lambda inst, kd=k: hapus(kd))
            row.add_widget(btn_edit)
            row.add_widget(btn_hapus)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 6. BIAYA OPERASIONAL (OWNER) =====================
    def tampilkan_promosi_ops(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="BIAYA OPERASIONAL BULANAN", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))
        ops = app.db["biaya_operasional"]
        fields = {}
        for key in ["sewa", "listrik", "air", "gas", "karyawan", "transportasi", "lainnya"]:
            row = BoxLayout(size_hint_y=None, height=dp(40))
            row.add_widget(Label(text=key.capitalize(), size_hint_x=0.4))
            ti = TextInput(text=str(ops.get(key, 0)), input_filter="int", multiline=False)
            fields[key] = ti
            row.add_widget(ti)
            box.add_widget(row)

        def simpan_ops(*_):
            for k, ti in fields.items():
                ops[k] = int(ti.text or 0)
            app.simpan_database()
            total_ops = sum(ops.values())
            tampilkan_pesan("Sukses", f"Biaya Operasional tersimpan!\nTotal: Rp {total_ops:,} / bulan")

        btn_ops = Button(text="SIMPAN BIAYA OPERASIONAL", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_ops.bind(on_release=simpan_ops)
        box.add_widget(btn_ops)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    # ===================== 7. LAPORAN RUGI LABA (1 BULAN & 1 TAHUN) + PDF =====================
    def tampilkan_laporan(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        root_lap = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))

        row_ctrl = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        spn_periode = Spinner(text="Laporan 1 Bulan", values=["Laporan 1 Bulan", "Laporan 1 Tahun"], size_hint_x=0.42, font_size=dp(12))
        now = datetime.datetime.now()
        inp_filter = TextInput(text=now.strftime("%m-%Y"), hint_text="MM-YYYY atau YYYY", multiline=False, size_hint_x=0.28, font_size=dp(13))
        btn_hitung = Button(text="Tampilkan", size_hint_x=0.30, background_color=C_AKSEN, bold=True, font_size=dp(12))

        row_ctrl.add_widget(spn_periode)
        row_ctrl.add_widget(inp_filter)
        row_ctrl.add_widget(btn_hitung)
        root_lap.add_widget(row_ctrl)

        scroll = ScrollView()
        lbl_laporan = Label(text="", font_size=dp(13), size_hint_y=None, halign="left", valign="top")
        lbl_laporan.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        lbl_laporan.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        scroll.add_widget(lbl_laporan)
        root_lap.add_widget(scroll)

        btn_pdf = Button(text="SALIN / SIMPAN LAPORAN KE PDF", size_hint_y=None, height=dp(46), background_color=C_BATAL, bold=True, font_size=dp(13))
        root_lap.add_widget(btn_pdf)

        self.data_laporan_terakhir = {}

        def saat_ganti_jenis(spinner, val):
            if val == "Laporan 1 Bulan":
                inp_filter.text = datetime.datetime.now().strftime("%m-%Y")
            else:
                inp_filter.text = datetime.datetime.now().strftime("%Y")
            hitung_dan_tampilkan()

        def hitung_dan_tampilkan(*_):
            jenis = spn_periode.text
            kunci_waktu = inp_filter.text.strip()
            trx_semua = app.db["riwayat_transaksi"]

            if jenis == "Laporan 1 Bulan":
                trx_filtered = [t for t in trx_semua if t.get("tanggal", "").endswith(kunci_waktu)]
                pengali_ops = 1
                judul_periode = f"PERIODE 1 BULAN ({kunci_waktu})"
            else:
                trx_filtered = [t for t in trx_semua if t.get("tanggal", "").endswith(kunci_waktu)]
                pengali_ops = 12
                judul_periode = f"PERIODE 1 TAHUN ({kunci_waktu})"

            total_omset = sum(t.get("total", 0) for t in trx_filtered)
            total_hpp = 0
            total_item = 0

            sub_tunai = {"trx": 0, "omset": 0}
            sub_qris = {"trx": 0, "omset": 0}
            sub_lain = {"trx": 0, "omset": 0}

            for t in trx_filtered:
                m = t.get("metode", "Tunai").upper()
                nom = t.get("total", 0)
                if m == "TUNAI":
                    sub_tunai["trx"] += 1
                    sub_tunai["omset"] += nom
                elif m == "QRIS":
                    sub_qris["trx"] += 1
                    sub_qris["omset"] += nom
                else:
                    sub_lain["trx"] += 1
                    sub_lain["omset"] += nom

                for it in t.get("keranjang", []):
                    total_hpp += it.get("hpp", 0) * it.get("jumlah", 0)
                    total_item += it.get("jumlah", 0)

            gross_profit = total_omset - total_hpp
            biaya_ops_bulanan = sum(app.db["biaya_operasional"].values())
            total_biaya_ops = biaya_ops_bulanan * pengali_ops
            net_profit = gross_profit - total_biaya_ops
            status_rl = "LABA BERSIH" if net_profit >= 0 else "RUGI BERSIH"

            atv = (total_omset / len(trx_filtered)) if trx_filtered else 0
            gm_persen = (gross_profit / total_omset * 100) if total_omset > 0 else 0
            nm_persen = (net_profit / total_omset * 100) if total_omset > 0 else 0

            nama_warung = app.db["profil_toko"]["nama"].upper()
            teks = (
                f"LAPORAN RUGI LABA - {nama_warung}\n"
                f"{judul_periode}\n"
                f"==========================================\n"
                f"1. REKAP SUB TOTAL METODE PEMBAYARAN\n"
                f"   - Sub Total TUNAI : {sub_tunai['trx']} trx | Rp {sub_tunai['omset']:,}\n"
                f"   - Sub Total QRIS  : {sub_qris['trx']} trx | Rp {sub_qris['omset']:,}\n"
            )
            if sub_lain["trx"] > 0:
                teks += f"   - Sub Total Lain  : {sub_lain['trx']} trx | Rp {sub_lain['omset']:,}\n"
            teks += (
                f"   ---------------------------------------\n"
                f"   TOTAL OMSET       : {len(trx_filtered)} trx ({total_item} porsi) | Rp {total_omset:,}\n\n"
                f"2. PERHITUNGAN RUGI LABA\n"
                f"   Pendapatan / Omset : Rp {total_omset:,}\n"
                f"   Harga Pokok (HPP)  : Rp ({total_hpp:,})\n"
                f"   ---------------------------------------\n"
                f"   LABA KOTOR (Gross) : Rp {gross_profit:,} ({gm_persen:.1f}%)\n"
                f"   Biaya Operasional  : Rp ({total_biaya_ops:,}) ({pengali_ops} bln)\n"
                f"   =======================================\n"
                f"   {status_rl:<18} : Rp {net_profit:,} ({nm_persen:.1f}%)\n"
                f"   Rata-rata / Nota   : Rp {atv:,.0f}\n\n"
                f"3. SISA STOK MENU SAAT INI\n"
            )
            for kd, mn in app.db["menu"].items():
                teks += f"   - {mn['nama']}: {mn.get('stok', 0)} porsi\n"

            lbl_laporan.text = teks
            self.data_laporan_terakhir = {
                "judul_periode": judul_periode,
                "kunci_waktu": kunci_waktu.replace("-", "_"),
                "teks": teks
            }

        def ekspor_ke_pdf(*_):
            if not self.data_laporan_terakhir:
                hitung_dan_tampilkan()
            try:
                nama_file = f"Laporan_Rugi_Laba_{self.data_laporan_terakhir['kunci_waktu']}.pdf"
                if platform == "android":
                    folder_dl = "/storage/emulated/0/Download"
                    os.makedirs(folder_dl, exist_ok=True)
                    path_output = os.path.join(folder_dl, nama_file)
                else:
                    path_output = os.path.abspath(nama_file)

                simpan_teks_ke_pdf_murni(self.data_laporan_terakhir["teks"], path_output)
                tampilkan_pesan("PDF Berhasil Disimpan", f"Laporan Rugi Laba berhasil disimpan dalam format PDF:\n\n{path_output}")
            except Exception as e:
                tampilkan_pesan("Gagal Ekspor PDF", f"Terjadi kesalahan saat membuat PDF:\n{e}")

        spn_periode.bind(text=saat_ganti_jenis)
        btn_hitung.bind(on_release=hitung_dan_tampilkan)
        btn_pdf.bind(on_release=ekspor_ke_pdf)

        self.area_konten.add_widget(root_lap)
        hitung_dan_tampilkan()

    # ===================== 8. MANAJEMEN USER & ROLE (OWNER) =====================
    def tampilkan_manajemen_user(self):
        app = App.get_running_app()
        self.area_konten.clear_widgets()

        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(6))
        box.bind(minimum_height=box.setter("height"))

        box.add_widget(Label(text="MANAJEMEN USER & ROLE", bold=True, font_size=dp(16), size_hint_y=None, height=dp(30)))

        inp_u = TextInput(hint_text="Username Baru", multiline=False, size_hint_y=None, height=dp(42))
        inp_p = TextInput(hint_text="Password", multiline=False, size_hint_y=None, height=dp(42))
        spn_r = Spinner(text="kasir", values=["kasir", "owner"], size_hint_y=None, height=dp(42))

        box.add_widget(inp_u)
        box.add_widget(inp_p)
        box.add_widget(spn_r)

        def tambah_user(*_):
            u = inp_u.text.strip()
            p = inp_p.text.strip()
            r = spn_r.text
            if not u or not p:
                tampilkan_pesan("Error", "Username dan Password wajib diisi!")
                return
            app.db["users"][u] = {"password": p, "role": r, "nama": u}
            app.simpan_database()
            catat_audit(app.role_aktif, app.user_aktif, "USER_CREATE", f"user={u}, role={r}")
            tampilkan_pesan("Sukses", f"User '{u}' ({r}) berhasil dibuat!")
            self.tampilkan_manajemen_user()

        btn_add = Button(text="TAMBAH USER", size_hint_y=None, height=dp(46), background_color=C_SUKSES, bold=True)
        btn_add.bind(on_release=tambah_user)
        box.add_widget(btn_add)

        box.add_widget(Label(text="DAFTAR USER TERDAFTAR:", bold=True, size_hint_y=None, height=dp(28)))
        for u, info in app.db["users"].items():
            row = BoxLayout(size_hint_y=None, height=dp(38))
            row.add_widget(Label(text=f"User: {u} | Role: {info['role'].upper()}", halign="left"))
            if u != "owner":
                btn_del = Button(text="Hapus", size_hint_x=None, width=dp(65), background_color=C_BATAL)
                btn_del.bind(on_release=lambda inst, usr=u: self.hapus_user(usr))
                row.add_widget(btn_del)
            box.add_widget(row)

        scroll.add_widget(box)
        self.area_konten.add_widget(scroll)

    def hapus_user(self, uname):
        app = App.get_running_app()
        if uname in app.db["users"]:
            del app.db["users"][uname]
            app.simpan_database()
            catat_audit(app.role_aktif, app.user_aktif, "USER_DELETE", f"user={uname}")
            self.tampilkan_manajemen_user()


class KasirAndroidApp(App):
    def build(self):
        self.db = self.muat_database()
        self.title = self.db["profil_toko"].get("nama", "Kasir Warung")
        self.user_aktif = None
        self.role_aktif = None
        self.modal_awal = 0
        self.saldo_kas = 0
        self.bt_manager = BluetoothPrinterManager()
        self.bt_manager.minta_izin()

        sm = ScreenManager()
        self.login_screen = LoginScreen(name="login")
        self.main_screen = MainScreen(name="main")
        sm.add_widget(self.login_screen)
        sm.add_widget(self.main_screen)
        return sm

    def muat_database(self):
        if not os.path.exists(FILE_DATABASE):
            db = copy.deepcopy(DATA_AWAL)
            with open(FILE_DATABASE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4, ensure_ascii=False)
            return db
        try:
            with open(FILE_DATABASE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DATA_AWAL.items():
                if k not in data:
                    data[k] = copy.deepcopy(v)
            for m in data.get("menu", {}).values():
                if "stok" not in m:
                    m["stok"] = 20
            return data
        except Exception:
            return copy.deepcopy(DATA_AWAL)

    def simpan_database(self):
        try:
            with open(FILE_DATABASE, "w", encoding="utf-8") as f:
                json.dump(self.db, f, indent=4, ensure_ascii=False)
        except Exception as e:
            tampilkan_pesan("Error Database", f"Gagal menyimpan data: {e}")


if __name__ == "__main__":
    KasirAndroidApp().run()