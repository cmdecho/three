from datetime import datetime, timezone
import uuid, json, time, base64
import requests
import qrcode
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from crypto_helper import API_KEY, encryptsign_xdata, decrypt_xdata, get_x_signature_payment, get_x_signature_bounty, java_like_timestamp
from api_request import send_api_request

BASE_API_URL = "https://api.myxl.xlaxiata.co.id"
UA = "myXL / 8.6.0(1179); com.android.vending; (oppo; CPH1937; SDK 30; Android 11"

console = Console()

# ===========================
# Render Table dengan Rich
# ===========================
def render_table(title, data, headers=None):
    table = Table(title=title, show_header=bool(headers), header_style="bold magenta")
    if headers:
        for h in headers:
            table.add_column(str(h))
    for row in data:
        table.add_row(*[str(c) for c in row])
    console.print(table)

# ===========================
# Payment Methods
# ===========================
def get_payment_methods(api_key: str, tokens: dict, token_confirmation: str, payment_target: str):
    path = "payments/api/v8/payment-methods-option"
    payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation
    }

    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if res["status"] != "SUCCESS":
        console.print(f"[red]Failed to fetch payment methods.[/red] Error: {res}")
        return None
    return res["data"]

# ===========================
# Multipayment Settlement
# ===========================
def settlement_multipayment(api_key: str, tokens: dict, token_payment: str, ts_to_sign: int,
                            payment_target: str, price: int, amount_int: int,
                            wallet_number: str, item_name: str = "", payment_method: str = "DANA"):

    path = "payments/api/v8/settlement-multipayment/ewallet"
    payload = {
        "akrab": {"akrab_members": [], "akrab_parent_alias": "", "members": []},
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {"is_using_autobuy": False, "activated_autobuy_code": "", "autobuy_threshold_setting": {"label": "", "type": "", "value": 0}},
        "cc_payment_type": "",
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "wallet_number": wallet_number,
        "additional_data": {"original_price": price, "is_spend_limit_temporary": False, "migration_type": "", "spend_limit_amount": 0, "is_spend_limit": False, "tax": 0, "benefit_type": "", "quota_bonus": 0, "cashtag": "", "is_family_plan": False, "combo_details": [], "is_switch_plan": False, "discount_recurring": 0, "has_bonus": False, "discount_promo": 0},
        "total_amount": amount_int,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{"item_code": payment_target, "product_type": "", "item_price": price, "item_name": item_name, "tax": 0}],
        "verification_token": token_payment,
        "payment_method": payment_method,
        "timestamp": int(time.time())
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    body = encrypted_payload["encrypted_body"]
    xtime = int(body["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    payload["timestamp"] = ts_to_sign

    x_sig = get_x_signature_payment(api_key, tokens["access_token"], ts_to_sign, payment_target, token_payment, payment_method)
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    resp = requests.post(f"{BASE_API_URL}/{path}", headers=headers, data=json.dumps(body), timeout=30)
    try:
        return decrypt_xdata(api_key, resp.json())
    except Exception as e:
        console.print(f"[red][decrypt err][/red] {e}")
        return resp.text

# ===========================
# QRIS Settlement
# ===========================
def settlement_qris(api_key, tokens, token_payment, ts_to_sign, payment_target, price, item_name=""):
    amount_int = price
    path = "payments/api/v8/settlement-multipayment/qris"
    payload = {
        "access_token": tokens["access_token"],
        "items": [{"item_code": payment_target, "item_price": price, "item_name": item_name, "product_type": "", "tax": 0}],
        "total_amount": amount_int,
        "verification_token": token_payment,
        "payment_method": "QRIS",
        "timestamp": int(time.time())
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    body = encrypted_payload["encrypted_body"]
    xtime = int(body["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    x_sig = get_x_signature_payment(api_key, tokens["access_token"], ts_to_sign, payment_target, token_payment, "QRIS")
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    resp = requests.post(f"{BASE_API_URL}/{path}", headers=headers, data=json.dumps(body), timeout=30)
    try:
        decrypted = decrypt_xdata(api_key, resp.json())
        if decrypted["status"] != "SUCCESS":
            console.print(f"[red]Failed to initiate settlement.[/red] Error: {decrypted}")
            return None
        return decrypted["data"]["transaction_code"]
    except Exception as e:
        console.print(f"[red][decrypt err][/red] {e}")
        return resp.text

# ===========================
# Show QRIS Payment
# ===========================
def show_qris_payment(api_key, tokens, package_option_code, token_confirmation, price, item_name=""):
    console.print("[bold cyan]Fetching payment method details...[/bold cyan]")

    payment_data = get_payment_methods(api_key, tokens, token_confirmation, package_option_code)
    if not payment_data:
        return

    token_payment = payment_data.get("token_payment")
    ts_to_sign = payment_data.get("timestamp")

    transaction_id = settlement_qris(api_key, tokens, token_payment, ts_to_sign, package_option_code, price, item_name)
    if not transaction_id:
        console.print("[red]Failed to create QRIS transaction.[/red]")
        return

    # Ambil QRIS code
    path = "payments/api/v8/pending-detail"
    payload = {"transaction_id": transaction_id, "is_enterprise": False, "lang": "en", "status": ""}
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if res["status"] != "SUCCESS":
        console.print(f"[red]Failed to fetch QRIS code.[/red] Error: {res}")
        return
    qris_code = res["data"]["qr_code"]

    # Encode QRIS code menjadi URL
    qris_b64 = base64.urlsafe_b64encode(qris_code.encode()).decode()
    qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"

    # Render table info QRIS
    table_data = [
        ["Item", item_name or "-"],
        ["Price", f"Rp {price:,}"],
        ["Transaction ID", transaction_id],
        ["QRIS Link", qris_url]
    ]
    render_table("QRIS PAYMENT DETAILS", table_data, headers=["Field", "Value"])

    # QR Code
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=1)
    qr.add_data(qris_code)
    qr.make(fit=True)

    terminal_width = shutil.get_terminal_size((80, 20)).columns
    qr_lines = qr.get_matrix()
    for row in qr_lines:
        line = "".join(["██" if cell else "  " for cell in row])
        console.print(line.center(terminal_width))

    console.print(f"\n[bold green]Atau buka link berikut untuk melihat QRIS:[/bold green] {qris_url}\n")

# ===========================
# Bounty Settlement
# ===========================
def settlement_bounty(api_key, tokens, token_confirmation, ts_to_sign, payment_target, price, item_name=""):
    path = "api/v8/personalization/bounties-exchange"
    payload = {
        "access_token": tokens["access_token"],
        "token_confirmation": token_confirmation,
        "timestamp": ts_to_sign,
        "items": [{"item_code": payment_target, "item_price": price, "item_name": item_name, "product_type": "", "tax": 0}],
        "payment_method": "BALANCE"
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    body = encrypted_payload["encrypted_body"]
    xtime = int(body["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    x_sig = get_x_signature_bounty(api_key, tokens["access_token"], ts_to_sign, payment_target, token_confirmation)
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    resp = requests.post(f"{BASE_API_URL}/{path}", headers=headers, data=json.dumps(body), timeout=30)
    try:
        decrypted = decrypt_xdata(api_key, resp.json())
        if decrypted["status"] != "SUCCESS":
            console.print(f"[red]Failed to claim bounty.[/red] Error: {decrypted}")
            return None
        console.print(decrypted)
        return decrypted
    except Exception as e:
        console.print(f"[red][decrypt err][/red] {e}")
        return resp.text

def show_multipayment(api_key: str, tokens: dict, package_option_code: str, token_confirmation: str, price: int, item_name: str = ""):
    console.print("[bold cyan]Fetching available payment methods...[/bold cyan]")

    payment_methods_data = get_payment_methods(api_key, tokens, token_confirmation, package_option_code)
    if not payment_methods_data:
        return

    token_payment = payment_methods_data.get("token_payment")
    ts_to_sign = payment_methods_data.get("timestamp")

    # Optional overwrite amount
    amount_str = console.input(f"Total amount is [bold yellow]{price}[/bold yellow]. Enter value to overwrite or press Enter to use default: ")
    amount_int = price
    if amount_str.strip() != "":
        try:
            amount_int = int(amount_str.strip())
        except ValueError:
            console.print("[red]Invalid input, using original price.[/red]")

    # Payment options
    payment_options = [
        ["1", "DANA"],
        ["2", "ShopeePay"],
        ["3", "GoPay"],
        ["4", "OVO"]
    ]

    choosing = True
    while choosing:
        table = Table(title="METODE PEMBAYARAN", show_header=True, header_style="bold magenta")
        table.add_column("No", style="cyan", justify="center")
        table.add_column("Metode", style="green")
        for row in payment_options:
            table.add_row(*row)
        console.print(table)

        choice = console.input("Pilih metode pembayaran: ").strip()
        wallet_number = ""
        payment_method = ""

        if choice == "1":
            payment_method = "DANA"
            wallet_number = console.input("Masukkan nomor DANA (contoh: 08123456789): ").strip()
            if not wallet_number.startswith("08") or not wallet_number.isdigit() or len(wallet_number) < 10 or len(wallet_number) > 13:
                console.print("[red]Nomor DANA tidak valid.[/red]")
                continue
            choosing = False
        elif choice == "2":
            payment_method = "SHOPEEPAY"
            choosing = False
        elif choice == "3":
            payment_method = "GOPAY"
            choosing = False
        elif choice == "4":
            payment_method = "OVO"
            wallet_number = console.input("Masukkan nomor OVO (contoh: 08123456789): ").strip()
            if not wallet_number.startswith("08") or not wallet_number.isdigit() or len(wallet_number) < 10 or len(wallet_number) > 13:
                console.print("[red]Nomor OVO tidak valid.[/red]")
                continue
            choosing = False
        else:
            console.print("[red]Pilihan tidak valid.[/red]")

    console.print(f"[bold cyan]Initiating settlement with {payment_method}...[/bold cyan]")

    settlement_response = settlement_multipayment(
        api_key, tokens, token_payment, ts_to_sign,
        package_option_code, price, amount_int,
        wallet_number, item_name, payment_method
    )

    if not settlement_response or settlement_response.get("status") != "SUCCESS":
        console.print(f"[red]Failed to initiate settlement.[/red] Error: {settlement_response}")
        return

    # Handle response
    if payment_method != "OVO":
        deeplink = settlement_response["data"].get("deeplink", "")
        if deeplink:
            console.print(Panel(f"[bold green]Silahkan selesaikan pembayaran melalui link berikut:[/bold green]\n{deeplink}", title="Payment Link"))
    else:
        console.print(Panel("[bold green]Silahkan buka aplikasi OVO Anda untuk menyelesaikan pembayaran.[/bold green]", title="OVO Payment"))
