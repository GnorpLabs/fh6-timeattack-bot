import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw

import api_client
import token_store

if TYPE_CHECKING:
    from session_manager import LapRecord, SessionManager


class App:
    def __init__(self, session: "SessionManager", loop: asyncio.AbstractEventLoop) -> None:
        self.session = session
        self.loop = loop
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        """Start the system tray. Blocks until quit. Must be called from main thread."""
        if not token_store.is_setup_complete():
            _show_setup_dialog()
        self._icon = pystray.Icon(
            "FH6 Relay",
            _make_tray_image(),
            "FH6 Relay",
            pystray.Menu(
                pystray.MenuItem("Session Review", self._on_open_review),
                pystray.MenuItem("Settings", self._on_open_settings),
                pystray.MenuItem("Quit", self._on_quit),
            ),
        )
        self._icon.run()

    def notify_new_lap(self, lap: "LapRecord") -> None:
        ms = lap.lap_time_ms
        m, rest = divmod(ms, 60_000)
        s, ms_part = divmod(rest, 1_000)
        time_str = f"{m}:{s:02d}.{ms_part:03d}" if m else f"{s}.{ms_part:03d}"
        if self._icon:
            self._icon.notify(f"Lap {lap.lap_number} recorded: {time_str}", "FH6 Relay")

    def _on_open_review(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        threading.Thread(target=self._show_review_window, daemon=True).start()

    def _on_open_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        threading.Thread(target=_show_settings_dialog, daemon=True).start()

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        icon.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)

    def _show_review_window(self) -> None:
        cfg = token_store.load_config()

        root = tk.Tk()
        root.title("FH6 Relay — Session Review")
        root.geometry("620x420")

        # Track / vehicle selectors
        frame_top = tk.Frame(root)
        frame_top.pack(fill="x", padx=10, pady=6)

        tk.Label(frame_top, text="Track:").pack(side="left")
        track_var = tk.StringVar()
        track_combo = ttk.Combobox(frame_top, textvariable=track_var, width=28)
        track_combo.pack(side="left", padx=(4, 12))

        tk.Label(frame_top, text="Vehicle:").pack(side="left")
        vehicle_var = tk.StringVar()
        vehicle_combo = ttk.Combobox(frame_top, textvariable=vehicle_var, width=30)
        vehicle_combo.pack(side="left", padx=4)

        # Laps table
        tree = ttk.Treeview(root, columns=("lap", "time"), show="headings", selectmode="browse")
        tree.heading("lap", text="Lap #")
        tree.heading("time", text="Time")
        tree.column("lap", width=80, anchor="center")
        tree.column("time", width=160, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=4)

        for lap in self.session.get_laps_snapshot():
            ms = lap.lap_time_ms
            m, rest = divmod(ms, 60_000)
            s, ms_part = divmod(rest, 1_000)
            time_str = f"{m}:{s:02d}.{ms_part:03d}" if m else f"{s}.{ms_part:03d}"
            tree.insert("", "end", iid=str(lap.lap_number), values=(lap.lap_number, time_str))

        status_var = tk.StringVar(value="Select a lap and fill in track + vehicle, then submit.")
        tk.Label(root, textvariable=status_var, anchor="w").pack(fill="x", padx=10)

        def on_submit() -> None:
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Lap", "Select a lap row first.", parent=root)
                return
            if not track_var.get().strip():
                messagebox.showwarning("No Track", "Select or type a track name.", parent=root)
                return
            if not vehicle_var.get().strip():
                messagebox.showwarning("No Vehicle", "Select or type a vehicle name.", parent=root)
                return

            lap_num = int(sel[0])
            lap = next(l for l in self.session.get_laps_snapshot() if l.lap_number == lap_num)
            status_var.set("Submitting…")
            root.update()

            future = asyncio.run_coroutine_threadsafe(
                api_client.submit_lap(
                    api_url=cfg["api_url"],
                    token=cfg["token"],
                    discord_id=cfg["discord_id"],
                    discord_username=cfg["discord_username"],
                    lap=lap,
                    track=track_var.get().strip(),
                    vehicle_name=vehicle_var.get().strip(),
                ),
                self.loop,
            )
            try:
                result = future.result(timeout=10)
                status_var.set(f"Submitted! Entry #{result['entry_id']} — check Discord for confirmation.")
            except ValueError as exc:
                reason = str(exc)
                if "token_expired" in reason:
                    messagebox.showerror(
                        "Token Expired",
                        "Your token has expired.\nRun /dataout-refresh in Discord, then update it via Settings.",
                        parent=root,
                    )
                else:
                    messagebox.showerror("Submission Failed", f"Server error: {reason}", parent=root)
                status_var.set("Submission failed.")
            except Exception as exc:
                messagebox.showerror("Network Error", str(exc), parent=root)
                status_var.set("Submission failed.")

        def on_clear() -> None:
            self.session.reset()
            for item in tree.get_children():
                tree.delete(item)
            status_var.set("Session cleared.")

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=10, pady=6)
        tk.Button(btn_frame, text="Submit Selected Lap", command=on_submit).pack(side="right")
        tk.Button(btn_frame, text="Clear Session", command=on_clear).pack(side="right", padx=6)

        # Fetch tracks + vehicles from bot API in background
        if cfg.get("api_url"):
            import aiohttp

            async def _fetch() -> tuple[list, list]:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(f"{cfg['api_url']}/api/tracks") as r:
                        tracks = await r.json()
                    async with sess.get(f"{cfg['api_url']}/api/vehicles") as r:
                        vehicles_raw = await r.json()
                return tracks, [v["name"] for v in vehicles_raw]

            fetch_future = asyncio.run_coroutine_threadsafe(_fetch(), self.loop)
            try:
                tracks, vehicle_names = fetch_future.result(timeout=5)
                track_combo["values"] = tracks
                vehicle_combo["values"] = vehicle_names
            except Exception:
                pass  # offline — user can type values manually

        root.mainloop()


