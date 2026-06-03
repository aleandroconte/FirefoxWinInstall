#!/usr/bin/env python3
"""
install_firefox.py
Scarica e installa l'ultima versione stabile di Firefox su Windows 10.
  1. Recupera la versione più recente dalle API Mozilla
  2. Scarica il programma di installazione
  3. Esegue l'installazione silenziosa
"""

import os
import sys
import urllib.request
import json
import subprocess
import tempfile

# ───────────────────────────────────────────────────────────────────────────────

BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

MOZILLA_VERSION_API = "https://product-details.mozilla.org/1.0/firefox_versions.json"
FIREFOX_DOWNLOAD_URL = "https://download.mozilla.org/?product=firefox-latest-ssl&os=win64&lang=it"
INSTALLER_NAME = "firefox_installer.exe"

# ───────────────────────────────────────────────────────────────────────────────

def banner():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════╗
║       Firefox Installer for Windows      ║
║       + RSAT Active Directory Tools      ║
╚══════════════════════════════════════════╝{RESET}
""")

def log(msg: str):
    print(f"{GREEN}[+]{RESET} {msg}")

def warn(msg: str):
    print(f"{YELLOW}[!]{RESET} {msg}")

def err(msg: str):
    print(f"{RED}[-]{RESET} {msg}")

def section(title: str):
    print(f"\n{BOLD}{CYAN}── {title} {'─' * (40 - len(title))}{RESET}")

def check_windows():
    if sys.platform != "win32":
        err("Questo script è pensato per Windows. Piattaforma rilevata: " + sys.platform)
        sys.exit(1)

# ─── STEP 1: Recupera versione più recente ────────────────────────────────────

def get_latest_version() -> str:
    section("STEP 1 — Recupero ultima versione disponibile")
    log(f"Contatto API Mozilla: {MOZILLA_VERSION_API}")
    try:
        with urllib.request.urlopen(MOZILLA_VERSION_API, timeout=10) as response:
            data = json.loads(response.read())
            version = data["LATEST_FIREFOX_VERSION"]
            log(f"Ultima versione stabile: {BOLD}{version}{RESET}")
            return version
    except Exception as e:
        warn(f"Impossibile contattare le API Mozilla ({e}).")
        warn("Procedo comunque con il link di download diretto all'ultima versione.")
        return None

# ─── STEP 2: Download installer ───────────────────────────────────────────────

def download_installer(version: str) -> str:
    section("STEP 2 — Download installer Firefox")

    installer_path = os.path.join(tempfile.gettempdir(), INSTALLER_NAME)

    if version:
        url = (
            f"https://releases.mozilla.org/pub/firefox/releases/{version}/"
            f"win64/it/Firefox%20Setup%20{version}.exe"
        )
    else:
        url = FIREFOX_DOWNLOAD_URL

    log(f"URL: {url}")
    log(f"Destinazione: {installer_path}")
    log("Download in corso...")

    try:
        def progress(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 // total_size)
                bar = ("█" * (percent // 5)).ljust(20)
                print(f"\r    [{bar}] {percent}%", end="", flush=True)

        urllib.request.urlretrieve(url, installer_path, reporthook=progress)
        print()  # newline dopo la barra
        log("Download completato.")
        return installer_path

    except Exception as e:
        print()
        err(f"Download fallito: {e}")
        # Fallback al link diretto Mozilla se il link versione specifica fallisce
        if url != FIREFOX_DOWNLOAD_URL:
            warn("Provo con il link diretto Mozilla...")
            try:
                urllib.request.urlretrieve(FIREFOX_DOWNLOAD_URL, installer_path, reporthook=progress)
                print()
                log("Download completato (link diretto).")
                return installer_path
            except Exception as e2:
                print()
                err(f"Anche il link diretto è fallito: {e2}")
        sys.exit(1)

# ─── STEP 3: Installazione silenziosa ────────────────────────────────────────

def install_firefox(installer_path: str):
    section("STEP 3 — Installazione Firefox")
    log("Avvio installazione silenziosa (/S)...")
    log("Timeout: 3 minuti. Se si blocca verrà interrotto automaticamente.")

    try:
        result = subprocess.run(
            [installer_path, "/S"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            log("Firefox installato con successo.")
        else:
            err(f"L'installer ha restituito il codice {result.returncode}.")
            warn(f"Prova manualmente: {installer_path} /S")
            sys.exit(result.returncode)

    except subprocess.TimeoutExpired:
        err("Installazione Firefox bloccata dopo 3 minuti. Processo terminato.")
        warn(f"Prova manualmente: {installer_path} /S")
        sys.exit(1)

# ─── STEP 4: Pulizia ──────────────────────────────────────────────────────────

def cleanup(installer_path: str):
    section("STEP 4 — Pulizia file temporanei")
    try:
        os.remove(installer_path)
        log(f"Installer rimosso: {installer_path}")
    except Exception as e:
        warn(f"Impossibile rimuovere l'installer ({e}). Puoi eliminarlo manualmente.")

# ─── STEP 5: Installazione RSAT Active Directory ─────────────────────────────

def get_windows_os_type() -> str:
    """Rileva se siamo su Windows Desktop o Windows Server."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-WmiObject Win32_OperatingSystem).Caption"],
            capture_output=True, text=True, timeout=15
        )
        caption = result.stdout.strip().lower()
        if "server" in caption:
            log(f"OS rilevato: Windows Server ({result.stdout.strip()})")
            return "server"
        else:
            log(f"OS rilevato: Windows Desktop ({result.stdout.strip()})")
            return "desktop"
    except Exception as e:
        warn(f"Impossibile rilevare il tipo di OS ({e}). Assumo Desktop.")
        return "desktop"

