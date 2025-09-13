import json
import os
import io
import sys
import banner
import textwrap
import shutil
from datetime import datetime

from api_request import get_otp, submit_otp, save_tokens, get_package, purchase_package, get_addons
from purchase_api import show_multipayment, show_qris_payment, settlement_bounty
from bookmark import show_bookmark_menu, BookmarkInstance
from auth_helper import AuthInstance
from util import display_html, clear_screen, pause, ascii_art, show_banner, save_banner_url
from package import show_package_details

from rich.console import Console
from rich.table import Table
from rich.align import Align
from rich import box
from rich.text import Text

console = Console()


max_col_width = 90 - 9

# -----------------------------
# Utils
# -----------------------------
def get_terminal_width(default=70):
    try:
        return shutil.get_terminal_size().columns
    except:
        return default


def show_banner():
    term_width = shutil.get_terminal_size().columns
    buffer = io.StringIO()
    sys.stdout = buffer
    ascii_art.to_terminal(columns=60)
    sys.stdout = sys.__stdout__
    banner_lines = [line.center(term_width) for line in buffer.getvalue().splitlines()]
    console.print("\n".join(banner_lines), style="bold blue")


# -----------------------------
# Render table full-width dengan Rich
# -----------------------------
def render_table(title, rows, headers=None, aligns=None, style="white", show_header=True):
    """Render table dengan Rich, full-width, border tebal, judul bold, kolom Value left-aligned"""
    term_width = shutil.get_terminal_size().columns

    table = Table(
        show_lines=True,
        show_header=show_header,
        title=Text(title, style=f"bold {style}", justify="center"),
        box=box.DOUBLE_EDGE,
        width=term_width
    )

    n_cols = len(headers) if headers else len(rows[0]) if rows else 1

    # Default alignment
    if aligns is None:
        aligns = ["center"] * n_cols

    # Pastikan kolom Value align left jika ada
    if headers and "Value" in headers:
        for i, h in enumerate(headers):
            if h.lower() == "value":
                aligns[i] = "left"

    # Tambahkan kolom
    if headers:
        for i, h in enumerate(headers):
            col_align = aligns[i] if i < len(aligns) else "left"
            table.add_column(h, justify=col_align, style=style)
    else:
        for i in range(n_cols):
            col_align = aligns[i] if i < len(aligns) else "left"
            table.add_column("", justify=col_align, style=style)

    # Tambahkan baris
    for row in rows:
        str_row = [str(cell) for cell in row]
        table.add_row(*str_row)

    # Center table
    console.print(Align.center(table))

# -----------------------------
# UI Functions
# -----------------------------
def show_main_menu(number, balance, balance_expired_at, display_quota=None):
    clear_screen()
    show_banner()
    expired_at_dt = datetime.fromtimestamp(balance_expired_at).strftime("%Y-%m-%d %H:%M:%S")

    account_info = [
        ["📱 Nomor", number],
        ["💰 Pulsa", f"Rp {balance}"],
        ["⏳ Masa Aktif", expired_at_dt],
    ]
    if display_quota:
        account_info.append(["📶 Kuota", display_quota])

    menu_options = [
        ["1", "☑️ Login/Ganti akun"],
        ["2", "🔹 Lihat Paket Saya"],
        ["3", "🛒 Beli Paket XUT"],
        ["4", "💎 Beli Paket Berdasarkan Family Code"],
        ["5", "💎 Beli Paket Berdasarkan Family Code (Enterprise)"],
        ["6", "✨ List Family Code"],
        ["7", "📔 Bookmarks Paket"],
        ["8", "⚙️ Pengaturan"],
        ["99", "❌ Tutup aplikasi"],
    ]

    render_table("INFORMASI AKUN", account_info, headers=["Keterangan", "Value"], aligns=["left", "left"], style="red",show_header=False)
    render_table("MAIN MENU", menu_options, headers=["No", "Keterangan"], aligns=["center", "left"], style="blue",show_header=False)

def show_account_menu():
    clear_screen()
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active_user = AuthInstance.get_active_user()

    in_account_menu = True
    add_user = False
    while in_account_menu:
        clear_screen()
        show_banner()
        if active_user is None or add_user:
            number, refresh_token = login_prompt(AuthInstance.api_key)
            if not refresh_token:
                console.print("Gagal menambah akun. Silahkan coba lagi.", style="bold red")
                pause()
                continue
            AuthInstance.add_refresh_token(str(number), refresh_token)
            AuthInstance.load_tokens()
            users = AuthInstance.refresh_tokens
            add_user = False
            active_user = AuthInstance.get_active_user()
            continue

        if not users:
            render_table("AKUN TERSIMPAN", [["-", "Tidak ada akun tersimpan"]],
                         headers=["No", "Nomor HP"], aligns=["center", "left"], style="red")
        else:
            table_data = []
            for idx, user in enumerate(users):
                is_active = active_user and str(user["number"]) == str(active_user["number"])
                marker = " (Aktif)" if is_active else ""
                table_data.append([str(idx + 1), str(user["number"]) + marker])
            render_table("AKUN TERSIMPAN", table_data,
                         headers=["No", "Nomor HP"], aligns=["center", "left"], style="red")

        commands = [
            ["0", "➕ Tambah Akun"],
            ["00", "↩️ Kembali ke menu utama"],
            ["99", "❌ Hapus Akun aktif"],
        ]
        render_table("COMMANDS", commands, headers=["No", "Keterangan"], aligns=["center", "left"], style="blue")

        input_str = input("Pilihan: ")
        if input_str == "00":
            return str(active_user["number"]) if active_user else None
        elif input_str == "0":
            add_user = True
            continue
        elif input_str == "99":
            if not active_user:
                console.print("Tidak ada akun aktif untuk dihapus.", style="bold red")
                pause()
                continue
            confirm = input(f"Yakin ingin menghapus akun {active_user['number']}? (y/n): ")
            if confirm.lower() == "y":
                AuthInstance.remove_refresh_token(str(active_user["number"]))
                users = AuthInstance.refresh_tokens
                active_user = AuthInstance.get_active_user()
                console.print("Akun berhasil dihapus.", style="bold green")
                pause()
            else:
                console.print("Penghapusan akun dibatalkan.", style="bold yellow")
                pause()
            continue
        elif input_str.isdigit() and 1 <= int(input_str) <= len(users):
            selected_user = users[int(input_str) - 1]
            return str(selected_user["number"])
        else:
            console.print("Input tidak valid. Silahkan coba lagi.", style="bold red")
            pause()