def _show_setup_dialog() -> None:
    root = tk.Tk()
    root.title("FH6 Relay — First Time Setup")
    root.resizable(False, False)

    cfg = token_store.load_config()
    rows = [
        ("api_url", "Server IP or FQDN", "e.g. 192.168.1.1 or bot.example.com"),
        ("discord_id", "Discord User ID", "Developer Mode → right-click profile → Copy User ID"),
        ("discord_username", "Discord Username", "e.g. alice"),
        ("token", "Token", "From /dataout-register in Discord"),
    ]
    entries: dict[str, tk.Entry] = {}
    for i, (key, label, hint) in enumerate(rows):
        tk.Label(root, text=label, anchor="w", font=("", 10, "bold")).grid(
            row=i * 2, column=0, columnspan=2, padx=12, pady=(8, 0), sticky="w"
        )
        tk.Label(root, text=hint, anchor="w", fg="gray").grid(
            row=i * 2, column=0, columnspan=2, padx=12, sticky="w"
        )
        entry = tk.Entry(root, width=52)
        entry.insert(0, cfg.get(key, ""))
        entry.grid(row=i * 2 + 1, column=0, columnspan=2, padx=12, pady=(2, 0), sticky="ew")
        entries[key] = entry

    def on_save() -> None:
        values = {k: e.get().strip() for k, e in entries.items()}
        if not all(values.values()):
            messagebox.showerror("Required", "All fields are required.", parent=root)
            return
        api_url = values["api_url"]
        if not api_url.startswith("http"):
            api_url = f"https://{api_url}"
        token_store.save_setup(
            api_url=api_url,
            discord_id=values["discord_id"],
            discord_username=values["discord_username"],
            token=values["token"],
        )
        root.destroy()

    tk.Button(root, text="Save & Continue", command=on_save, width=20).grid(
        row=len(rows) * 2, column=0, columnspan=2, pady=14
    )
    root.mainloop()


def _show_settings_dialog() -> None:
    _show_setup_dialog()


def _make_tray_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(0, 180, 80))
    return img
