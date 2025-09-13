# table.py
from rich.console import Console
from rich.table import Table
import shutil

console = Console()

def get_terminal_width(default=80):
    """Dapatkan lebar terminal"""
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default

def render_table(title, data, headers=None, show_headers=True, aligns=None, style="cyan"):
    """
    Render tabel menggunakan Rich
    - title: judul tabel
    - data: list of list (rows)
    - headers: list kolom atau None
    - show_headers: tampilkan header atau tidak
    - aligns: list alignment per kolom
    - style: warna judul tabel
    """

    # Buat tabel
    table = Table(
        title=f"[bold {style}]{title}[/bold {style}]" if title else None,
        title_justify="center",
        show_header=False if headers is None else show_headers,
        header_style="bold",
        expand=True  # 🔥 Biar full ke layar
    )

    # Kolom
    if headers:
        for i, header in enumerate(headers):
            justify = aligns[i] if aligns and i < len(aligns) else "left"
            table.add_column(header, justify=justify)
    else:
        col_count = max(len(row) for row in data) if data else 0
        for i in range(col_count):
            justify = aligns[i] if aligns and i < len(aligns) else "left"
            table.add_column("", justify=justify)  # 🔥 header kosong

    # Isi baris
    for row in data:
        row_str = [str(c) if c is not None else "" for c in row]
        table.add_row(*row_str)

    console.print(table)
