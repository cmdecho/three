# bookmark.py
import os
import json
import shutil
import io
import sys
import banner
import textwrap
from typing import List, Dict
from auth_helper import AuthInstance
from package import show_package_details

from util import clear_screen, pause
from paket_xut import get_family  # atau sesuaikan import get_family sesuai struktur proyek
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

console = Console()

def show_banner():
    term_width = shutil.get_terminal_size().columns
    buffer = io.StringIO()
    sys.stdout = buffer
    ascii_art.to_terminal(columns=60)
    sys.stdout = sys.__stdout__
    banner_lines = [line.center(term_width) for line in buffer.getvalue().splitlines()]
    console.print("\n".join(banner_lines), style="bold blue")

# ======================
# Singleton Bookmark
# ======================
class Bookmark:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.packages: List[Dict] = []
            self.filepath = "bookmark.json"

            if os.path.exists(self.filepath):
                self.load_bookmark()
            else:
                self._save([])  # create empty file

            self._initialized = True

    def _save(self, data: List[Dict]):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _ensure_schema(self):
        updated = False
        for p in self.packages:
            if "family_name" not in p:
                p["family_name"] = ""
                updated = True
        if updated:
            self.save_bookmark()

    def load_bookmark(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.packages = json.load(f)
        self._ensure_schema()

    def save_bookmark(self):
        self._save(self.packages)

    def add_bookmark(
        self,
        family_code: str,
        family_name: str,
        is_enterprise: bool,
        variant_name: str,
        option_name: str,
    ) -> bool:
        key = (family_code, variant_name, option_name)
        if any(
            (p["family_code"], p["variant_name"], p["option_name"]) == key
            for p in self.packages
        ):
            console.print(Panel("Bookmark already exists.", style="yellow"))
            return False

        self.packages.append(
            {
                "family_name": family_name,
                "family_code": family_code,
                "is_enterprise": is_enterprise,
                "variant_name": variant_name,
                "option_name": option_name,
            }
        )
        self.save_bookmark()
        console.print(Panel("Bookmark added.", style="green"))
        return True

    def remove_bookmark(
        self,
        family_code: str,
        is_enterprise: bool,
        variant_name: str,
        option_name: str,
    ) -> bool:
        for i, p in enumerate(self.packages):
            if (
                p["family_code"] == family_code
                and p["is_enterprise"] == is_enterprise
                and p["variant_name"] == variant_name
                and p["option_name"] == option_name
            ):
                del self.packages[i]
                self.save_bookmark()
                console.print(Panel("Bookmark removed.", style="green"))
                return True
        console.print(Panel("Bookmark not found.", style="red"))
        return False

    def get_bookmarks(self) -> List[Dict]:
        return self.packages.copy()


BookmarkInstance = Bookmark()

# ======================
# Menu Bookmark
# ======================

def show_bookmark_menu():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

    in_bookmark_menu = True
    while in_bookmark_menu:
        clear_screen()

        bookmarks = BookmarkInstance.get_bookmarks()

        if not bookmarks:
            console.print(
                Panel("Tidak ada bookmark tersimpan.", style="red", expand=True, padding=(1, 2))
            )
            pause()
            return None

        # ======================
        # Tabel Bookmark (judul jadi bagian tabel)
        # ======================
        bookmark_table = Table(
            title="[bold cyan]📚 Bookmark[/bold cyan]",
            title_justify="center",
            show_header=True,
            header_style="bold white on blue",
            expand=True,
            box=box.ROUNDED,
        )
        bookmark_table.add_column("No", justify="center", style="bold cyan", width=6)
        bookmark_table.add_column("📦 Paket", style="green")
        bookmark_table.add_column("📂 Family", style="yellow")

        for idx, bm in enumerate(bookmarks, start=1):
            bookmark_table.add_row(
                str(idx),
                f"{bm['variant_name']} - {bm['option_name']}",
                bm.get("family_name", "-")
            )

        console.print(bookmark_table)

        # ======================
        # Tabel Command
        # ======================
        command_table = Table(
            title="[bold cyan]⚙ Command[/bold cyan]",
            title_justify="center",
            show_header=True,
            header_style="bold white on blue",
            expand=True,
            box=box.ROUNDED,
        )
        command_table.add_column("No", justify="center", style="bold cyan", width=6)
        command_table.add_column("Perintah", style="bold")

        command_table.add_row("0", "🔙 Kembali ke menu utama")
        command_table.add_row("00", "❌ Hapus Bookmark")

        console.print(command_table)

        # ======================
        # Input
        # ======================
        choice = Prompt.ask("\nPilih bookmark / command").strip().upper()

        if choice == "0":
            in_bookmark_menu = False
            return None
        elif choice == "00":
            del_choice = Prompt.ask("Masukkan nomor bookmark yang ingin dihapus").strip()
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(bookmarks):
                del_bm = bookmarks[int(del_choice) - 1]
                BookmarkInstance.remove_bookmark(
                    del_bm["family_code"],
                    del_bm["is_enterprise"],
                    del_bm["variant_name"],
                    del_bm["option_name"]
                )
            else:
                console.print(Panel("Input tidak valid.", style="red"))
            pause()
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(bookmarks):
            selected_bm = bookmarks[int(choice) - 1]
            family_code = selected_bm["family_code"]
            is_enterprise = selected_bm["is_enterprise"]

            family_data = get_family(api_key, tokens, family_code, is_enterprise)
            if not family_data:
                console.print(Panel("Gagal mengambil data family.", style="red"))
                pause()
                continue

            # Cari kode opsi paket
            option_code = None
            for variant in family_data["package_variants"]:
                if variant["name"] == selected_bm["variant_name"]:
                    for option in variant["package_options"]:
                        if option["name"] == selected_bm["option_name"]:
                            option_code = option["package_option_code"]
                            break
            if option_code:
                show_package_details(api_key, tokens, option_code, is_enterprise)
            else:
                console.print(
                    Panel(
                        f"❌ Paket [{selected_bm['variant_name']} - {selected_bm['option_name']}] "
                        "tidak ditemukan di family data.",
                        style="red"
                    )
                )
                pause()