def login_prompt(api_key: str):
    clear_screen()
    show_banner()
    render_table("LOGIN KE MYXL", [["-", ""]], style="blue")
    phone_number = input("Masukan nomor XL Prabayar (Contoh 6281234567890): ")

    if not phone_number.startswith("628") or not (10 <= len(phone_number) <= 14):
        console.print("Nomor tidak valid.", style="bold red")
        return None, None

    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            return None, None
        console.print("OTP Berhasil dikirim ke nomor Anda.", style="bold green")
        otp = input("Masukkan OTP yang telah dikirim: ")
        if not otp.isdigit() or len(otp) != 6:
            console.print("OTP tidak valid.", style="bold red")
            pause()
            return None, None
        tokens = submit_otp(api_key, phone_number, otp)
        if not tokens:
            console.print("Gagal login. Periksa OTP dan coba lagi.", style="bold red")
            pause()
            return None, None
        console.print("Berhasil login!", style="bold green")
        return phone_number, tokens["refresh_token"]
    except Exception:
        return None, None
def show_package_menu(packages):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        render_table("ERROR", [["No active user tokens found"]], style="red")
        pause()
        return None

    while True:
        clear_screen()
        show_banner()

        # Data tabel: No, Nama Paket, Harga
        table_data = [
            [pkg["number"], f"📦 {pkg['name']}", f"Rp {pkg['price']}"]
            for pkg in packages
        ]

        # Tabel paket tersedia
        render_table(
            "PAKET TERSEDIA",
            table_data,
            headers=["No", "Nama Paket", "Harga"],
            aligns=["center", "left", "left"],
            style="green"
        )

        # Tabel kembali
        render_table(
            "KEMBALI",
            [["99 ↩️ Kembali ke menu utama"]],
            headers=["Keterangan"],
            aligns=["left"],
            style="yellow"
        )

        pkg_choice = input("Pilih paket (nomor): ").strip()
        if pkg_choice == "99":
            return None

        if not pkg_choice.isdigit():
            console.print("Input tidak valid. Silakan masukan nomor yang benar.", style="bold red")
            pause()
            continue

        selected_pkg = next((p for p in packages if p["number"] == int(pkg_choice)), None)
        if not selected_pkg:
            console.print("Paket tidak ditemukan. Silakan masukan nomor yang benar.", style="bold red")
            pause()
            continue

        is_done = show_package_details(api_key, tokens, selected_pkg["code"])
        if is_done:
            return None

def show_settings_menu():
    """
    Menu Pengaturan: ganti banner, reset banner, dsb.
    """
    global ascii_art  # ← harus di awal fungsi
    in_settings_menu = True
    DEFAULT_BANNER_URL = "https://d17e22l2uh4h4n.cloudfront.net/corpweb/pub-xlaxiata/2019-03/xl-logo.png"

    while in_settings_menu:
        clear_screen()
        show_banner()

        # Tabel opsi pengaturan
        settings_options = [
            ["1", "🖼 Ganti Banner"],
            ["2", "⚡ Reset Banner ke Default"],
        ]
        render_table(
            "⚙️ PENGATURAN",
            settings_options,
            headers=["No", "Pilihan"],
            aligns=["center", "left"],
            style="cyan"
        )

        # Tabel command
        commands = [
            ["00", "↩️ Kembali ke menu utama"],
        ]
        render_table(
            "COMMANDS",
            commands,
            headers=["No", "Keterangan"],
            aligns=["center", "left"],
            style="yellow"
        )

        choice = input("Pilih opsi pengaturan: ").strip()

        if choice == "00":
            in_settings_menu = False
            return None

        elif choice == "1":
            new_url = input("Masukkan URL banner baru: ").strip()
            if not new_url:
                console.print("URL tidak boleh kosong.", style="bold red")
                pause()
                continue
            try:
                ascii_art = banner.load(new_url, globals())
                save_banner_url(new_url)  # simpan ke config.json
                console.print("Banner berhasil diganti dan disimpan!", style="bold green")
            except Exception as e:
                console.print(f"Gagal mengganti banner: {e}", style="bold red")
            pause()
            continue

        elif choice == "2":
            try:
                ascii_art = banner.load(DEFAULT_BANNER_URL, globals())
                save_banner_url(DEFAULT_BANNER_URL)  # reset config.json
                console.print("Banner berhasil di-reset ke default.", style="bold green")
            except Exception as e:
                console.print(f"Gagal reset banner: {e}", style="bold red")
            pause()
            continue

        else:
            console.print("Input tidak valid. Silahkan coba lagi.", style="bold red")
            pause()
            continue