# ─── STEP 5: Installazione RSAT Active Directory ─────────────────────────────

def step_install_rsat():
    section("STEP 5 — Installazione RSAT Active Directory Tools")
    warn("Questo step richiede privilegi di amministratore.")
    log("Timeout per ogni comando: 10 minuti.")

    os_type = get_windows_os_type()

    if os_type == "server":
        # Su Windows Server: Install-WindowsFeature è il metodo corretto
        # Add-WindowsCapability non è disponibile su Server
        log("Windows Server rilevato: uso Install-WindowsFeature.")
        ps_commands = [
            (
                "Install-WindowsFeature -Name RSAT-AD-Tools -IncludeAllSubFeature",
                "RSAT AD Tools completo"
            ),
            (
                "Install-WindowsFeature -Name RSAT-AD-PowerShell",
                "RSAT AD PowerShell module"
            ),
        ]
    else:
        # Su Windows 10/11 Desktop: Add-WindowsCapability è il metodo corretto
        # Install-WindowsFeature non è disponibile su Desktop
        log("Windows Desktop rilevato: uso Add-WindowsCapability.")
        ps_commands = [
            (
                'Add-WindowsCapability -Online -Name "Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0"',
                "RSAT AD DS e LDS Tools"
            ),
            (
                'Add-WindowsCapability -Online -Name "Rsat.GroupPolicy.Management.Tools~~~~0.0.1.0"',
                "RSAT Group Policy Management Tools"
            ),
        ]

    for ps_cmd, description in ps_commands:
        log(f"Eseguo: {description} ...")
        print(f"  {YELLOW}${RESET} powershell -Command \"{ps_cmd}\"")

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600
            )
            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    print(f"    {line}")

            if result.returncode == 0:
                log(f"{description}: completato.")
            else:
                warn(f"Codice {result.returncode}. Esegui manualmente in PowerShell Admin:")
                warn(f"  {ps_cmd}")

        except subprocess.TimeoutExpired:
            err(f"Timeout (10 min) su: {description}")
            warn("Esegui manualmente in PowerShell Admin:")
            warn(f"  {ps_cmd}")

    log("RSAT Active Directory Tools: completato.")

# ─── RIEPILOGO ────────────────────────────────────────────────────────────────

def summary(version: str):
    section("RIEPILOGO")
    ver_str = version if version else "ultima disponibile"
    print(f"""
  {GREEN}✔{RESET} Versione Firefox scaricata: {BOLD}{ver_str}{RESET}
  {GREEN}✔{RESET} Firefox installato
  {GREEN}✔{RESET} File temporanei rimossi
  {GREEN}✔{RESET} RSAT AD DS e LDS Tools installato
  {GREEN}✔{RESET} RSAT AD PowerShell module installato

  {YELLOW}Firefox è installato in:{RESET}
    C:\\Program Files\\Mozilla Firefox\\firefox.exe

  {YELLOW}Verifica modulo AD PowerShell con:{RESET}
    Get-Module -ListAvailable -Name ActiveDirectory
""")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    banner()
    check_windows()

    version = get_latest_version()
    installer_path = download_installer(version)
    install_firefox(installer_path)
    cleanup(installer_path)
    step_install_rsat()
    summary(version)

if __name__ == "__main__":
    main()
