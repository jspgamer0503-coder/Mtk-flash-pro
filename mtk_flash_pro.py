#!/usr/bin/env python3
"""MTK Flash Pro v4.3 — clean sudo via bash wrapper"""

import customtkinter as ctk
import tkinter.filedialog as filedialog
import subprocess, threading, os, sys, time, logging, shutil
from datetime import datetime

APP_NAME = "MTK Flash Pro"
VERSION  = "4.3"
APP_DIR  = os.path.expanduser("~/.local/share/mtk_flash_pro")
VENV     = os.path.join(APP_DIR, "venv")
VENV_PY  = os.path.join(VENV, "bin", "python3")
VENV_PIP = os.path.join(VENV, "bin", "pip")
WRAPPER  = os.path.join(APP_DIR, "mtk_run.sh")
LOG_PATH = os.path.expanduser("~/.mtk_flash_pro/session.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(message)s")

# ── Ensure wrapper script exists ──────────────────────────────────────────────
def _ensure_wrapper():
    os.makedirs(APP_DIR, exist_ok=True)
    # mtkclient installs a "mtk" console script entry point in venv/bin/mtk
    mtk_bin = os.path.join(VENV, "bin", "mtk")
    with open(WRAPPER, "w") as f:
        f.write(f"""#!/bin/bash
# Activates venv and runs mtkclient
source "{VENV}/bin/activate"
# Use the installed mtk script if present, otherwise python -m mtkclient
if [ -x "{mtk_bin}" ]; then
    exec "{mtk_bin}" "$@"
else
    exec python3 -m mtkclient "$@"
fi
""")
    os.chmod(WRAPPER, 0o755)

_ensure_wrapper()

# ── Check mtkclient ───────────────────────────────────────────────────────────
def mtk_ok():
    """Check if mtkclient is installed and runnable in the venv."""
    try:
        # Try importing as mtkclient (the actual package name)
        r = subprocess.run(
            [VENV_PY, "-c", "import mtkclient"],
            capture_output=True, timeout=8)
        if r.returncode == 0:
            return True
        # Fallback: check via pip show
        r2 = subprocess.run(
            [VENV_PIP, "show", "mtkclient"],
            capture_output=True, timeout=8)
        return r2.returncode == 0
    except Exception:
        return False

# ── Elevation: ONLY "sudo bash WRAPPER args" ─────────────────────────────────
# pkexec is intentionally NOT used — it strips env and can't run shell scripts.
# The fix_mtk.sh script adds a NOPASSWD sudoers rule so this is always silent.

def _sudo_ok():
    """True if sudo currently needs no password."""
    try:
        return subprocess.run(["sudo","-n","true"],
                              capture_output=True, timeout=3).returncode == 0
    except Exception:
        return False

def _build_cmd(args):
    """
    Returns (cmd_list, needs_password:bool).
    Always uses: sudo bash WRAPPER args
    """
    cmd = ["sudo", "bash", WRAPPER] + args
    return cmd, not _sudo_ok()

