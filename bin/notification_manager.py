import requests

NTFY_SERVER_URL = "https://ntfy.sh"
NTFY_TOPIC = "austerealertscg"


def send_notification():
    requests.post(f"http://ntfy.sh/austerealertscg",
        data="cg testtoad".encode(encoding='utf-8'))


requests.post("https://ntfy.sh/stock_alerts_austere_1337",
    data="An urgent message",
    headers={ "Priority": "5" })
