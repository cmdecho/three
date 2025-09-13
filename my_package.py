from api_request import get_package, send_api_request
from auth_helper import AuthInstance
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from ui import show_package_details
from util import clear_screen, pause

console = Console()

def fetch_my_packages():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        console.print(Panel("[red]No active user tokens found[/red]", title="ERROR"))
        pause()
        return None

    id_token = tokens.get("id_token")
    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}

    console.print(Panel("Fetching my packages...", title="INFO", style="cyan"))
    res = send_api_request(api_key, path, payload, id_token, "POST")

    if res.get("status") != "SUCCESS":
        console.print(Panel(f"Failed to fetch packages: {res}", title="ERROR", style="red"))
        pause()
        return None

    quotas = res["data"]["quotas"]
    clear_screen()

    my_packages = []
    num = 1

    # Tampilkan setiap paket sebagai panel vertikal
    for quota in quotas:
        quota_code = quota.get("quota_code", "N/A")
        name = quota.get("name", "N/A")
        expired_ts = quota.get("active_date", 0)
        expired_dt = datetime.fromtimestamp(expired_ts).strftime("%Y-%m-%d %H:%M:%S") if expired_ts else "N/A"

        benefits = quota.get("benefits", [])
        if benefits:
            main_benefit = benefits[0]
            remaining = main_benefit.get("remaining", 0)
            total = main_benefit.get("total", 0)
            is_unlimited = main_benefit.get("is_unlimited", False)
        else:
            remaining = total = 0
            is_unlimited = False

        remaining_gb = remaining / 1e9
        total_gb = total / 1e9
        display_quota = f"{remaining_gb:.2f}/{total_gb:.2f} GB"
        if is_unlimited:
            display_quota += " Unlimited"

        # Ambil family_code jika tersedia
        family_code = "N/A"
        package_details = get_package(api_key, tokens, quota_code)
        if package_details:
            family_code = package_details.get("package_family", {}).get("package_family_code", "N/A")

        # Buat panel vertikal
        panel_content = f"[cyan]No:[/cyan] {num}\n"
        panel_content += f"[green]Name:[/green] {name}\n"
        panel_content += f"[yellow]Quota:[/yellow] {display_quota}\n"
        panel_content += f"[magenta]Expired At:[/magenta] {expired_dt}\n"
        panel_content += f"[blue]Quota Code:[/blue] {quota_code}\n"
        panel_content += f"[white]Family Code:[/white] {family_code}"

        console.print(Panel(panel_content, expand=True, border_style="bright_blue"))

        my_packages.append({"number": num, "quota_code": quota_code})
        num += 1

    # Interaksi memilih paket
    while True:
        choice = Prompt.ask("[cyan]Input package number to rebuy / view details, or '00' to back[/cyan]", default="00")
        if choice == "00":
            return None

        selected_pkg = next((pkg for pkg in my_packages if str(pkg["number"]) == choice), None)
        if not selected_pkg:
            console.print(Panel(f"[red]Package number {choice} not found. Try again.[/red]", title="ERROR"))
            continue

        # Tampilkan detail paket interaktif
        is_done = show_package_details(api_key, tokens, selected_pkg["quota_code"])
        if is_done:
            break

    pause()
