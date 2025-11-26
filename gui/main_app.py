import tkinter as tk
from ttkthemes import ThemedTk
from PIL import Image, ImageTk, ImageOps
import sys,os

from gui.status_page import StatusPage
from gui.measurement_manager import MeasurementManager
from gui.config_page import ConfigPage
from gui.control_page import ControlPage
from gui.protection_page import ProtectionPage
from gui.graph_page import GraphPage
from gui.info_page import InfoPage
from utils.translation_utils import Translator

class MainApp(ThemedTk):
    def __init__(self, device):
        super().__init__(theme="breeze")
        self.translator = Translator('en')  # Default language
        self.title(self.translator.t("app_title"))
        self.geometry("800x640")
        self.device = device
        self.simulation_active = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # ---------------- Navigation Bar ----------------
        self.navar_frame = tk.Frame(self, bg="#e0e0e0", height=70)
        self.navar_frame.pack(fill="x", side="top")

        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")

        nav_items = [
            ("ConfigPage", "nav_config", "config.png"),
            ("StatusPage", "nav_status", "status.png"),
            ("ControlPage", "nav_control", "control.png"),
            ("ProtectionPage", "nav_protection", "protection.png"),
            ("GraphPage", "nav_logging", "graph.png"),
            ("InfoPage", "nav_about", "about.png")
        ]
        self.nav_buttons = {}
        self.nav_icons = {}
        self.active_page = None

        # ---------------- Connection Status Icon (Right Side) ----------------
        status_frame = tk.Frame(self.navar_frame, bg="#e0e0e0")
        status_frame.pack(side="right", padx=15)

        # Load icons
        try:
            self.icon_connected = ImageTk.PhotoImage(
                Image.open(os.path.join(base_path, "connected.png")).resize((28, 28), Image.Resampling.LANCZOS)
            )
            self.icon_disconnected = ImageTk.PhotoImage(
                Image.open(os.path.join(base_path, "disconnected.png")).resize((28, 28), Image.Resampling.LANCZOS)
            )
            self.icon_simulation = ImageTk.PhotoImage(
                Image.open(os.path.join(base_path, "simulation.png")).resize((28, 28), Image.Resampling.LANCZOS)
            )
        except Exception as e:
            print(f"[WARN] Could not load connection icons: {e}")
            self.icon_connected = self.icon_disconnected = self.icon_simulation = None

        # Icon label
        self.connection_icon_label = tk.Label(
            status_frame,
            image=self.icon_connected if self.device.is_connected() else self.icon_disconnected,
            bg="#e0e0e0"
        )
        self.connection_icon_label.pack()

        # Optional tooltip text under icon
        self.connection_text_label = tk.Label(
            status_frame,
            text="Connected" if self.device.is_connected() else "Disconnected",
            font=("Helvetica", 9, "italic"),
            bg="#e0e0e0",
            fg="#2ecc71" if self.device.is_connected() else "#e74c3c"
        )
        self.connection_text_label.pack()

        # ---------------- Main Content Area ----------------
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # ---------------- Measurement Manager ----------------
        self.mm = MeasurementManager(self, self.device)

        # Subscribe connection status with a wrapper that forces simulation
        def connection_callback(connected: bool):
            # If simulation is active, force simulation icon
            self.update_connection_status_icon(
                connected=connected,
                simulation=self.simulation_active  # True if simulation active
            )

        self.mm.subscribe_connection_status(connection_callback)
        # ---------------- Frames dictionary ----------------
        self.frames = {}
        for PageClass in (ConfigPage, StatusPage, ControlPage, ProtectionPage, GraphPage, InfoPage):
            page_name = PageClass.__name__
            frame = PageClass(container, self, self.device, self.mm)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            self._update_widget_texts(frame)

        # ----------- Initialize MM from ProtectionPage ---------
        protection_page = self.frames["ProtectionPage"]
        initial_limits = protection_page.get_initial_limits()  # <-- NEW
        self.mm.set_ovp(initial_limits["ovp_enabled"], initial_limits["ovp_limit"])
        self.mm.set_ocp(initial_limits["ocp_enabled"], initial_limits["ocp_limit"])

        # ---------------- Start Measurement Manager ----------------
        self.mm.start()

        # ---------------- Helper to disable icons ----------------
        def make_icon_disabled(img, opacity=0.3):
            """Return the same image with lower opacity (alpha reduced)."""
            img = img.convert("RGBA")
            r, g, b, a = img.split()
            a = a.point(lambda p: int(p * opacity))
            img.putalpha(a)
            return img

        # ---------------- Navigation Buttons ----------------
        def set_active_page(name):
            self.active_page = name
            for page, btn in self.nav_buttons.items():
                if page == name:
                    btn.config(bg="#ffffff")  # Active
                    if self.nav_icons[page]:
                        btn.image = ImageTk.PhotoImage(self.nav_icons[page])
                        btn.config(image=btn.image)
                else:
                    btn.config(bg="#e0e0e0")  # Inactive
                    if self.nav_icons[page]:
                        disabled_img = make_icon_disabled(self.nav_icons[page], opacity=0.3)
                        btn.image = ImageTk.PhotoImage(disabled_img)
                        btn.config(image=btn.image)

            self.show_frame(name)

        for page_name, trans_key, filename in nav_items:
            icon_path = os.path.join(base_path, filename)
            try:
                img = Image.open(icon_path).resize((32, 32), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"[WARN] Could not load icon {filename}: {e}")
                img = None

            self.nav_icons[page_name] = img

            btn_frame = tk.Frame(self.navar_frame, bg="#e0e0e0")
            btn_frame.pack(side="left", expand=True, fill="both")

            btn = tk.Button(
                btn_frame,
                text=self.translator.t(trans_key),
                compound="top",
                bg="#d0d0d0",
                relief="flat",
                command=lambda n=page_name: set_active_page(n)
            )
            btn.trans_key = trans_key  # <-- add this
            btn.pack(expand=True, fill="both", pady=2, padx=2)

            # Assign initial icon (disabled if not active)
            if img:
                if page_name == "ConfigPage":  # initial active page
                    tk_img = ImageTk.PhotoImage(img)
                else:
                    tk_img = ImageTk.PhotoImage(make_icon_disabled(img, opacity=0.3))
                btn.config(image=tk_img)
                btn.image = tk_img  # keep reference
        
            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#f0f0f0"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(
                bg="#eaeaea" if b == self.nav_buttons.get(self.active_page) else "#d0d0d0"))

            self.nav_buttons[page_name] = btn

        # ---------------- Show initial page ----------------
        set_active_page("ConfigPage")
    def show_frame(self, page_name):
        # Call on_hide for all frames first
        for name, frame in self.frames.items():
            if hasattr(frame, "on_hide"):
                frame.on_hide()

        # Raise the selected frame
        frame = self.frames[page_name]
        frame.tkraise()

        # Call on_show for the selected frame
        if hasattr(frame, "on_show"):
            frame.on_show()
    def update_connection_status_icon(self, connected: bool, simulation: bool = False):
        """Update connection status icon and text in the nav bar."""

        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")

        # ✅ Force to simulation mode if simulation is active
        t = self.translator.t

        if self.simulation_active:
            icon_file = "simulation.png"
            text = t("status_simulation")
            color = "#3498db"  # Blue

        # ✅ Strict priority: Simulation ONLY if simulation=True AND connected=True
        elif simulation and connected:
            icon_file = "simulation.png"
            text = t("status_simulation")
            color = "#3498db"  # Blue

        elif connected:
            icon_file = "connected.png"
            text = t("status_connected")
            color = "#2ecc71"  # Green

        else:
            icon_file = "disconnected.png"
            text = t("status_disconnected")
            color = "#e74c3c"  # Red

        icon_path = os.path.join(base_path, icon_file)

        try:
            img = Image.open(icon_path).resize((28, 28), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[WARN] Could not load connection icon: {e}")
            return

        tk_img = ImageTk.PhotoImage(img)
        self.connection_icon_label.config(image=tk_img)
        self.connection_icon_label.image = tk_img
        self.connection_text_label.config(text=text, fg=color)

        print(f"[DEBUG] Icon updated -> {text} ({icon_file})")

    def update_nav_labels(self):
        for page_name, btn in self.nav_buttons.items():
            if hasattr(btn, "trans_key"):
                btn.config(text=self.translator.t(btn.trans_key))
    
    def change_language(self, lang_code):
        self.translator.load_language(lang_code)
        self.title(self.translator.t("app_title"))
        self.update_nav_labels()
        
        self.refresh_all_pages()
        

    def refresh_all_pages(self):
        for page in self.frames.values():
            self._update_widget_texts(page)
        

    def _update_widget_texts(self, parent):
        """Recursively update widgets that have a translation key (trans_key)."""
        for widget in parent.winfo_children():
            # Update text if trans_key exists
            if hasattr(widget, "trans_key"):
                widget.config(text=self.translator.t(widget.trans_key))
            # Recurse into nested frames, tabs, labelframes, etc.
            if widget.winfo_children():
                self._update_widget_texts(widget)
    
    def resource_path(relative_path):
        """Get the absolute path to resource, works for dev and for PyInstaller .exe"""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
    
    def on_close(self):
        """Properly stop threads and close the app."""
        print("[INFO] Closing application...")
        try:
            # Stop measurement manager thread safely
            if hasattr(self, "mm") and self.mm.is_running:
                self.mm.stop()

            # Disconnect device if needed
            if hasattr(self, "device") and self.device.is_connected():
                try:
                    self.device.disconnect()
                except Exception as e:
                    print(f"[WARN] Failed to disconnect device: {e}")
        except Exception as e:
            print(f"[ERROR] Error during shutdown: {e}")

        # Destroy window and exit
        self.destroy()
        self.quit()
        sys.exit(0)