"""Avisa no Telegram quando um CTFd lança desafios novos.

Roda uma vez por execução (feito pra GitHub Actions) e guarda os IDs já
vistos em seen.json. Usa só a biblioteca padrão do Python.
Configuração por variáveis de ambiente (GitHub Secrets):
  CTF_URL, CTF_TOKEN, TG_TOKEN, TG_CHAT_ID
"""
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

CTF_URL = os.environ.get("CTF_URL", "").rstrip("/")
CTF_TOKEN = os.environ.get("CTF_TOKEN", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
STATE_FILE = "seen.json"


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def get_challenges():
    headers = {"Content-Type": "application/json", "User-Agent": "ctf-notify/1.0"}
    if CTF_TOKEN:
        headers["Authorization"] = f"Token {CTF_TOKEN}"
    req = urllib.request.Request(f"{CTF_URL}/api/v1/challenges", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return {str(c["id"]): c for c in data.get("data", [])}


def send_telegram(text):
    body = urllib.parse.urlencode(
        {
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=30) as r:
        r.read()


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return None  # primeira execução


def save_seen(ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids, key=lambda x: (len(x), x)), f)


def main():
    if "--teste" in sys.argv:
        send_telegram("✅ Bot de CTF conectado ao Telegram!")
        log("Mensagem de teste enviada.")
        return

    atuais = get_challenges()
    seen = load_seen()

    if seen is None:
        save_seen(atuais.keys())
        log(f"Primeira execução: {len(atuais)} desafios registrados (sem notificar).")
        return

    novos = [c for i, c in atuais.items() if i not in seen]
    if not novos:
        log(f"Nada novo ({len(atuais)} desafios visíveis).")
        return

    linhas = ["🚩 <b>Novos desafios no CTF!</b>", ""]
    for c in novos:
        nome = html.escape(str(c.get("name")))
        cat = html.escape(str(c.get("category")))
        linhas.append(f"• <b>{nome}</b> — {cat} ({c.get('value')} pts)")
    linhas += ["", f"{CTF_URL}/challenges"]
    send_telegram("\n".join(linhas))
    save_seen(set(atuais.keys()) | seen)
    log(f"{len(novos)} desafio(s) novo(s) notificado(s).")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        log(f"Erro HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        log(f"Erro: {e}")
        sys.exit(1)
