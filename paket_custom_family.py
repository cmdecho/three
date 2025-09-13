import json
import shutil
from api_request import send_api_request, get_family
from auth_helper import AuthInstance
from ui import show_package_details
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.align import Align
from util import clear_screen, pause


console = Console()

# ======================
# Utils Family Code
# ======================
def load_family_codes():
    try:
        with open("family_code.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_family_codes(family_list):
    with open("family_code.json", "w", encoding="utf-8") as f:
        json.dump(family_list, f, indent=4)

def add_family_code_auto(family_name: str, code: str, type_: str = "normal"):
    family_list = load_family_codes()
    if any(fc['code'] == code for fc in family_list):
        console.print(Panel(f"Family code '{code}' sudah ada di family_code.json.", title="INFO", style="yellow"))
    else:
        family_list.append({"name": family_name, "code": code, "type": type_})
        save_family_codes(family_list)
        console.print(Panel(f"{type_.capitalize()} Family code '{family_name}' berhasil disimpan dengan code: {code}", title="SUCCESS", style="green"))
    pause()


# ======================
# Rich Table Renderer
# ======================
def render_rich_table(title, rows, headers=None, col_aligns=None,show_header=None):
    table = Table(title=title, show_lines=True, expand=True, show_header=False)
    n_cols = len(headers) if headers else (len(rows[0]) if rows else 1)

    for i in range(n_cols):
        justify = col_aligns[i] if col_aligns and i < len(col_aligns) else "left"
        col_title = headers[i] if headers and i < len(headers) else f"Col{i+1}"
        table.add_column(col_title, justify=justify)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


# ======================
# Menu Family Package
# ======================
def get_packages_by_family(family_code: str, is_enterprise: bool = False):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        console.print(Panel("No active user tokens found.", title="ERROR", style="red"))
        pause()
        return None

    type_ = "enterprise" if is_enterprise else "normal"
    packages = []

    data = get_family(api_key, tokens, family_code, is_enterprise)
    if not data:
        console.print(Panel("Failed to load family data.", title="ERROR", style="red"))
        pause()
        return None

    in_package_menu = True
    while in_package_menu:
        clear_screen()
        family_name = data['package_family']["name"]
        console.print(Panel(Align.center(f"📁 Family Name [bold]{family_name}[/bold]"), style="cyan"))


        package_variants = data["package_variants"]
        option_number = 1

        for variant_number, variant in enumerate(package_variants, start=1):
            variant_name = variant["name"]
            console.print(Panel(Align.center(f"Variant [bold]{variant_number}: {variant_name}[/bold]"), style="magenta"))

            variant_table_rows = []
            for option in variant["package_options"]:
                option_name = option["name"]
                price = option["price"]
                code = option["package_option_code"]

                variant_table_rows.append([option_number, option_name, f"Rp {price:,}"])
                packages.append({
                    "number": option_number,
                    "name": option_name,
                    "price": price,
                    "code": code
                })
                option_number += 1

            if variant_table_rows:
                render_rich_table("PAKET", variant_table_rows, headers=["No", "Nama Paket", "Harga"], col_aligns=["center", "left", "right"])

        # Commands menu
        commands = [
        ["A", "💾 Simpan Family Code"],
        ["00", "🔙 Kembali ke menu sebelumnya"]
        ]
        render_rich_table("COMMANDS", commands, headers=["Input", "Deskripsi"], col_aligns=["center", "left"], show_header=False)

        pkg_choice = Prompt.ask("[cyan]Pilihan[/cyan]").strip().upper()
        if pkg_choice == "00":
            in_package_menu = False
            return None
        elif pkg_choice == "A":
            confirm = Prompt.ask(f"Mau simpan Family Code ({family_name}) ? (y/n)").strip().lower()
            if confirm == "y":
                add_family_code_auto(family_name, family_code, type_)
        elif pkg_choice.isdigit():
            selected_pkg = next((p for p in packages if p["number"] == int(pkg_choice)), None)
            if not selected_pkg:
                console.print(Panel("Paket tidak ditemukan. Silakan masukkan nomor yang benar.", style="red"))
                pause()
                continue
            is_done = show_package_details(api_key, tokens, selected_pkg["code"])
            if is_done:
                in_package_menu = False
                return None
        else:
            console.print(Panel("Input tidak valid. Silakan masukkan nomor yang benar.", style="red"))
            pause()

    return packages
