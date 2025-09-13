from dotenv import load_dotenv
load_dotenv()

import sys
import os
import json
import shutil

from ui import *
from api_request import *
from paket_xut import get_package_xut
from my_package import fetch_my_packages
from paket_custom_family import get_packages_by_family
from auth_helper import AuthInstance

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()


# -----------------------------
# Utils
# -----------------------------
def get_terminal_width(default=90):
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return default


def render_rich_table(title, rows, headers=None, col_aligns=None, style="cyan", show_header=True):
    """
    Render tabel menggunakan Rich dengan warna dan opsional header.
    """
    table = Table(
        title=f"[bold {style}]{title}[/bold {style}]",
        show_lines=True,
        expand=True,
        show_header=show_header,
        border_style=style
    )

    n_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
    for i in range(n_cols):
        justify = col_aligns[i] if col_aligns and i < len(col_aligns) else "left"
        col_title = headers[i] if headers and i < len(headers) else f"Col{i+1}"
        table.add_column(col_title, justify=justify, style=style)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def render_commands_table(rows, title="COMMANDS", style="magenta"):
    """
    Tabel commands khusus Rich tanpa header
    """
    render_rich_table(title, rows, headers=["No", "Description"], col_aligns=["center", "left"], style=style, show_header=False)


# -----------------------------
# Auth / Login
# -----------------------------
def login_flow():
    selected_user_number = show_account_menu()
    if selected_user_number:
        AuthInstance.set_active_user(selected_user_number)
    else:
        console.print(Panel("No user selected or failed to load user.", style="red"))


# -----------------------------
# Family Code Management
# -----------------------------
def save_family_codes(family_list):
    with open("family_code.json", "w", encoding="utf-8") as f:
        json.dump(family_list, f, indent=4)


def add_family_code(family_list, type_="normal"):
    name = Prompt.ask(f"Masukkan nama paket baru ({type_.capitalize()})").strip()
    code = Prompt.ask("Masukkan code baru").strip()
    if not name or not code:
        console.print("[red]Nama atau code tidak boleh kosong[/red]")
    elif any(fc['code'] == code for fc in family_list):
        console.print(f"[yellow]Code {code} sudah ada[/yellow]")
    else:
        family_list.append({"name": name, "code": code, "type": type_})
        save_family_codes(family_list)
        console.print(f"[green]{type_.capitalize()} Family code berhasil ditambahkan[/green]")
    pause()


def delete_family_code(family_list, number_mapping):
    if not number_mapping:
        console.print("[red]Daftar family code kosong[/red]")
        pause()
        return

    del_idx = Prompt.ask("Masukkan nomor family code yang ingin dihapus").strip()
    selected_family = number_mapping.get(del_idx)

    if selected_family:
        confirm = Prompt.ask(f"Apakah Anda yakin ingin menghapus '{selected_family.get('name')}'? (y/n)").strip().lower()
        if confirm == 'y':
            family_list.remove(selected_family)
            save_family_codes(family_list)
            console.print(f"[green]Family code '{selected_family.get('name')}' berhasil dihapus[/green]")
        else:
            console.print("[yellow]Penghapusan dibatalkan[/yellow]")
    else:
        console.print("[red]Nomor yang dimasukkan tidak ada[/red]")
    pause()


def family_code_menu():
    json_file = "family_code.json"
    if not os.path.exists(json_file):
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

    with open(json_file, "r", encoding="utf-8") as f:
        family_list = json.load(f)

    while True:
        clear_screen()

        normal_codes = [fc for fc in family_list if fc.get("type") == "normal"]
        enterprise_codes = [fc for fc in family_list if fc.get("type") == "enterprise"]

        def build_table(codes, start_index=1):
            return [[idx, fc.get("name", ""), fc.get("code", "")] for idx, fc in enumerate(codes, start=start_index)]

        # Render NORMAL table
        normal_table = build_table(normal_codes, 1) if normal_codes else [[ "-", "-", "Tidak ada normal family code"]]
        render_rich_table("NORMAL FAMILY CODES", normal_table, headers=["No","Name","Code"], col_aligns=["center","left","left"], style="blue")

        # Render ENTERPRISE table
        enterprise_start_index = len(normal_codes)+1
        enterprise_table = build_table(enterprise_codes, enterprise_start_index) if enterprise_codes else [["-","-","Tidak ada enterprise family code"]]
        render_rich_table("ENTERPRISE FAMILY CODES", enterprise_table, headers=["No","Name","Code"], col_aligns=["center","left","left"], style="cyan")

        # Global mapping nomor -> family code
        number_mapping = {str(i): fc for i, fc in enumerate(normal_codes + enterprise_codes, start=1)}

        commands = [
        ["0", "➕ Tambah Family Code (Normal)"],
        ["00", "🏢 Tambah Family Code (Enterprise)"],
        ["-", "🗑️ Hapus Family Code"],
        ["99", "🔙 Kembali"]
        ]
        render_commands_table(commands, style="magenta")


        selection = Prompt.ask("\nPilihan").strip().upper()
        if selection == "99":
            break
        elif selection == "0":
            add_family_code(family_list,"normal")
        elif selection == "00":
            add_family_code(family_list,"enterprise")
        elif selection == "-":
            delete_family_code(family_list, number_mapping)
        elif selection in number_mapping:
            fc = number_mapping[selection]
            get_packages_by_family(fc.get("code"), is_enterprise=(fc.get("type")=="enterprise"))
            pause()
        else:
            console.print("[red]Pilihan tidak valid atau nomor di luar jangkauan[/red]")
            pause()


# -----------------------------
# Main Menu
# -----------------------------
def main():
    while True:
        active_user = AuthInstance.get_active_user()
        if active_user: None
            balance = os_getenv(AuthInstance.api_key, active_user["tokens"]["id_token"]) or {}
            balance_remaining = os_getenv("remaining",0)
            balance_expired_at = os_getenv("expired_at","N/A")

            quota = os_getenv(AuthInstance.api_key, active_user["tokens"]["id_token"]) or {}
            remaining = os_getenv("remaining",0)
            total = os_getenv("total",0)
            has_unlimited = os_getenv("has_unlimited",False)

            remaining_gb = remaining/1e9
            total_gb = total/1e9
            display_quota = f"{remaining_gb:.2f}/{total_gb:.2f} GB Unlimited" if has_unlimited else f"{remaining_gb:.2f}/{total_gb:.2f} GB"

            show_main_menu(active_user["number"], balance_remaining, balance_expired_at, display_quota=display_quota)

            choice = Prompt.ask("Pilih menu").strip()
            if choice=="1":
                login_flow()
            elif choice=="2":
                fetch_my_packages()
            elif choice=="3":
                packages = get_package_xut()
                show_package_menu(packages)
            elif choice=="4":
                family_code = Prompt.ask("Enter family code (or '99' to cancel)").strip()
                if family_code!="99":
                    get_packages_by_family(family_code)
            elif choice=="5":
                family_code = Prompt.ask("Enter family code (or '99' to cancel)").strip()
                if family_code!="99":
                    get_packages_by_family(family_code,is_enterprise=True)
            elif choice=="6":
                family_code_menu()
            elif choice == "7":  
                show_bookmark_menu()
            elif choice == "8":
                show_settings_menu()
                continue
            elif choice=="99":
                console.print("[green]Exiting the application.[/green]")
                return
            else:
                console.print("[red]Pilihan tidak valid. Silakan coba lagi.[/red]")
                pause()
        else:
            login_flow()


if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Exiting the application.[/red]")
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")
