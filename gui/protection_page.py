import tkinter as tk
from tkinter import ttk
import json
import os

DATA_FOLDER = "data"
DEFAULTS_FILE = os.path.join(DATA_FOLDER,"protection_defaults.json")

class ProtectionPage(ttk.Frame):
    def __init__(self, parent, controller, device, measurement_manager):
        super().__init__(parent)
        self.controller = controller
        self.mm = measurement_manager
        self.device = device

        # Subscribe to protection trips
        self.mm.subscribe_protection(self.on_protection_trip)

        # ---------- Load Defaults ----------
        self.load_defaults()

        # ---------- UI ----------
        ttk.Label(self, text="", font=("Arial", 16, "bold")).pack(pady=10)
        self.title_label = self.children["!label"]
        self.title_label.trans_key = "label_protection_settings"

        settings_frame = ttk.Frame(self)
        settings_frame.pack(pady=5)

        # --- OVP ---
        ovp_label = ttk.Label(settings_frame, text="")
        ovp_label.trans_key = "label_ovp_limit"
        ovp_label.grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.ovp_var = tk.DoubleVar(value=self.defaults.get("ovp_limit", 20.0))
        self.ovp_enabled = tk.BooleanVar(value=self.defaults.get("ovp_enabled", True))
        ttk.Entry(settings_frame, textvariable=self.ovp_var, width=10).grid(row=0, column=1, padx=6, pady=6)
        ovp_chk = ttk.Checkbutton(settings_frame, text="", variable=self.ovp_enabled, command=self.update_protection)
        ovp_chk.trans_key = "checkbox_enable"
        ovp_chk.grid(row=0, column=2, padx=6, pady=6)

        # --- OCP ---
        ocp_label = ttk.Label(settings_frame, text="")
        ocp_label.trans_key = "label_ocp_limit"
        ocp_label.grid(row=1, column=0, padx=6, pady=6, sticky="e")
        self.ocp_var = tk.DoubleVar(value=self.defaults.get("ocp_limit", 2.0))
        self.ocp_enabled = tk.BooleanVar(value=self.defaults.get("ocp_enabled", True))
        ttk.Entry(settings_frame, textvariable=self.ocp_var, width=10).grid(row=1, column=1, padx=6, pady=6)
        ocp_chk = ttk.Checkbutton(settings_frame, text="", variable=self.ocp_enabled, command=self.update_protection)
        ocp_chk.trans_key = "checkbox_enable"
        ocp_chk.grid(row=1, column=2, padx=6, pady=6)

        # --- Status ---
        status_frame = ttk.LabelFrame(self, text="")
        status_frame.trans_key = "label_protection_status"
        status_frame.pack(pady=15, fill="x", padx=20)
        self.protection_status_label = ttk.Label(
            status_frame, text="", font=("Arial", 14, "bold"), foreground="green"
        )
        self.protection_status_label.trans_key = "label_protection_status_value"
        self.protection_status_label.pack(pady=10)

        # --- Buttons ---
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=10)

        reset_btn = ttk.Button(buttons_frame, text="", command=self.reset_protection)
        reset_btn.trans_key = "button_reset_protection"
        reset_btn.pack(side="left", padx=5)
        save_btn = ttk.Button(buttons_frame, text="", command=self.save_defaults)
        save_btn.trans_key = "button_save_settings"
        save_btn.pack(side="left", padx=5)

    # ------------------- Defaults -------------------
    def load_defaults(self):
        """Load OVP/OCP defaults from JSON file."""
        if os.path.exists(DEFAULTS_FILE):
            with open(DEFAULTS_FILE, "r") as f:
                self.defaults = json.load(f)
        else:
            # fallback defaults
            self.defaults = {
                "ovp_enabled": True,
                "ovp_limit": 20.0,
                "ocp_enabled": True,
                "ocp_limit": 2.0
            }

    def save_defaults(self):
        """Save current OVP/OCP settings to JSON file."""
        self.defaults = {
            "ovp_enabled": self.ovp_enabled.get(),
            "ovp_limit": self.ovp_var.get(),
            "ocp_enabled": self.ocp_enabled.get(),
            "ocp_limit": self.ocp_var.get()
        }
        with open(DEFAULTS_FILE, "w") as f:
            json.dump(self.defaults, f, indent=4)
        print("Protection settings saved.")
        self.update_protection()

    # ------------------- Protection Logic -------------------
    def update_protection(self):
        """Send OVP/OCP settings to MeasurementManager."""
        self.mm.set_ovp(self.ovp_enabled.get(), self.ovp_var.get())
        self.mm.set_ocp(self.ocp_enabled.get(), self.ocp_var.get())

    def on_protection_trip(self, reason: str):
        """Update UI when protection is triggered."""
        self.protection_status_label.config(
            text=f"Status: {reason} TRIPPED", foreground="orange"
        )

    def reset_protection(self):
        self.mm.reset_protection()
        self.protection_status_label.config(text="Status: SAFE", foreground="green")

    def get_initial_limits(self):
        """Return the initial OVP/OCP settings (loaded from defaults or defaults file)."""
        return {
            "ovp_enabled": self.ovp_enabled.get(),
            "ovp_limit": self.ovp_var.get(),
            "ocp_enabled": self.ocp_enabled.get(),
            "ocp_limit": self.ocp_var.get()
        }
