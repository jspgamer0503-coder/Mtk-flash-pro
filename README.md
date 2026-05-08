# MTK Flash Pro

A clean, dark-themed GUI frontend for [mtkclient](https://github.com/bkerler/mtkclient) — the open-source MediaTek device toolkit. Flash, backup, exploit, and wipe MTK-based Android devices without touching the command line.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Linux-orange?logo=linux)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-4.3-informational)

---

## Features

- 🔍 **Scan Device** — Read the full partition table (GPT)
- 💾 **Backup Partitions** — Dump `boot`, `recovery`, `vbmeta`, and `lk`
- ⚡ **Flash Image** — Write any GSI or system image to a partition
- 🔓 **BROM Exploit** — Unlock via bootrom payload
- 🗑️ **Wipe Userdata** — Erase `userdata` and `metadata` partitions
- 📱 **Live USB Monitor** — Auto-detects BROM and Preloader mode
- 🔧 **Auto-repair** — Detects missing `mtkclient` and reinstalls it
- 🔒 **Passwordless sudo** — `fix_mtk.sh` sets up a scoped sudoers rule so the app never prompts mid-operation

---

## Requirements

- **OS**: Linux (Ubuntu/Debian recommended)
- **Python**: 3.8+
- **System packages**: `python3-venv`, `python3-tk`, `git`, `libusb-1.0-0`
- **GUI**: `customtkinter`, `pyusb` (installed automatically by `fix_mtk.sh`)
- **Backend**: [mtkclient](https://github.com/bkerler/mtkclient) (installed automatically into an isolated venv)

> **Note:** `mtkclient` is not on PyPI. It is pulled directly from GitHub by the setup script.

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/mtk-flash-pro.git
cd mtk-flash-pro
```

### 2. Run the setup script

```bash
bash fix_mtk.sh
```

This script will:
- Install system dependencies via `apt`
- Create a Python venv at `~/.local/share/mtk_flash_pro/venv`
- Install `mtkclient` and `customtkinter` from GitHub
- Write a scoped sudoers rule (`/etc/sudoers.d/mtk-flash-pro`) for passwordless elevation
- Install a `mtk-flash-pro` launcher to `~/.local/bin/`

> ⚠️ **Do NOT run `fix_mtk.sh` with `sudo`.** It will prompt for your password internally where needed.

### 3. Launch the app

```bash
mtk-flash-pro
```

Or directly:

```bash
python3 mtk_flash_pro.py
```

---

## Usage

### Entering BROM Mode

1. Power off your device
2. Hold **Volume −**
3. Plug in the USB cable

The device status badge in the sidebar will turn green and show **BROM Mode** when detected.

### Operations

| Operation | What it does |
|---|---|
| **Scan Device** | Runs `mtk printgpt` — prints the full partition table |
| **Backup Partitions** | Runs `mtk r boot,recovery,vbmeta,lk <output.bin>` |
| **Flash Image** | Runs `mtk w system <image.img>` |
| **BROM Exploit** | Runs `mtk payload` — executes the bootrom unlock payload |
| **Wipe Userdata** | Runs `mtk e userdata,metadata` |

All output streams live to the console panel. Use **Copy** to grab it or **Clear** to reset.

---

## Troubleshooting

### "Venv missing" on startup
Run `bash fix_mtk.sh` in a terminal. The app cannot create the venv itself.

### "Sudo not configured"
The sudoers rule is missing. Re-run `bash fix_mtk.sh` to restore it.

### Handshake failed
Re-plug the cable while holding **Vol−**. The app will log `↳ Re-plug while holding Vol-` as a hint.

### Device not detected
Make sure `libusb` is installed:
```bash
sudo apt install libusb-1.0-0
```
You may also need udev rules — see the [mtkclient docs](https://github.com/bkerler/mtkclient#linux).

### Repair Install button
If `mtkclient` gets corrupted or updated, click **⟳ Repair Install** in the sidebar. It reinstalls from GitHub without touching your sudoers or venv.

---

## Logs

Session logs are written to:

```
~/.mtk_flash_pro/session.log
```

---

## Project Structure

```
mtk-flash-pro/
├── mtk_flash_pro.py   # Main GUI application
├── fix_mtk.sh         # One-time setup and repair script
├── requirements.txt   # Direct Python dependencies (for reference)
└── README.md
```

---

## Security Notes

- Elevation uses `sudo bash <wrapper_script>` — **not** `pkexec` (which strips the environment and cannot run shell scripts).
- The sudoers rule grants `NOPASSWD` only for the specific wrapper script path, not blanket root access.
- Passwords (when zenity fallback is used) are passed via stdin and never logged.

---


---

## License

MIT — see [LICENSE](LICENSE)

---

## Disclaimer

This tool interacts with device bootloaders and low-level storage. **Incorrect use can brick your device.** Always back up before flashing. The authors are not responsible for damaged hardware.