def _get_password_via_zenity():
    try:
        r = subprocess.run(
            ["zenity","--password","--title=MTK Flash Pro — sudo password"],
            capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

# ── USB monitor ───────────────────────────────────────────────────────────────
def detect_mtk():
    try:
        import usb.core
        if usb.core.find(idVendor=0x0e8d, idProduct=0x0003): return "brom"
        if usb.core.find(idVendor=0x0e8d, idProduct=0x2000): return "preloader"
    except Exception:
        pass
    return None

# ── Colours ───────────────────────────────────────────────────────────────────
C = {
    "bg":"#0a0e1a","panel":"#0d1321","sidebar":"#060a14","card":"#111827",
    "accent":"#00e5ff","green":"#00ff88","amber":"#ffb300",
    "red":"#ff3d3d","muted":"#3d4966","text":"#cdd6f4","subtext":"#6b7a99",
}

# ── Card action button ────────────────────────────────────────────────────────
class ActionCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, subtitle, command):
        super().__init__(parent, corner_radius=12, fg_color=C["card"],
                         border_width=1, border_color=C["muted"])
        self._cmd    = command
        self._active = False

        for w in (self,):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

        left = ctk.CTkFrame(self, fg_color="transparent", width=44)
        left.pack(side="left", padx=(14,6), pady=12)
        self.icon_lbl = ctk.CTkLabel(left, text=icon,
                                     font=("Segoe UI Emoji",22),
                                     text_color=C["accent"])
        self.icon_lbl.pack()

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(side="left", fill="both", expand=True, pady=10)
        self.t_lbl = ctk.CTkLabel(mid, text=title,
                                  font=("Arial",14,"bold"),
                                  text_color=C["text"], anchor="w")
        self.t_lbl.pack(anchor="w")
        self.s_lbl = ctk.CTkLabel(mid, text=subtitle,
                                  font=("Arial",11),
                                  text_color=C["subtext"], anchor="w")
        self.s_lbl.pack(anchor="w")

        self.dot = ctk.CTkLabel(self, text="", width=14,
                                font=("Arial",18), text_color=C["green"])
        self.dot.pack(side="right", padx=14)

        for w in (left, mid, self.icon_lbl, self.t_lbl, self.s_lbl, self.dot):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def _click(self, _=None):
        if not self._active: self._cmd()

    def _hover(self, on):
        if not self._active:
            self.configure(border_color=C["accent"] if on else C["muted"])

    def set_active(self, on):
        self._active = on
        if on:
            self.configure(fg_color="#0a1a28", border_color=C["accent"],
                           border_width=2)
            self.icon_lbl.configure(text_color=C["green"])
            self.dot.configure(text="●")
        else:
            self.configure(fg_color=C["card"], border_color=C["muted"],
                           border_width=1)
            self.icon_lbl.configure(text_color=C["accent"])
            self.dot.configure(text="")


