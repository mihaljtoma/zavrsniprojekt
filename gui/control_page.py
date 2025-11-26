import tkinter as tk
from tkinter import ttk
import time
import json
import os
import tkinter.font as tkfont
class ControlPage(ttk.Frame):
    SCALE = 1000

    def __init__(self, parent, controller,device, measurement_manager):
        super().__init__(parent)
        self.controller = controller
        self.device = device
        self.mm = measurement_manager

        self.mm.subscribe(self.on_new_data)
        
        # in __init__ of your control panel
        self.max_voltage = self.mm.get_ovp()["limit"]
        self.max_current = self.mm.get_ocp()["limit"]

        # subscribe to updates
        self.mm.subscribe_limits(self._on_limit_update)

        self.auto_apply = True
        self.presets_file = "data/presets.json"
        self.voltage_presets, self.current_presets = self.load_presets()
        self.set_voltage = 0.0
        self.set_current = 0.0
        self.is_visible = False
        machine_font = tkfont.Font(family="DS-Digital", size=24, weight="bold")
      # ---------------- Main Frames ----------------
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Create 3 main columns
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=4)
        center_frame = ttk.Frame(main_frame)
        center_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=4)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        # ---------------- LEFT COLUMN ----------------

        # --- Protection Mirror ---
        protection_frame = ttk.LabelFrame(left_frame, text="")
        protection_frame.trans_key = "label_protection_status"
        protection_frame.pack(fill="x", pady=4)

        self.protection_status_var = tk.StringVar(value=self.controller.translator.t("label_safe"))

        self.protection_status_label = ttk.Label(
            protection_frame, 
            textvariable=self.protection_status_var, 
            font=("Arial", 14, "bold")
        )
        self.protection_status_label.pack(padx=5, pady=10)

        # --- Measurements ---
        measured_frame = ttk.LabelFrame(left_frame, text="")
        measured_frame.trans_key = "label_measurements"
        measured_frame.pack(fill="x", pady=4)

        big_font = ("Arial", 14, "bold")
        box_font = tkfont.Font(family="Courier", size=18, weight="bold")  # 7-segment style

        # Create StringVars for measurements
        self.meas_voltage_var = tk.StringVar(value="0.000 V")
        self.meas_current_var = tk.StringVar(value="0.000 A")
        self.meas_power_var = tk.StringVar(value="0.000 W")

        def create_measurement_row(parent, label_key, var):
            container = ttk.Frame(parent)
            container.pack(pady=6, anchor="center")
            lbl = ttk.Label(container, text="", font=big_font)
            lbl.trans_key = label_key
            lbl.pack(pady=(0,4))
            box = tk.Label(
                container,
                textvariable=var,
                font=box_font,
                relief="solid",
                borderwidth=2,
                width=12,
                anchor="center",
                bg="black",
                fg="lime"
            )
            box.pack()
            return container

        self.voltage_box = create_measurement_row(measured_frame, "label_voltage", self.meas_voltage_var)
        self.current_box = create_measurement_row(measured_frame, "label_current", self.meas_current_var)
        self.power_box = create_measurement_row(measured_frame, "label_power", self.meas_power_var)


        # ---------------- OUTPUT  ----------------
        self.output_state = tk.BooleanVar(value=False)

        # Large ON/OFF Button
        self.output_button = tk.Button(
            left_frame,
            text="",
            font=("Arial", 18, "bold"),
            bg="red",
            fg="white",
            command=self.toggle_output
        )
        self.output_button.trans_key = "button_output_off"
       
        self.output_button.pack(padx=10, pady=10, fill="x")

        # ---------------- CENTER COLUMN ----------------

        # --- Voltage Block ---
        v_frame = ttk.LabelFrame(center_frame, text="")
        v_frame.trans_key = "label_voltage_frame"       
        v_frame.pack(fill="x", pady=4)
        for i in range(4):
            v_frame.grid_columnconfigure(i, weight=1)

        self.voltage_var = tk.DoubleVar(value=0.000)
        self.voltage_entry = tk.Entry(
            v_frame, textvariable=self.voltage_var, width=10, font=machine_font,
            bg="lightblue", fg="white", justify="center"
        )
        self.voltage_entry.grid(row=0, column=0, columnspan=4, padx=2, pady=4, sticky="ew", ipady=6)

        self.v_pos = tk.IntVar(value=3)
        ttk.Button(v_frame, text="◀", width=2, command=lambda: self.change_position("voltage", -1)).grid(row=1, column=0)
        self.v_pos_label = ttk.Label(v_frame, text=self._pos_label(self.v_pos.get()), width=10, anchor="center")
        self.v_pos_label.grid(row=1, column=1, columnspan=2)
        ttk.Button(v_frame, text="▶", width=2, command=lambda: self.change_position("voltage", +1)).grid(row=1, column=3)

        ttk.Button(v_frame, text="-", width=2, command=lambda: self.increment_digit("voltage", -1)).grid(row=2, column=0)
        self.v_slider = tk.Scale(v_frame, from_=0, to=9, orient="horizontal", length=100, showvalue=True, resolution=1,
                                command=lambda v: self.on_slider_change("voltage", int(float(v))))
        self.v_slider.grid(row=2, column=1, columnspan=2, pady=4)
        ttk.Button(v_frame, text="+", width=2, command=lambda: self.increment_digit("voltage", +1)).grid(row=2, column=3)

        # --- Current Block ---
        c_frame = ttk.LabelFrame(center_frame, text="")
        c_frame.trans_key = "label_current_frame"
        c_frame.pack(fill="x", pady=4)
        for i in range(4):
            c_frame.grid_columnconfigure(i, weight=1)

        self.current_var = tk.DoubleVar(value=0.000)
        self.current_entry = tk.Entry(
            c_frame, textvariable=self.current_var, width=10, font=machine_font,
            bg="lightblue", fg="white", justify="center"
        )
        self.current_entry.grid(row=0, column=0, columnspan=4, padx=2, pady=4, sticky="ew", ipady=6)

        self.c_pos = tk.IntVar(value=3)
        ttk.Button(c_frame, text="◀", width=2, command=lambda: self.change_position("current", -1)).grid(row=1, column=0)
        self.c_pos_label = ttk.Label(c_frame, text=self._pos_label(self.c_pos.get()), width=10, anchor="center")
        self.c_pos_label.grid(row=1, column=1, columnspan=2)
        ttk.Button(c_frame, text="▶", width=2, command=lambda: self.change_position("current", +1)).grid(row=1, column=3)

        ttk.Button(c_frame, text="-", width=2, command=lambda: self.increment_digit("current", -1)).grid(row=2, column=0)
        self.c_slider = tk.Scale(c_frame, from_=0, to=9, orient="horizontal", length=100, showvalue=True, resolution=1,
                                command=lambda v: self.on_slider_change("current", int(float(v))))
        self.c_slider.grid(row=2, column=1, columnspan=2, pady=4)
        ttk.Button(c_frame, text="+", width=2, command=lambda: self.increment_digit("current", +1)).grid(row=2, column=3)


        # ---------------- RIGHT COLUMN ----------------

        # --- CV/CC Mode ---
        mode_frame = ttk.LabelFrame(right_frame, text="")
        mode_frame.trans_key = "label_mode_frame"
        mode_frame.pack(fill="x", pady=4)

        self.mode_label = ttk.Label(
            mode_frame, 
            text="",
            anchor="center",
            font=("Arial", 14, "bold")
        )
        self.mode_label.trans_key = "label_mode_text"
        self.mode_label.pack(padx=5, pady=6)

       
        # --- Apply / Auto Apply ---
        apply_frame = ttk.LabelFrame(right_frame, text="")
        apply_frame.trans_key = "label_apply_frame"
        apply_frame.pack(fill="x", pady=4)
        apply_btn = ttk.Button(apply_frame, text="", width=15, command=self.apply_settings)
        apply_btn.trans_key = "button_apply_settings"
        apply_btn.pack(padx=5, pady=4)
        self.auto_apply_var = tk.BooleanVar(value=True)
        auto_apply_chk = ttk.Checkbutton(
            apply_frame,
            text="",
            variable=self.auto_apply_var,
            command=lambda: setattr(self, 'auto_apply', self.auto_apply_var.get())
        )
        auto_apply_chk.trans_key = "checkbox_auto_apply"
        auto_apply_chk.pack(padx=5, pady=4)

       # ---------------- Voltage Presets ----------------
        self.voltage_presets_frame = ttk.LabelFrame(right_frame, text="")
        self.voltage_presets_frame.trans_key = "label_voltage_presets"  
        self.voltage_presets_frame.pack(fill="x", pady=4)

        # Top row: Entry + Add/Del buttons
        top_row = ttk.Frame(self.voltage_presets_frame)
        top_row.pack(fill="x", pady=2, padx=2)
        self.voltage_input_var = tk.StringVar()
        ttk.Entry(top_row, textvariable=self.voltage_input_var, width=6).pack(side="left", padx=(0,4))
        ttk.Button(top_row, text="+", width=3, command=self.add_voltage_preset).pack(side="left", padx=(0,2))
        ttk.Button(top_row, text="×", width=3, command=self.delete_voltage_preset).pack(side="left", padx=(0,2))

        # Frame to hold the preset value buttons
        self.voltage_buttons_frame = ttk.Frame(self.voltage_presets_frame)
        self.voltage_buttons_frame.pack(fill="x", pady=(4,2))

        # ---------------- Current Presets ----------------
        self.current_presets_frame = ttk.LabelFrame(right_frame, text="")
        self.current_presets_frame.trans_key = "label_current_presets"
        self.current_presets_frame.pack(fill="x", pady=4)

        top_row = ttk.Frame(self.current_presets_frame)
        top_row.pack(fill="x", pady=2, padx=2)
        self.current_input_var = tk.StringVar()
        ttk.Entry(top_row, textvariable=self.current_input_var, width=6).pack(side="left", padx=(0,4))
        ttk.Button(top_row, text="+", width=3, command=self.add_current_preset).pack(side="left", padx=(0,2))
        ttk.Button(top_row, text="×", width=3, command=self.delete_current_preset).pack(side="left", padx=(0,2))

        self.current_buttons_frame = ttk.Frame(self.current_presets_frame)
        self.current_buttons_frame.pack(fill="x", pady=(4,2))

        # Populate preset buttons initially
        self.refresh_presets_buttons()

        

    # ---------------- Helper functions ----------------
    def _pos_label(self, pos: int) -> str:
        mapping = {1: "10", 2: "1", 3: "0.1", 4: "0.01", 5: "0.001"}
        return f"Digit {pos} ({mapping.get(pos, '')})"

    def _pos_factor(self, pos: int) -> int:
        factors = {1: 10 * self.SCALE, 2: 1 * self.SCALE, 3: int(0.1 * self.SCALE),
                4: int(0.01 * self.SCALE), 5: int(0.001 * self.SCALE)}
        return factors[pos]

    def _get_scaled(self, control: str) -> int:
        return int(round((self.voltage_var.get() if control=="voltage" else self.current_var.get()) * self.SCALE))

    def _set_scaled(self, control: str, scaled: int):
        """Set scaled voltage/current value based on limits from MeasurementManager."""
        if control == "voltage":
            self.voltage_var.set(
                max(0, min(self.max_voltage, scaled / self.SCALE))
            )
        else:
            self.current_var.set(
                max(0, min(self.max_current, scaled / self.SCALE))
            )


    def _get_limits_scaled(self, control: str):
        """Return min/max scaled range dynamically."""
        if control == "voltage":
            return (0, int(self.max_voltage * self.SCALE))
        else:
            return (0, int(self.max_current * self.SCALE))


    def _get_pos(self, control: str) -> int:
        return self.v_pos.get() if control == "voltage" else self.c_pos.get()


    def _get_digit_at_pos(self, scaled: int, pos: int) -> int:
        return (scaled // self._pos_factor(pos)) % 10


    def _update_slider_from_value(self, control: str):
        scaled = self._get_scaled(control)
        pos = self._get_pos(control)
        digit = self._get_digit_at_pos(scaled, pos)
        if control == "voltage":
            self.v_slider.set(digit)
        else:
            self.c_slider.set(digit)


    def on_slider_change(self, control: str, digit: int):
        scaled = self._get_scaled(control)
        pos = self._get_pos(control)
        factor = self._pos_factor(pos)
        cur_digit = self._get_digit_at_pos(scaled, pos)
        new_scaled = scaled + (digit - cur_digit) * factor
        min_s, max_s = self._get_limits_scaled(control)
        new_scaled = max(min_s, min(max_s, new_scaled))
        self._set_scaled(control, new_scaled)
        self._update_slider_from_value(control)
        if self.auto_apply:
            self._apply_auto(control)


    def increment_digit(self, control: str, delta: int):
        scaled = self._get_scaled(control)
        pos = self._get_pos(control)
        cur_digit = self._get_digit_at_pos(scaled, pos)
        new_digit = max(0, min(9, cur_digit + delta))
        factor = self._pos_factor(pos)
        new_scaled = scaled + (new_digit - cur_digit) * factor
        min_s, max_s = self._get_limits_scaled(control)
        new_scaled = max(min_s, min(max_s, new_scaled))
        self._set_scaled(control, new_scaled)
        self._update_slider_from_value(control)
        if self.auto_apply:
            self._apply_auto(control)


    def change_position(self, control: str, delta: int):
        pos_var = self.v_pos if control == "voltage" else self.c_pos
        lbl = self.v_pos_label if control == "voltage" else self.c_pos_label
        new_pos = max(1, min(5, pos_var.get() + delta))
        pos_var.set(new_pos)
        lbl.config(text=self._pos_label(new_pos))
        self._update_slider_from_value(control)


    def on_entry_change(self, control: str):
        entry = self.voltage_entry if control == "voltage" else self.current_entry
        try:
            val = float(entry.get())
        except ValueError:
            val = self.voltage_var.get() if control == "voltage" else self.current_var.get()

        if control == "voltage":
            val = max(0, min(self.max_voltage, val))
            self.voltage_var.set(round(val, 3))
        else:
            val = max(0, min(self.max_current, val))
            self.current_var.set(round(val, 3))

        self._update_slider_from_value(control)
        if self.auto_apply:
            self._apply_auto(control)


    def _apply_auto(self, control: str):
        try:
            if control=="voltage":
                self.device.set_voltage(self.voltage_var.get())
                self.set_voltage = self.voltage_var.get()
            else:
                self.device.set_current(self.current_var.get())
                self.set_current = self.current_var.get()
        except Exception as e:
            print(f"[ERROR] Auto apply {control}: {e}")

    def apply_settings(self):
        try:
            self.device.set_voltage(self.voltage_var.get())
            self.set_voltage = self.voltage_var.get()
            self.device.set_current(self.current_var.get())
            self.set_current = self.current_var.get()
        except Exception as e:
            print(f"[ERROR] Apply settings failed: {e}")

    def toggle_output(self):
        # Flip the output state manually
        current_state = self.output_state.get()
        new_state = not current_state
        self.output_state.set(new_state)

        # Update button text & color
        if new_state:
            self.output_button.config(text=self.controller.translator.t("button_output_on"), bg="green", fg="white")
            # --- Trigger your actual output ON logic here ---
            print("Output ENABLED")
            self.device.set_output(True)   # example if you have a method
        else:
            self.output_button.config(text=self.controller.translator.t("button_output_off"), bg="red", fg="white")
            # --- Trigger your actual output OFF logic here ---
            print("Output DISABLED")
            self.device.set_output(False)  # example if you have a method


    # ---------------- Auto-Measure ----------------
    def on_new_data(self, v, i, p):
        """Called every time new measurement data is available."""
        self.meas_voltage_var.set(f"{v:.4f} V")
        self.meas_current_var.set(f"{i:.4f} A")
        self.meas_power_var.set(f"{p:.4f} W")
                # Reflect protection status from MeasurementManager
        t = self.controller.translator.t

        if self.mm.protection_tripped:
            self.protection_status_var.set(f"{self.mm.protection_tripped} {t('label_tripped')}")
            self.protection_status_label.config(foreground="orange")
        else:
            self.protection_status_var.set(t("label_safe"))
            self.protection_status_label.config(foreground="green")

        self._update_mode_indicator(v, i)

    # ---------------- CV/CC detection ----------------

    def _update_mode_indicator(self, v_meas, i_meas):
            
        try:
                if not self.output_state.get():  # Output OFF → gray
                    self.mode_label.config(text="Mode: ---", foreground="gray")
                    return

                tolerance = 0.005  # 5 mA / 5 mV tolerance

                # Check CC first
                if v_meas < self.set_voltage - tolerance and abs(i_meas - self.set_current) < tolerance:
                    self.mode_label.config(text="Mode: CC", foreground="red")
                else:
                    # Else CV
                    self.mode_label.config(text="Mode: CV", foreground="blue")

        except Exception as e:
                print(f"[ERROR] Mode detection failed: {e}")    


        # ---------------- Presets ----------------
    def load_presets(self):
            if not os.path.exists(self.presets_file):
                default_data = {
                    "voltage_presets": [3.3,5.0,9.0,12.0,24.0],
                    "current_presets": [0.1,0.5,1.0,2.0,3.0]
                }
                os.makedirs(os.path.dirname(self.presets_file), exist_ok=True)
                with open(self.presets_file,"w") as f:
                    json.dump(default_data, f, indent=4)
                return default_data["voltage_presets"], default_data["current_presets"]
            with open(self.presets_file,"r") as f:
                data = json.load(f)
                return data.get("voltage_presets", []), data.get("current_presets", [])

            # ---------------- Preset handlers ----------------
    def set_voltage_preset(self, value: float):
            self.voltage_var.set(round(value, 3))
            self._update_slider_from_value("voltage")
            if self.auto_apply:
                self._apply_auto("voltage")
            print(f"[Preset] Voltage preset applied: {value:.3f} V")

    def set_current_preset(self, value: float):
            self.current_var.set(round(value, 3))
            self._update_slider_from_value("current")
            if self.auto_apply:
                self._apply_auto("current")
            print(f"[Preset] Current preset applied: {value:.3f} A")

    # ---------------- Presets Management ----------------
    def refresh_presets_buttons(self):
        # Voltage buttons
        for widget in self.voltage_buttons_frame.winfo_children():
            widget.destroy()
        for idx, val in enumerate(self.voltage_presets):
            ttk.Button(self.voltage_buttons_frame, text=f"{val} V", width=6,
                    command=lambda v=val: self.set_voltage_preset(v)).grid(row=idx//3, column=idx%3, padx=2, pady=2)
        # Current buttons
        for widget in self.current_buttons_frame.winfo_children():
            widget.destroy()
        for idx, val in enumerate(self.current_presets):
            ttk.Button(self.current_buttons_frame, text=f"{val} A", width=6,
                    command=lambda a=val: self.set_current_preset(a)).grid(row=idx//3, column=idx%3, padx=2, pady=2)

    def save_presets(self):
        data = {
            "voltage_presets": self.voltage_presets,
            "current_presets": self.current_presets
        }
        with open(self.presets_file, "w") as f:
            json.dump(data, f, indent=4)

    def add_voltage_preset(self):
        try:
            val = float(self.voltage_input_var.get())
            if val not in self.voltage_presets:
                self.voltage_presets.append(val)
                self.voltage_presets.sort()
                self.save_presets()
                self.refresh_presets_buttons()
        except ValueError:
            print("[ERROR] Invalid voltage value")

    def add_current_preset(self):
        try:
            val = float(self.current_input_var.get())
            if val not in self.current_presets:
                self.current_presets.append(val)
                self.current_presets.sort()
                self.save_presets()
                self.refresh_presets_buttons()
        except ValueError:
            print("[ERROR] Invalid current value")

    def delete_voltage_preset(self):
        try:
            val = float(self.voltage_input_var.get())
            if val in self.voltage_presets:
                self.voltage_presets.remove(val)
                self.save_presets()
                self.refresh_presets_buttons()
        except ValueError:
            print("[ERROR] Invalid voltage value")

    def delete_current_preset(self):
        try:
            val = float(self.current_input_var.get())
            if val in self.current_presets:
                self.current_presets.remove(val)
                self.save_presets()
                self.refresh_presets_buttons()
        except ValueError:
            print("[ERROR] Invalid current value")


    def on_show(self):
        """Called by the controller when this page becomes visible."""
        self.is_visible = True

    def on_hide(self):
        """Called by the controller when this page is hidden."""
        self.is_visible = False

    def _update_limits_from_mm(self):
        """Fetch current limits from MeasurementManager."""
        ovp = self.mm.get_ovp()
        ocp = self.mm.get_ocp()
        self.max_voltage = ovp["limit"] if ovp else 30.0
        self.max_current = ocp["limit"] if ocp else 3.0

    def _on_measurement_update(self, voltage, current, power):
        """Callback called on every measurement update."""
        # Refresh limits if they might have changed
        self._update_limits_from_mm()

        # callback function
    def _on_limit_update(self, ovp_limit, ocp_limit):
        self.max_voltage = ovp_limit
        self.max_current = ocp_limit
        # update sliders/entries/digits to respect new limits
        self._update_slider_from_value("voltage")
        self._update_slider_from_value("current")