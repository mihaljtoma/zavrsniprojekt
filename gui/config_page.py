# gui/config_page.py
import os
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
import pyvisa
import json
import serial.tools.list_ports
import pyvisa.constants as visa_consts
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
# ------------------ CONFIG PATH ------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

COMMON_BAUD_RATES = [9600, 14400, 19200, 28800, 38400, 57600, 115200]
STOPBITS_MAP = {"1": visa_consts.StopBits.one, "2": visa_consts.StopBits.two}


class ConfigPage(ttk.Frame):
    def __init__(self, parent, controller, device, mm):
        super().__init__(parent)
        self.controller = controller
        self.device = device

        # ------------------ Variables ------------------
        self.selected_port = tk.StringVar()
        self.selected_baud = tk.StringVar()
        self.timeout_var = tk.IntVar()
        self.selected_parity = tk.StringVar()
        self.selected_stopbits = tk.StringVar()
        self.selected_databits = tk.StringVar()
        self.simulation_mode = tk.BooleanVar(value=False)  # default OFF

        # ---------- Build UI ----------
        self.sim_frame = ttk.LabelFrame(self, text="")
        self.sim_frame.trans_key = "label_sim_frame"
        self.sim_frame.pack(fill="x", padx=10, pady=5)

        self.sim_btn = ttk.Button(self.sim_frame, text="")
        self.sim_btn.trans_key = "button_simulation"
        self.sim_btn.config(command=self.toggle_simulation_mode)
        self.sim_btn.pack(padx=5, pady=5)
        self.sim_btn.pack(anchor="w", padx=8, pady=5)
        
        self.connection_frame = ttk.Frame(self)
        self.connection_frame.pack(fill="x", padx=10, pady=5)
        self.build_connection_ui(container=self.connection_frame)

        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.pack(fill="x", pady=10)
        self.build_buttons_ui(container=self.buttons_frame)

    
        self.sim_params_frame = ttk.Frame(self)
        self.sim_params_frame.pack_forget()
        self.build_simulation_ui(container=self.sim_params_frame)
        
        self.load_settings()
        self.result_label = ttk.Label(self, text="No connection", foreground="gray")
        self.result_label.pack(pady=5)

        self.toggle_simulation_mode()
        self.toggle_simulation_mode()

    # ------------------ UI Builders ------------------
    def build_connection_ui(self,container):
        # VISA / COM Port
        port_frame = ttk.LabelFrame(container, text="")
        port_frame.trans_key = "label_port_frame"
        port_frame.pack(fill="x", padx=10, pady=5)

        self.port_combo = ttk.Combobox(port_frame, textvariable=self.selected_port, width=25)
        self.port_combo.pack(side="left", padx=5, pady=5)

        refresh_btn = ttk.Button(port_frame, text="", command=self.refresh_ports)
        refresh_btn.trans_key = "button_refresh"
        refresh_btn.pack(side="left", padx=5)

        # Baud Rate
        baud_frame = ttk.LabelFrame(container, text="")
        baud_frame.trans_key = "label_baud_frame"
        baud_frame.pack(fill="x", padx=10, pady=5)

        baud_combo = ttk.Combobox(
            baud_frame, textvariable=self.selected_baud,
            values=[str(b) for b in COMMON_BAUD_RATES], width=10
        )
        baud_combo.pack(padx=5, pady=5)

        # Timeout
        timeout_frame = ttk.LabelFrame(container, text="")
        timeout_frame.trans_key = "label_timeout_frame"
        timeout_frame.pack(fill="x", padx=10, pady=5)

        timeout_spin = ttk.Spinbox(
            timeout_frame, from_=100, to=10000, increment=100,
            textvariable=self.timeout_var, width=10
        )
        timeout_spin.pack(padx=5, pady=5)

        # Parity
        parity_frame = ttk.LabelFrame(container, text="")
        parity_frame.trans_key = "label_parity_frame"
        parity_frame.pack(fill="x", padx=10, pady=5)

        parity_combo = ttk.Combobox(
            parity_frame, textvariable=self.selected_parity,
            values=["NONE", "EVEN(2)", "ODD(1)", "MARK(3)", "SPACE(4)"],
            width=10, state="readonly"
        )
        parity_combo.pack(padx=5, pady=5)

        # Stop Bits
        stopbits_frame = ttk.LabelFrame(container, text="")
        stopbits_frame.trans_key = "label_stopbits_frame"
        stopbits_frame.pack(fill="x", padx=10, pady=5)

        stopbits_combo = ttk.Combobox(
            stopbits_frame, textvariable=self.selected_stopbits,
            values=["1", "2"], width=10, state="readonly"
        )
        stopbits_combo.pack(padx=5, pady=5)

        # Data Bits
        databits_frame = ttk.LabelFrame(container, text="")
        databits_frame.trans_key = "label_databits_frame"
        databits_frame.pack(fill="x", padx=10, pady=5)

        databits_combo = ttk.Combobox(
            databits_frame, textvariable=self.selected_databits,
            values=["7", "8"], width=10, state="readonly"
        )
        databits_combo.pack(padx=5, pady=5)

    def build_buttons_ui(self,container):
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=10)
        inner_frame = ttk.Frame(button_frame)
        inner_frame.pack(anchor="center")

        self.test_btn = ttk.Button(inner_frame, text="")
        self.test_btn.trans_key = "button_test_connection"
        self.test_btn.config(command=self.test_connection)
        self.test_btn.pack(side="left", padx=5)

        self.apply_btn = ttk.Button(inner_frame, text="")
        self.apply_btn.trans_key = "button_apply"
        self.apply_btn.config(command=self.apply_settings)
        self.apply_btn.pack(side="left", padx=5)

        self.save_btn = ttk.Button(inner_frame, text="")
        self.save_btn.trans_key = "button_save_settings"
        self.save_btn.config(command=self.save_settings)
        self.save_btn.pack(side="left", padx=5)

        self.reset_btn = ttk.Button(inner_frame, text="")
        self.reset_btn.trans_key = "button_reset_device"
        self.reset_btn.config(command=self.reset_device)
        self.reset_btn.pack(side="left", padx=5)

        self.language_btn = ttk.Button(inner_frame, text="")
        self.language_btn.trans_key = "button_language"
        self.language_btn.config(command=self.open_language_popup)
        self.language_btn.pack(side="left", padx=5)

    def build_simulation_ui(self,container):

        sim_params_frame = ttk.LabelFrame(container, text="")
        sim_params_frame.trans_key = "label_sim_params_frame"
        sim_params_frame.pack(fill="x", padx=10, pady=5)

        res_label = ttk.Label(sim_params_frame, text="")
        res_label.trans_key = "label_load_resistance"
        res_label.grid(row=1, column=0, sticky="w")
        self.resistance_var = tk.DoubleVar(value=10.0)
        self.res_spinbox = ttk.Spinbox(sim_params_frame, from_=0.1, to=1000.0, increment=0.1, textvariable=self.resistance_var)
        self.res_spinbox.grid(row=1, column=1)

        self.apply_sim_btn = ttk.Button(sim_params_frame, text="")
        self.apply_sim_btn.trans_key = "button_apply_sim"
        self.apply_sim_btn.config(command=self.apply_simulation_params)
        self.apply_sim_btn.grid(row=5, column=0, columnspan=2, pady=5)

        self.apply_sim_btn.config(state="disabled")

    # ------------------ Methods ------------------
    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        port_list = [p.device for p in ports]
        try:
            rm = pyvisa.ResourceManager()
            visa_ports = rm.list_resources()
        except Exception:
            visa_ports = []
        all_ports = list(set(port_list + list(visa_ports)))
        self.port_combo['values'] = all_ports
        if all_ports:
            self.selected_port.set(all_ports[0])

    def load_settings(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}

        self.selected_port.set(self.config.get("address", ""))
        self.selected_baud.set(str(self.config.get("baud_rate", 19200)))
        self.timeout_var.set(self.config.get("timeout", 5000))
        self.selected_parity.set(self.config.get("parity", "NONE"))
        self.selected_stopbits.set(str(self.config.get("stop_bits", 1)))
        self.selected_databits.set(str(self.config.get("data_bits", 8)))

        return self.config


    def save_settings(self):
        self.config = {
            "address": self.selected_port.get(),
            "baud_rate": int(self.selected_baud.get()),
            "timeout": int(self.timeout_var.get()),
            "parity": self.selected_parity.get(),
            "stop_bits": float(self.selected_stopbits.get()),
            "data_bits": int(self.selected_databits.get()),
            "simulation_mode": self.simulation_mode.get()  # <--- NEW
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
        self.result_label.config(text=f"Settings saved to {CONFIG_FILE}", foreground="green")


    def test_connection(self):
        try:
            self.apply_settings()
            idn = self.device.get_id()
            self.result_label.config(text=f"Connected: {idn}", foreground="green")
        except Exception as e:
            self.result_label.config(text=f"Test failed: {e}", foreground="red")

    def apply_settings(self):
        try:
            stop_bits_enum = STOPBITS_MAP.get(self.selected_stopbits.get(), visa_consts.StopBits.one)
            self.device.apply_connection(
                address=self.selected_port.get(),
                baud_rate=int(self.selected_baud.get()),
                timeout=int(self.timeout_var.get()),
                parity=self.selected_parity.get(),
                stop_bits=stop_bits_enum,
                data_bits=int(self.selected_databits.get())
            )
            self.result_label.trans_key = "label_connection_applied"
            self.result_label.config(
                text=self.controller.translator.t(self.result_label.trans_key),
                foreground="green"
            )
            messagebox.showinfo(
                title=self.controller.translator.t("msg_success_title"),
                message=self.controller.translator.t("msg_connection_applied")
            )
        except Exception as e:
            self.result_label.trans_key = "label_connection_failed"
            self.result_label.config(
                text=self.controller.translator.t("label_connection_failed") + f": {e}",
                foreground="red"
            )
            messagebox.showerror(
                title=self.controller.translator.t("msg_error_title"),
                message=str(e)
            )

    def reset_device(self):
            try:
                self.device.write("*RST")
                self.result_label.trans_key = "label_device_reset"
                self.result_label.config(
                    text=self.controller.translator.t(self.result_label.trans_key),
                    foreground="blue"
                )
            except Exception as e:
                self.result_label.trans_key = "label_reset_failed"
                self.result_label.config(
                    text=self.controller.translator.t(self.result_label.trans_key) + f": {e}",
                    foreground="red"
                )

    
    def toggle_simulation_mode(self):
        """Toggle simulation mode on/off with a single button."""
        # If currently disabled → enable it
        if not getattr(self, "simulation_enabled", False):
            self.simulation_enabled = True
            self.sim_btn.trans_key = "button_stop_simulation"
            self.sim_btn.config(text=self.controller.translator.t(self.sim_btn.trans_key))

            
            self.device.enable_simulation(True)
            self.apply_sim_btn.config(state="normal")

            # Hide real connection UI
            self.connection_frame.pack_forget()
            self.buttons_frame.pack_forget()

            # Show simulation UI
            self.sim_params_frame.pack(fill="x", padx=10, pady=5)

            # ✅ Update MainApp state
            self.controller.simulation_active = True
            self.controller.update_connection_status_icon(
                connected=True,  # virtual device is "connected"
                simulation=True
            )

        else:
            self.simulation_enabled = False
            self.sim_btn.config(text=self.controller.translator.t("button_simulation"))

           
            self.device.enable_simulation(False)
            self.apply_sim_btn.config(state="disabled")

            self.connection_frame.pack(fill="x", padx=10)
            self.buttons_frame.pack(fill="x", pady=5)
            self.sim_params_frame.pack_forget()

            self.controller.simulation_active = False
            device_connected = self.device.is_connected()
            self.controller.update_connection_status_icon(
                connected=device_connected,
                simulation=False
            )


            


    def apply_simulation_params(self):
        resistance = self.resistance_var.get()
        self.device.set_load_resistance(resistance)

        messagebox.showinfo("Simulation", f"Resistor load set to {resistance} Ω")

    def open_language_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Language")
        popup.resizable(False, False)

        languages = {
            "en": "uk.png",
            "hr": "hr.png",
            "de": "de.png",
            "pl": "pl.png",
            "ru": "ru.png",
            "it": "it.png",
            "fr": "fr.png",
            "zh": "zh.png",
            "es": "es.png"
        }
        style = ttk.Style()
        style.configure("Flat.TButton", borderwidth=0, relief="flat", padding=0)

        self.lang_icons = {}
        columns = 3

        for index, (code, file_name) in enumerate(languages.items()):
            row = index // columns
            col = index % columns

            icon_path = resource_path(os.path.join("assets", file_name))
            img = Image.open(icon_path).resize((42, 32), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.lang_icons[code] = photo  

            btn = ttk.Button(
                popup,
                image=photo,
                command=lambda c=code: self.select_language(c, popup),
                style="Flat.TButton"
            )
            btn.grid(row=row, column=col, padx=10, pady=10)



    def select_language(self, lang_code, popup_window):
        self.controller.change_language(lang_code)
        popup_window.destroy()
   