# ── Main app ──────────────────────────────────────────────────────────────────
class MTKFlashPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=C["bg"])
        self.title(f"{APP_NAME}  v{VERSION}")
        self.geometry("1240x820")
        self.minsize(960,660)

        self._proc       = None
        self._busy       = False
        self._mon_on     = True
        self._active_btn = None

        self._build_ui()
        self._start_monitor()
        self._startup_check()

    # ── Startup ───────────────────────────────────────────────────────────────
    def _startup_check(self):
        def _go():
            time.sleep(0.2)
            self._log(f"MTK Flash Pro v{VERSION}")
            self._log("Hold Vol- and plug USB to enter BROM mode.")
            self._log("─"*44)

            if not os.path.exists(VENV_PY):
                self._log("✗ Venv not found.")
                self._log("  Run fix_mtk.sh in a terminal first.")
                self.after(0, lambda: self._set_status("❌","Venv missing",
                    "Open terminal → bash fix_mtk.sh", C["red"]))
                return

            self._log(f"Venv: {VENV_PY}")

            if not mtk_ok():
                self._log("✗ mtkclient not in venv — auto-repairing…")
                self.after(0, lambda: self._set_status("🔧","Installing mtkclient…",
                    "Please wait…", C["amber"]))
                self.after(0, self.prog.start)
                self._repair(after=self._post_startup)
            else:
                self._log("✓ mtkclient OK")
                self._post_startup()

        threading.Thread(target=_go, daemon=True).start()

    def _post_startup(self):
        if _sudo_ok():
            self._log("✓ Elevation: passwordless sudo — no prompts")
        elif shutil.which("zenity"):
            self._log("⚠  Will prompt for password via zenity each time.")
            self._log("   Run fix_mtk.sh to make it passwordless.")
        else:
            self._log("✗  Cannot elevate to root!")
            self._log("   Run fix_mtk.sh in a terminal to fix this.")
            self.after(0, lambda: self._set_status("❌","Sudo not configured",
                "Open terminal → bash fix_mtk.sh", C["red"]))
            return

        self.after(0, lambda: self._set_status("💤","Idle — ready",
            "Select an operation from the left panel"))
        self.after(0, self.prog.stop)
        self.after(0, lambda: self.prog.set(0))

    def _repair(self, after=None):
        def _run():
            for cmd in [
                [VENV_PIP,"install","--upgrade","pip","--quiet"],
                [VENV_PIP,"install","--upgrade",
                 "git+https://github.com/bkerler/mtkclient.git"],
            ]:
                self._log(f"$ {' '.join(cmd)}")
                try:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True)
                    for l in iter(p.stdout.readline,""):
                        if l.strip(): self._log(f"  {l.rstrip()}")
                    p.wait()
                except Exception as e:
                    self._log(f"✗ {e}")

            if not mtk_ok():
                self._log("PyPI failed — trying git…")
                cmd = [VENV_PIP,"install","--upgrade",
                       "git+https://github.com/bkerler/mtkclient.git"]
                self._log(f"$ {' '.join(cmd)}")
                try:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True)
                    for l in iter(p.stdout.readline,""):
                        if l.strip(): self._log(f"  {l.rstrip()}")
                    p.wait()
                except Exception as e:
                    self._log(f"✗ {e}")

            if mtk_ok():
                self._log("✓ mtkclient installed!")
                self.after(0, lambda: self.repair_btn.configure(
                    text="✓ Repaired", text_color=C["green"]))
            else:
                self._log("✗ Install failed — run fix_mtk.sh in terminal.")
                self.after(0, lambda: self.repair_btn.configure(
                    text="✗ Repair failed", text_color=C["red"]))

            if after: after()
        threading.Thread(target=_run, daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        sb = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color=C["sidebar"])
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        # Logo
        lf = ctk.CTkFrame(sb, fg_color="transparent")
        lf.pack(pady=(28,16), padx=20, fill="x")
        ctk.CTkLabel(lf, text="MTK", font=("Impact",46),
                     text_color=C["accent"]).pack(side="left")
        ctk.CTkLabel(lf, text=" Flash\nPro", font=("Arial",15,"bold"),
                     text_color=C["green"], justify="left").pack(side="left",padx=4)

        # Device card
        dc = ctk.CTkFrame(sb, fg_color=C["card"], corner_radius=10)
        dc.pack(fill="x", padx=14, pady=(0,16))
        self.dev_icon = ctk.CTkLabel(dc, text="📵",
                                     font=("Segoe UI Emoji",20))
        self.dev_icon.pack(side="left", padx=(12,6), pady=10)
        dt = ctk.CTkFrame(dc, fg_color="transparent")
        dt.pack(side="left")
        ctk.CTkLabel(dt, text="DEVICE STATUS", font=("Arial",9),
                     text_color=C["subtext"]).pack(anchor="w")
        self.dev_badge = ctk.CTkLabel(dt, text="Searching…",
                                      font=("Arial",13,"bold"),
                                      text_color=C["amber"])
        self.dev_badge.pack(anchor="w")

        ctk.CTkFrame(sb, height=1, fg_color=C["muted"]).pack(fill="x",padx=14,pady=6)
        ctk.CTkLabel(sb, text="OPERATIONS", font=("Arial",10),
                     text_color=C["subtext"]).pack(anchor="w",padx=18,pady=(4,6))

        self.btn_info    = self._card(sb,"🔍","Scan Device",
                                      "Read partition table (GPT)", self._do_info)
        self.btn_backup  = self._card(sb,"💾","Backup Partitions",
                                      "Dump boot, recovery, vbmeta", self._do_backup)
        self.btn_flash   = self._card(sb,"⚡","Flash Image",
                                      "Write GSI / system image", self._do_flash)
        self.btn_exploit = self._card(sb,"🔓","BROM Exploit",
                                      "Unlock via bootrom payload", self._do_exploit)
        self.btn_wipe    = self._card(sb,"🗑️","Wipe Userdata",
                                      "Erase userdata + metadata", self._do_wipe)

        ctk.CTkFrame(sb, height=1, fg_color=C["muted"]).pack(fill="x",padx=14,pady=8)

        self.repair_btn = ctk.CTkButton(
            sb, text="⟳  Repair Install", height=34,
            fg_color=C["card"], hover_color="#1c2333",
            font=("Arial",12), text_color=C["subtext"],
            command=self._manual_repair)
        self.repair_btn.pack(fill="x", padx=14, pady=2)

        # Main area
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # Banner
        self.banner = ctk.CTkFrame(main, height=72, corner_radius=0,
                                   fg_color=C["panel"])
        self.banner.grid(row=0, column=0, sticky="ew")
        self.banner.grid_columnconfigure(1, weight=1)
        self.banner.grid_propagate(False)

        self.op_icon = ctk.CTkLabel(self.banner, text="💤",
                                    font=("Segoe UI Emoji",30))
        self.op_icon.grid(row=0, column=0, padx=(18,10), pady=(14,4))

        bt = ctk.CTkFrame(self.banner, fg_color="transparent")
        bt.grid(row=0, column=1, sticky="w", pady=(12,0))
        self.op_title = ctk.CTkLabel(bt, text="Idle — ready",
                                     font=("Arial",16,"bold"),
                                     text_color=C["text"])
        self.op_title.pack(anchor="w")
        self.op_sub = ctk.CTkLabel(bt, text="Select an operation from the left panel",
                                   font=("Arial",11),
                                   text_color=C["subtext"])
        self.op_sub.pack(anchor="w")

        self.prog = ctk.CTkProgressBar(self.banner, height=4,
                                       progress_color=C["accent"],
                                       fg_color=C["card"])
        self.prog.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.prog.set(0)

        # Console
        cw = ctk.CTkFrame(main, corner_radius=12, fg_color=C["panel"])
        cw.grid(row=1, column=0, sticky="nsew", padx=16, pady=(12,8))
        cw.grid_columnconfigure(0, weight=1)
        cw.grid_rowconfigure(1, weight=1)

        ch = ctk.CTkFrame(cw, fg_color="transparent", height=32)
        ch.grid(row=0, column=0, sticky="ew", padx=14, pady=(10,0))
        ctk.CTkLabel(ch, text="● LIVE OUTPUT", font=("Courier",10,"bold"),
                     text_color=C["green"]).pack(side="left")
        ctk.CTkButton(ch, text="Copy", width=58, height=24,
                      fg_color=C["card"], hover_color=C["muted"],
                      font=("Arial",10),
                      command=self._copy).pack(side="right", padx=(4,0))
        ctk.CTkButton(ch, text="Clear", width=58, height=24,
                      fg_color=C["card"], hover_color=C["muted"],
                      font=("Arial",10),
                      command=self._clear).pack(side="right")

        self.console = ctk.CTkTextbox(
            cw, font=("DejaVu Sans Mono",12),
            fg_color="#050810", text_color="#aaffcc",
            corner_radius=8, border_width=0)
        self.console.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4,8))

        # Footer
        foot = ctk.CTkFrame(main, height=52, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=16, pady=(0,12))
        self.kill_btn = ctk.CTkButton(
            foot, text="⬛  STOP OPERATION", height=40, width=200,
            fg_color="#2d0808", hover_color="#4a0f0f",
            font=("Arial",13,"bold"), text_color=C["red"],
            command=self._kill, state="disabled")
        self.kill_btn.pack(side="right")

    def _card(self, parent, icon, title, sub, cmd):
        b = ActionCard(parent, icon, title, sub, cmd)
        b.pack(fill="x", padx=14, pady=4)
        return b

    # ── Status ────────────────────────────────────────────────────────────────
    def _set_status(self, icon, title, sub, color=None):
        self.op_icon.configure(text=icon)
        self.op_title.configure(text=title, text_color=color or C["text"])
        self.op_sub.configure(text=sub)

    def _set_busy(self, btn, icon, title, sub):
        self._active_btn = btn
        btn.set_active(True)
        self._set_status(icon, title, sub, C["accent"])
        self.banner.configure(fg_color="#050f1a")
        self.prog.start()
        self.kill_btn.configure(state="normal")

    def _set_idle(self, success=True, label=""):
        if self._active_btn:
            self._active_btn.set_active(False)
            self._active_btn = None
        if success:
            self._set_status("✅", f"Done — {label}",
                             "Operation completed successfully", C["green"])
        else:
            self._set_status("❌", f"Failed — {label}",
                             "See log below for details", C["red"])
        self.banner.configure(fg_color=C["panel"])
        self.prog.stop()
        self.prog.set(0)
        self.kill_btn.configure(state="disabled")

    def _manual_repair(self):
        self.repair_btn.configure(text="⟳  Repairing…", state="disabled")
        self._set_status("🔧","Repairing…","Installing mtkclient…", C["amber"])
        self.prog.start()
        def _after():
            self.repair_btn.configure(state="normal",
                                      text="⟳  Repair Install")
            self.prog.stop(); self.prog.set(0)
            self._set_status("💤","Idle","Ready")
        self._repair(after=_after)

    # ── Process runner ────────────────────────────────────────────────────────
    def _run(self, args, btn, icon, label, sub):
        if self._busy:
            self._log("⚠ Already busy."); return
        if not mtk_ok():
            self._log("✗ mtkclient not installed — click ⟳ Repair Install"); return

        cmd, needs_pw = _build_cmd(args)

        # Get password before going busy (blocks main thread briefly but avoids
        # zenity appearing after spinner starts)
        password = None
        if needs_pw:
            if shutil.which("zenity"):
                password = _get_password_via_zenity()
                if password is None:
                    self._log("✗ Password cancelled."); return
                cmd = ["sudo","-S","bash",WRAPPER] + args
            else:
                self._log("✗ Needs root but no zenity. Run fix_mtk.sh to set up passwordless sudo.")
                return

        self._busy = True
        self.after(0, lambda: self._set_busy(btn, icon, label, sub))

        def _worker():
            self._log("─"*44)
            self._log(f"▶ {label}")
            display_cmd = cmd.copy()
            if "-S" in display_cmd:   # hide -S from display
                display_cmd = [c for c in display_cmd if c != "-S"]
            self._log(f"$ {' '.join(display_cmd)}")
            rc = -1
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE if password else None,
                    text=False, bufsize=0)
                if password:
                    self._proc.stdin.write((password+"\n").encode())
                    self._proc.stdin.close()
                for raw in iter(self._proc.stdout.readline, b""):
                    line = raw.decode(errors="replace").rstrip()
                    self._log(line)
                    if "Handshake failed" in line:
                        self._log("  ↳ Re-plug while holding Vol-")
                self._proc.wait()
                rc = self._proc.returncode
            except Exception as e:
                self._log(f"✗ {e}")
            finally:
                success = (rc == 0)
                self._log(f"{'✓' if success else '✗'} exit {rc}")
                self._log("─"*44)
                self._busy = False
                self._proc = None
                self.after(0, lambda: self._set_idle(success, label))

        threading.Thread(target=_worker, daemon=True).start()

    def _kill(self):
        if self._proc:
            self._proc.terminate()
            self._log("⬛ Stopped.")
            self._busy = False
            self._proc = None
            self.after(0, lambda: self._set_idle(False, "Stopped"))

    # ── Actions ──────────────────────────────────────────────────────────────
    def _do_info(self):
        self._run(["printgpt"], self.btn_info,
                  "🔍","Scanning Device","Reading partition table…")

    def _do_backup(self):
        out = filedialog.asksaveasfilename(
            title="Save backup as…", defaultextension=".bin",
            filetypes=[("Binary","*.bin"),("All","*.*")])
        if out:
            self._run(["r","boot,recovery,vbmeta,lk",out],
                      self.btn_backup,"💾","Backing Up",
                      f"Saving to {os.path.basename(out)}…")

    def _do_flash(self):
        img = filedialog.askopenfilename(
            title="Select image file",
            filetypes=[("Image","*.img"),("All","*.*")])
        if img:
            self._run(["w","system",img],
                      self.btn_flash,"⚡","Flashing Image",
                      f"{os.path.basename(img)} → system partition")

    def _do_exploit(self):
        self._run(["payload"], self.btn_exploit,
                  "🔓","BROM Exploit","Running bootrom payload…")

    def _do_wipe(self):
        self._run(["e","userdata,metadata"], self.btn_wipe,
                  "🗑️","Wiping Userdata","Erasing userdata and metadata…")

    # ── Log ──────────────────────────────────────────────────────────────────
    def _log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.insert("end", f"[{ts}]  {text}\n")
        self.console.see("end")
        logging.info(text)

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.console.get("1.0","end"))

    def _clear(self):
        self.console.delete("1.0","end")

    # ── USB monitor ──────────────────────────────────────────────────────────
    def _start_monitor(self):
        def _loop():
            while self._mon_on:
                s = detect_mtk()
                if s == "brom":        txt,col,ico = "BROM Mode",  C["green"], "📱"
                elif s == "preloader": txt,col,ico = "Preloader",  "#3b82f6",  "📱"
                else:                  txt,col,ico = "No Device",  C["muted"],  "📵"
                self.after(0, self.dev_badge.configure,
                           {"text":txt,"text_color":col})
                self.after(0, self.dev_icon.configure, {"text":ico})
                time.sleep(1.5)
        threading.Thread(target=_loop, daemon=True).start()

    def on_close(self):
        self._mon_on = False
        self.destroy()


if __name__ == "__main__":
    app = MTKFlashPro()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
