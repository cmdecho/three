import json
from rich.console import Console
from rich.panel import Panel

from table import render_table
from util import clear_screen, pause, display_html, format_unit
from api_request import get_package, get_addons, purchase_package
from purchase_api import show_multipayment, show_qris_payment, settlement_bounty

console = Console()


def show_package_details(api_key, tokens, package_option_code, is_enterprise=False):
    """
    Tampilkan detail paket, addons, syarat & ketentuan, serta menu pembayaran.
    Digunakan baik dari ui.py maupun bookmark.py
    """
    while True:   # loop utama
        clear_screen()

        # Ambil data paket
        package = get_package(api_key, tokens, package_option_code)
        if not package:
            console.print("Failed to load package details.", style="bold red")
            pause()
            return None   # jangan sys.exit

        # Info dasar
        family_name = package.get("package_family", {}).get("name", "")
        variant_name = package.get("package_detail_variant", {}).get("name", "")
        option_name = package.get("package_option", {}).get("name", "")

        title = f"{family_name} {variant_name} {option_name}".strip()
        price = package["package_option"]["price"]
        validity = package["package_option"]["validity"]
        benefits = package["package_option"]["benefits"]
        detail = display_html(package["package_option"]["tnc"])

        # DETAIL PAKET
        package_table = [
            ["📦 Nama Paket", title],
            ["💰 Harga", f"Rp {price}"],
            ["⏳ Masa Aktif", validity]
        ]
        render_table("DETAIL PAKET", package_table, headers=None,
                     aligns=["left", "left"], style="cyan")

        # BENEFITS
        if benefits:
            benefit_table = [[f"✅ {b['name']}", format_unit(b["total"], b["name"])]
                             for b in benefits]
            render_table("BENEFITS", benefit_table, headers=None,
                         aligns=["left", "left"], style="magenta")

        # ADDONS
        try:
            addons = get_addons(api_key, tokens, package_option_code)
            addons_list = []
            if isinstance(addons, dict):
                addons_list = addons.get("addons") or addons.get("data") or []
            elif isinstance(addons, list):
                addons_list = addons

            if addons_list:
                rows = []
                for addon in addons_list:
                    if isinstance(addon, dict):
                        name = addon.get("name", "-")
                        info = addon.get("information", "")
                        validity = addon.get("validity", "-")
                        price = f"Rp {addon.get('price', 0)}"
                        rows.append([name, info, validity, price])
                    else:
                        rows.append([str(addon), "-", "-", "-"])
                render_table("ADDONS", rows,
                             headers=["Nama", "Keterangan", "Masa Aktif", "Harga"],
                             aligns=["left", "left", "center", "right"],
                             style="yellow")
            else:
                json_str = json.dumps(addons, indent=2, ensure_ascii=False)
                render_table("ADDONS", [[json_str]],
                             headers=None, aligns=["left"], style="yellow")
        except Exception as e:
            console.print(f"Fetching addons failed: {e}", style="bold red")

        # SYARAT & KETENTUAN
        if detail:
            detail_clean = "\n".join([line.strip()
                                     for line in detail.splitlines() if line.strip()])
            render_table("SYARAT & KETENTUAN", [[detail_clean]],
                         headers=None, aligns=["left"], style="yellow")
        else:
            console.print("Tidak ada syarat & ketentuan.", style="bold yellow")

        # MENU PEMBAYARAN
        payment_for = package["package_family"]["payment_for"]
        payment_methods = [
            ["1", "💰 Beli dengan Pulsa"],
            ["2", "💳 Beli dengan E-Wallet"],
            ["3", "🔲 Bayar dengan QRIS"],
            ["0", "📑 Bookmark Paket"],
            ["00", "🔙 Kembali ke Menu"],
        ]
        if payment_for == "REDEEM_VOUCHER":
            payment_methods.append(["4", "🎁 Ambil sebagai bonus (jika tersedia)"])

        render_table("METODE PEMBAYARAN", payment_methods,
                     headers=None, aligns=["center", "left"], style="blue")

        # Input user
        choice = input("Pilih metode pembayaran: ").strip()
        token_confirmation = package["token_confirmation"]
        ts_to_sign = package["timestamp"]
        item_name = f"{variant_name} {option_name}".strip()

        try:
            if choice == "1":
                purchase_package(api_key, tokens, package_option_code)
                console.print("Silahkan cek hasil pembelian di aplikasi MyXL.",
                              style="bold green")
                pause()
                return True

            elif choice == "2":
                show_multipayment(api_key, tokens, package_option_code,
                                  token_confirmation, price, item_name)
                console.print("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL.",
                              style="bold green")
                pause()
                return True

            elif choice == "3":
                try:
                    show_qris_payment(api_key, tokens, package_option_code,
                                      token_confirmation, price, item_name)
                    console.print("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL.",
                                  style="bold green")
                except Exception as e:
                    console.print(f"QRIS payment failed: {e}", style="bold red")
                pause()
                return True

            elif choice == "4" and payment_for == "REDEEM_VOUCHER":
                try:
                    settlement_bounty(api_key=api_key, tokens=tokens,
                                      token_confirmation=token_confirmation,
                                      ts_to_sign=ts_to_sign,
                                      payment_target=package_option_code,
                                      price=price, item_name=item_name)
                    console.print("Bonus berhasil diambil.", style="bold green")
                except Exception as e:
                    console.print(f"Redeem voucher failed: {e}", style="bold red")
                pause()
                return True

            elif choice == "0":
                # Import di dalam untuk hindari circular import
                from bookmark import BookmarkInstance
                success = BookmarkInstance.add_bookmark(
                    family_code=package.get("package_family", {}).get(
                        "package_family_code", ""),
                    family_name=family_name,
                    is_enterprise=is_enterprise,
                    variant_name=variant_name,
                    option_name=option_name
                )
                if success:
                    console.print("Paket berhasil ditambahkan ke bookmark.",
                                  style="bold green")
                else:
                    console.print("Paket sudah ada di bookmark.",
                                  style="bold yellow")
                pause()
                continue

            elif choice == "00":
                return None

            else:
                console.print("Purchase cancelled.", style="bold yellow")
                pause()
                continue

        except Exception as e:
            console.print(f"An unexpected error occurred during purchase: {e}",
                          style="bold red")
            pause()
            continue
