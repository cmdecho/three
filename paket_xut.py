import json
import shutil
from api_request import get_family
from auth_helper import AuthInstance
from util import pause, clear_screen
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

PACKAGE_FAMILY_CODE = "08a3b1e6-8e78-4e45-a540-b40f06871cfe"
console = Console()


def render_rich_table(title, rows, headers=None, col_aligns=None):
    """Render table menggunakan Rich"""
    table = Table(title=title, show_lines=True, expand=True)

    n_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
    for i in range(n_cols):
        justify = col_aligns[i] if col_aligns and i < len(col_aligns) else "left"
        col_title = headers[i] if headers and i < len(headers) else f"Col{i+1}"
        table.add_column(col_title, justify=justify)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def get_package_xut():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        console.print(Panel("No active user tokens found.", title="ERROR", style="red"))
        pause()
        return []

    packages = []
    data = get_family(api_key, tokens, PACKAGE_FAMILY_CODE)

    if not data:
        console.print(Panel("Failed to load package family data.", title="ERROR", style="red"))
        pause()
        return []

    clear_screen()

    family_name = data['package_family']["name"]
    console.print(Panel(f"FAMILY NAME: {family_name}", style="cyan"))

    start_number = 1
    for variant_number, variant in enumerate(data["package_variants"], start=1):
        variant_name = variant["name"]
        console.print(Panel(f"Variant {variant_number}: {variant_name}", style="magenta"))

        variant_table_rows = []
        for option in variant["package_options"]:
            friendly_name = option["name"]
            if friendly_name.lower() == "vidio":
                friendly_name = "Unli Turbo Vidio"
            if friendly_name.lower() == "iflix":
                friendly_name = "Unli Turbo Iflix"

            variant_table_rows.append([start_number, friendly_name, f"Rp {option['price']:,}"])

            packages.append({
                "number": start_number,
                "name": friendly_name,
                "price": option["price"],
                "code": option["package_option_code"]
            })
            start_number += 1

        if variant_table_rows:
            render_rich_table(
                f"PAKET VARIANT {variant_number}",
                variant_table_rows,
                headers=["No", "Nama Paket", "Harga"],
                col_aligns=["center", "left", "right"]
            )

    return packages
