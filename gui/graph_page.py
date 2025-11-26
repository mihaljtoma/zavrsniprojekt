# graph_page.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import time
import os
from collections import deque
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GraphPage(ttk.Frame):
    

    def __init__(self, parent, controller, device, mm,
                 max_points=10000, draw_interval=20):
       
        super().__init__(parent)
        self.controller = controller
        self.device = device
        self.mm = mm

        # subscribe to measurement manager callbacks
        # measurement callback signature expected: callback(v, i, p)
        self.mm.subscribe(self.on_new_data)

        # runtime flags
        self.running = False
        self.paused = False
        self.combined = True

        # storage (bounded)
        self.max_points = max_points
        self.time_data = deque(maxlen=self.max_points)     # integer seconds
        self.voltage_data = deque(maxlen=self.max_points)
        self.current_data = deque(maxlen=self.max_points)
        self.power_data = deque(maxlen=self.max_points)

        # start / timing
        self.start_time = None   # wall-clock time when graph started
        self.start_timestamp = None  # base timestamp used to compute HH:MM:SS (same as start_time)
        self.draw_interval = draw_interval  # seconds between heavy redraws
        self._last_full_redraw = 0.0

        # protection thresholds / previous values
        self.voltage_limit = 26.5
        self.current_limit = 2.0
        self.prev_voltage = None
        self.prev_current = None

        # CSV logging
        self.live_file = None
        self.live_writer = None

        # scaling
        self.auto_scale_var = tk.BooleanVar(value=True)
        self.manual_scale = None  # dict with "v","i","p" tuples

        # matplotlib figure and initial lines
        self.fig, self.ax1 = plt.subplots()
        # create Line2D objects and keep them (fast updates via set_data)
        self.voltage_line, = self.ax1.plot([], [], label="Voltage (V)")
        self.current_line, = self.ax1.plot([], [], label="Current (A)")

        # placeholders for separate-view axes & lines
        self.sep_axes_created = False
        self.ax_voltage = None
        self.ax_current = None
        self.ax_power = None
        self.vol_line_sep = None
        self.cur_line_sep = None
        self.pow_line_sep = None

        # build UI
        self.build_ui()
        self.update_text_labels(0.0, 0.0, 0.0)

    # ------------------ UI ------------------
    def build_ui(self):
        # top controls
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=8, pady=6)

        self.start_btn = ttk.Button(top_frame, text="", command=self.toggle_graph)
        self.start_btn.trans_key = "button_start_graph"
        self.start_btn.pack(side="left", padx=4)

        self.pause_btn = ttk.Button(top_frame, text="", command=self.toggle_pause, state="disabled")
        self.pause_btn.trans_key = "button_pause_graph"
        self.pause_btn.pack(side="left", padx=4)

        self.reset_btn = ttk.Button(top_frame, text="", command=lambda: self.reset_graph(True), state="disabled")
        self.reset_btn.trans_key = "button_reset_graph"
        self.reset_btn.pack(side="left", padx=4)

        self.export_btn = ttk.Button(top_frame, text="", command=self.export_csv, state="disabled")
        self.export_btn.trans_key = "button_export_csv"
        # self.export_btn.pack(side="left", padx=4)

        self.view_btn = ttk.Button(top_frame, text="", command=self.toggle_view)
        self.view_btn.trans_key = "button_toggle_view"
        self.view_btn.pack(side="left", padx=8)

        time_label = ttk.Label(top_frame, text="")
        time_label.trans_key = "label_time_window"
        time_label.pack(side="left", padx=(12,4))

        self.time_window_cb = ttk.Combobox(top_frame, values=["All", "10", "30", "60"], width=5, state="readonly")
        self.time_window_cb.set("All")
        self.time_window_cb.pack(side="left", padx=(0,10))
        self.time_window_cb.bind("<<ComboboxSelected>>", lambda e: self.force_full_redraw())

        self.import_btn = ttk.Button(top_frame, text="", command=self.import_csv)
        self.import_btn.trans_key = "button_import_csv"
        self.import_btn.pack(side="left", padx=4)

        # protection label
        self.protection_status_var = tk.StringVar(value="SAFE")
        self.protection_status_label = ttk.Label(self, textvariable=self.protection_status_var, font=("Arial", 14, "bold"))
        self.protection_status_label.trans_key = "label_protection_status_value"
        self.protection_status_label.pack(pady=4)

        # live stats frame
        live_frame = ttk.LabelFrame(self, text="")
        live_frame.trans_key = "label_live_stats"
        live_frame.pack(fill="x", padx=8, pady=6)


        row1 = ttk.Frame(live_frame)
        row1.pack(fill="x", padx=6, pady=2)
        self.voltage_label = ttk.Label(row1, text="", font=("Helvetica", 11, "bold"))
        self.voltage_label.trans_key = "label_voltage_measure"
        self.voltage_label.pack(side="left", padx=8)

        self.current_label = ttk.Label(row1, text="", font=("Helvetica", 11, "bold"))
        self.current_label.trans_key = "label_current_measure"
        self.current_label.pack(side="left", padx=8)

        self.power_label = ttk.Label(row1, text="", font=("Helvetica", 11, "bold"))
        self.power_label.trans_key = "label_power_measure"
        self.power_label.pack(side="left", padx=8)


        row2 = ttk.Frame(live_frame)
        row2.pack(fill="x", padx=6, pady=2)
        self.delta_label = ttk.Label(row2, text="ΔV: -- V   ΔI: -- A", font=("Helvetica", 9, "italic"))
        self.delta_label.pack(side="left", padx=8)

        # stats area
        stats_frame = ttk.LabelFrame(self, text="")
        stats_frame.trans_key = "label_statistics"
        stats_frame.pack(fill="x", padx=8, pady=6)

        self.stats_label = ttk.Label(stats_frame, text="")
        self.stats_label.trans_key = "label_stats_values"
        self.stats_label.pack(padx=8, pady=4)

        scale_frame = ttk.Frame(self)
        scale_frame.pack(side="left", fill="y", padx=8, pady=6)

        def add_entry(frame, trans_key):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=6)
            lbl = ttk.Label(row, text="")
            lbl.trans_key = trans_key
            lbl.config(width=8, anchor="w")
            lbl.pack(side="left")
            entry = ttk.Entry(row, width=6)
            entry.pack(side="left", padx=(4,0))
            return entry

        self.v_min_entry = add_entry(scale_frame, "label_v_min")
        self.v_max_entry = add_entry(scale_frame, "label_v_max")
        self.i_min_entry = add_entry(scale_frame, "label_i_min")
        self.i_max_entry = add_entry(scale_frame, "label_i_max")
        self.p_min_entry = add_entry(scale_frame, "label_p_min")
        self.p_max_entry = add_entry(scale_frame, "label_p_max")

        # Button at bottom
        self.scale_btn = ttk.Button(scale_frame, text="", command=self.apply_manual_scale)
        self.scale_btn.trans_key = "button_apply_scale"
        self.scale_btn.pack(pady=(20,0))

        # autoscale checkbox
        self.auto_scale_cb = ttk.Checkbutton(scale_frame, text="", variable=self.auto_scale_var,
                                            command=lambda: self.force_full_redraw())
        self.auto_scale_cb.trans_key = "checkbox_auto_scale"
        self.auto_scale_cb.pack(pady=(20, 0))

        # matplotlib canvas labels
        self.ax1.set_title("")
        self.ax1.trans_title_key = "graph_title"
        self.ax1.set_xlabel("")
        self.ax1.trans_xlabel_key = "graph_xlabel"
        self.ax1.set_ylabel("")
        self.ax1.trans_ylabel_key = "graph_ylabel"
        self.ax1.grid(True)
        self.ax1.legend()


        # --- Matplotlib canvas next to it ---
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------ controls ------------------
    def toggle_graph(self):
        if not self.running:
            self.reset_graph(False)

            # start logging/plotting
            self.running = True
            self.paused = False
            self.start_btn.trans_key = "button_stop_graph"
            # Update the text via translator
            self.start_btn.config(text=self.controller.translator.t(self.start_btn.trans_key))
            self.pause_btn.config(state="normal", text="⏸ Pause")
            self.reset_btn.config(state="normal")
            self.export_btn.config(state="normal")
            # initialize time base
            self.start_time = time.time()
            self.start_timestamp = self.start_time
            self._last_full_redraw = self.start_time
            # Ask user where to save live csv (optional)
            default_name = time.strftime("graph_data_%Y%m%d_%H%M%S.csv")
            file_path = filedialog.asksaveasfilename(
                title="Save Live CSV Data As",
                defaultextension=".csv",
                initialfile=default_name,
                filetypes=[("CSV files", "*.csv")]
            )
            if not file_path:
                file_path = default_name
            try:
                self.live_file = open(file_path, mode='w', newline='')
                self.live_writer = csv.writer(self.live_file)
                # header with HH:MM:SS times
                self.live_writer.writerow(["Time (HH:MM:SS)", "Voltage (V)", "Current (A)", "Power (W)"])
                if self.live_file:
                    print(f"[INFO] Live CSV logging to: {os.path.abspath(file_path)}")
            except Exception as e:
                messagebox.showerror("File Error", f"Could not create log file:\n{e}")
                self.live_file = None
                self.live_writer = None
            self.toggle_view()
            self.toggle_view()
        else:
            # stop
            self.running = False
            
            self.start_btn.trans_key = "button_start_graph"
            self.start_btn.config(text=self.controller.translator.t(self.start_btn.trans_key))
            self.pause_btn.trans_key = "button_pause_graph"
            self.pause_btn.config(state="disabled", text=self.controller.translator.t(self.pause_btn.trans_key))
            self.reset_btn.config(state="normal")
            self.export_btn.config(state="normal" if len(self.time_data) else "disabled")
            if self.live_file:
                try:
                    self.live_file.close()
                except Exception:
                    pass
                self.live_file = None
                self.live_writer = None
                print("[INFO] Live CSV logging stopped.")

    def toggle_pause(self):
        if self.paused:
            self.paused = False
            self.pause_btn.config(text=self.controller.translator.t("button_pause_graph"))
        else:
            self.paused = True
            self.pause_btn.config(text=self.controller.translator.t("button_resume_graph"))

    def toggle_view(self):
        self.combined = not self.combined
        view_text_key = "label_view_combined" if self.combined else "label_view_separate"
        view_text = self.controller.translator.t(view_text_key)
        self.view_btn.config(text=f"🔁 {self.controller.translator.t('button_toggle_view')} ({view_text})")
        self.force_full_redraw()


    # ------------------ data update ------------------
    def on_new_data(self, v, i, p):
        """Append new measurement points every second and update the graph."""
        # Update live text labels
        self.update_text_labels(v, i, p)

        if not self.running or self.paused:
            return

        # Initialize start time and last full redraw
        if self.start_time is None:
            self.start_time = time.time()
            self.start_timestamp = self.start_time
            self._last_full_redraw = self.start_time
            self.draw_interval = 20  # seconds

        # --- Timestamp (integer seconds) ---
        ts = int(time.time() - self.start_time)

        # Append new data
        self.time_data.append(ts)
        self.voltage_data.append(v)
        self.current_data.append(i)
        self.power_data.append(p)

        if self.mm.protection_tripped:
            self.protection_status_var.set(
                f"{self.mm.protection_tripped} {self.controller.translator.t('label_tripped')}"
            )
            self.protection_status_label.config(foreground="orange")
        else:
            self.protection_status_var.set(self.controller.translator.t("label_safe"))
            self.protection_status_label.config(foreground="green")


        # --- CSV logging ---
        if self.live_writer:
            try:
                hh = ts // 3600
                mm = (ts % 3600) // 60
                ss = ts % 60
                hhmmss = f"{hh:02}:{mm:02}:{ss:02}"
                self.live_writer.writerow([hhmmss, f"{v:.6f}", f"{i:.6f}", f"{p:.6f}"])
                self.live_file.flush()
            except Exception:
                pass

        # --- Lightweight append update (lines only) ---
        if self.combined:
            self.voltage_line.set_data(self.time_data, self.voltage_data)
            self.current_line.set_data(self.time_data, self.current_data)
            self._update_axes_limits(ts, v, i)
        else:
            # Ensure separate lines exist
            if not hasattr(self, "vol_line_sep"):
                self.vol_line_sep, = self.ax_voltage.plot([], [], color="blue")
                self.cur_line_sep, = self.ax_current.plot([], [], color="orange")
                self.pow_line_sep, = self.ax_power.plot([], [], color="green")

            self.vol_line_sep.set_data(self.time_data, self.voltage_data)
            self.cur_line_sep.set_data(self.time_data, self.current_data)
            self.pow_line_sep.set_data(self.time_data, self.power_data)
            self._update_axes_limits(ts, v, i)

        self.canvas.draw_idle()

        # --- Full redraw every 20 seconds ---
        now = time.time()
        if now - self._last_full_redraw >= self.draw_interval:
            self.redraw(full=True)
            self._last_full_redraw = now


    # ------------------ axes / view helpers ------------------
    def _create_separate_axes(self):
        """Create 3 subplots for separate view. Called once lazily."""
        self.fig.clf()
        self.ax_voltage = self.fig.add_subplot(311)
        self.ax_current = self.fig.add_subplot(312, sharex=self.ax_voltage)
        self.ax_power = self.fig.add_subplot(313, sharex=self.ax_voltage)

        # Translated labels
        t = self.controller.translator.t
        self.vol_line_sep, = self.ax_voltage.plot([], [], label=f"{t('label_voltage')} (V)")
        self.cur_line_sep, = self.ax_current.plot([], [], label=f"{t('label_current')} (A)")
        self.pow_line_sep, = self.ax_power.plot([], [], label=f"{t('label_power')} (W)")

        self.ax_voltage.set_ylabel(f"{t('label_voltage')} (V)")
        self.ax_current.set_ylabel(f"{t('label_current')} (A)")
        self.ax_power.set_ylabel(f"{t('label_power')} (W)")
        self.ax_power.set_xlabel(t("label_time_axis"))

        self.fig.subplots_adjust(hspace=0.5)
        self.sep_axes_created = True

        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    def _recreate_combined_axes(self):
        """Recreate single combined axis after being in separate view."""
        self.fig.clf()
        self.ax1 = self.fig.add_subplot(111)

        t = self.controller.translator.t
        self.voltage_line, = self.ax1.plot([], [], label=f"{t('label_voltage')} (V)")
        self.current_line, = self.ax1.plot([], [], label=f"{t('label_current')} (A)")

        self.ax1.set_xlabel(t("label_time_axis"))
        self.ax1.set_ylabel(t("label_value_axis"))
        self.ax1.set_title(t("label_graph_title"))
        self.ax1.grid(True)
        self.ax1.legend()
        self.sep_axes_created = False

        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    def force_full_redraw(self):
        """Force immediate full redraw (used when user changes time window or view)."""
        self._last_full_redraw = 0.0
        self.redraw(full=True)
        self._last_full_redraw = time.time()

    def redraw(self, full=False):
        """
        Full/partial redraw. When full=True (or called by timer), we:
          - apply time window (All/10/30/60) to determine t_plot slice
          - compute ~5-6 evenly spaced tick positions and HH:MM:SS labels
          - apply manual scale if requested (manual True usually passed)
        If full=False, function can be used to lightly refresh layout (not used heavily here).
        """
        if not self.time_data:
            return

        # read full lists
        t_list = list(self.time_data)
        v_list = list(self.voltage_data)
        c_list = list(self.current_data)
        p_list = list(self.power_data)

        # determine time window selection
        tw = self.time_window_cb.get()
        if tw != "All":
            try:
                window = int(float(tw))
                # show last 'window' seconds
                t_max = t_list[-1]
                t_min = t_max - window
                # find first index >= t_min
                start_idx = 0
                for idx, t in enumerate(t_list):
                    if t >= t_min:
                        start_idx = idx
                        break
                t_plot = t_list[start_idx:]
                v_plot = v_list[start_idx:]
                c_plot = c_list[start_idx:]
                p_plot = p_list[start_idx:]
            except Exception:
                t_plot, v_plot, c_plot, p_plot = t_list, v_list, c_list, p_list
        else:
            t_plot, v_plot, c_plot, p_plot = t_list, v_list, c_list, p_list

        if not t_plot:
            return

        # choose tick positions ~5-6 ticks evenly spaced across t_plot
        n_ticks = min(6, max(2, len(t_plot)))
        tick_indices = [int(round(i * (len(t_plot) - 1) / (n_ticks - 1))) for i in range(n_ticks)]
        tick_values = [t_plot[i] for i in tick_indices]
        tick_labels = [self._seconds_to_hhmmss(tv) for tv in tick_values]

        if self.combined:
            # if needed recreate axes
            if self.sep_axes_created:
                self._recreate_combined_axes()

            # set data
            self.voltage_line.set_data(t_plot, v_plot)
            self.current_line.set_data(t_plot, c_plot)

            # labels, ticks
            t = self.controller.translator.t
            self.ax1.set_title(t("label_graph_title"))
            self.ax1.set_xlabel(t("label_time_axis"))
            self.ax1.set_ylabel(t("label_value_axis"))
            self.ax1.grid(True)
            self.ax1.legend()

            # x-limits: show exactly the time window (or full range)
            self.ax1.set_xlim(min(t_plot), max(t_plot))

            # xticks / labels
            try:
                self.ax1.set_xticks(tick_values)
                self.ax1.set_xticklabels(tick_labels, rotation=0)
            except Exception:
                pass

            # apply scale: manual/auto
            if not self.auto_scale_var.get() and self.manual_scale:
                # for combined view, choose y-limits that include both V and I ranges requested
                vmin, vmax = self.manual_scale["v"]
                imin, imax = self.manual_scale["i"]
                ymin = min(vmin, imin)
                ymax = max(vmax, imax)
                try:
                    self.ax1.set_ylim(ymin, ymax)
                except Exception:
                    pass
            elif self.auto_scale_var.get():
                # autoscale based on data in view
                y_all = v_plot + c_plot if (v_plot and c_plot) else v_plot or c_plot
                if y_all:
                    ymin, ymax = min(y_all), max(y_all)
                    pad = (ymax - ymin) * 0.05 if ymax != ymin else 0.5
                    try:
                        self.ax1.set_ylim(ymin - pad, ymax + pad)
                    except Exception:
                        pass
        else:
            # separate axes
            if not self.sep_axes_created:
                self._create_separate_axes()

            self.vol_line_sep.set_data(t_plot, v_plot)
            self.cur_line_sep.set_data(t_plot, c_plot)
            self.pow_line_sep.set_data(t_plot, p_plot)

            # set x-limits and ticks for each subplot
            try:
                for ax in (self.ax_voltage, self.ax_current, self.ax_power):
                    ax.set_xlim(min(t_plot), max(t_plot))
                    ax.set_xticks(tick_values)
                    ax.set_xticklabels(tick_labels, rotation=0)
            except Exception:
                pass

            # apply scales
            if not self.auto_scale_var.get() and self.manual_scale:
                try:
                    self.ax_voltage.set_ylim(*self.manual_scale["v"])
                    self.ax_current.set_ylim(*self.manual_scale["i"])
                    self.ax_power.set_ylim(*self.manual_scale["p"])
                except Exception:
                    pass
            elif self.auto_scale_var.get():
                # autoscale each axis to its plotted data
                if v_plot:
                    ymin, ymax = min(v_plot), max(v_plot)
                    pad = (ymax - ymin) * 0.05 if ymax != ymin else 0.5
                    try:
                        self.ax_voltage.set_ylim(ymin - pad, ymax + pad)
                    except Exception:
                        pass
                if c_plot:
                    ymin, ymax = min(c_plot), max(c_plot)
                    pad = (ymax - ymin) * 0.05 if ymax != ymin else 0.5
                    try:
                        self.ax_current.set_ylim(ymin - pad, ymax + pad)
                    except Exception:
                        pass
                if p_plot:
                    ymin, ymax = min(p_plot), max(p_plot)
                    pad = (ymax - ymin) * 0.05 if ymax != ymin else 0.5
                    try:
                        self.ax_power.set_ylim(ymin - pad, ymax + pad)
                    except Exception:
                        pass

        # update statistics label
        try:
            vmin = min(v_list) if v_list else 0
            vmax = max(v_list) if v_list else 0
            vavg = sum(v_list) / len(v_list) if v_list else 0
            imin = min(c_list) if c_list else 0
            imax = max(c_list) if c_list else 0
            iavg = sum(c_list) / len(c_list) if c_list else 0
            t = self.controller.translator.t
            self.stats_label.config(
                text=(
                    f"{t('label_voltage')} - {t('label_min')}: {vmin:.4g} V | "
                    f"{t('label_max')}: {vmax:.4g} V | "
                    f"{t('label_avg')}: {vavg:.4g} V    ||    "
                    f"{t('label_current')} - {t('label_min')}: {imin:.4g} A | "
                    f"{t('label_max')}: {imax:.4g} A | "
                    f"{t('label_avg')}: {iavg:.4g} A"
                )
            )
        except Exception:
            pass

        # final draw
        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    # ------------------ utility / export / scale ------------------
    def _seconds_to_hhmmss(self, seconds_int):
        """Convert integer seconds to HH:MM:SS string (zero-padded)."""
        s = int(seconds_int)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"

    from tkinter import messagebox

    def reset_graph(self,option):
        """Clear data but keep start_time as new baseline, after confirmation."""
        if option:
            # Ask user for confirmation
            confirm = messagebox.askyesno(
            self.controller.translator.t("msg_confirm_reset_title"),
            self.controller.translator.t("msg_confirm_reset_body")
        )

            if not confirm:
                return  # User cancelled, do nothing

        # --- Clear data ---
        self.time_data.clear()
        self.voltage_data.clear()
        self.current_data.clear()
        self.power_data.clear()
        self.start_time = time.time()
        self.start_timestamp = self.start_time
        self._last_full_redraw = self.start_time

        # --- Clear axes and redraw empty plot ---
        if self.sep_axes_created:
            self._recreate_combined_axes()
        else:
            try:
                self.ax1.cla()
                t = self.controller.translator.t
                self.ax1.set_title(t("label_graph_title"))
                self.ax1.set_xlabel(t("label_time_axis"))
                self.ax1.set_ylabel(t("label_value_axis"))
                self.ax1.grid(True)
                self.ax1.legend()
            except Exception:
                pass

        self.canvas.draw_idle()
        self.update_text_labels(0.0, 0.0, 0.0)


    def export_csv(self):
        """Export stored data to CSV using HH:MM:SS for time column (relative)."""
        if not self.time_data:
            messagebox.showinfo(
                self.controller.translator.t("msg_no_data_title"),
                self.controller.translator.t("msg_no_data_body")
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title=self.controller.translator.t("dialog_save_csv_title"))
        if not file_path:
            return
        try:
            with open(file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time (HH:MM:SS)", "Time (s)", "Voltage (V)", "Current (A)", "Power (W)"])
                for t, v, c, p in zip(self.time_data, self.voltage_data, self.current_data, self.power_data):
                    hh = self._seconds_to_hhmmss(t)
                    writer.writerow([hh, str(int(t)), f"{v:.6f}", f"{c:.6f}", f"{p:.6f}"])
            messagebox.showinfo(
                self.controller.translator.t("msg_export_success_title"),
                f"{self.controller.translator.t('msg_export_success_body')}\n{file_path}"
            )
        except Exception as e:
            messagebox.showerror(
                self.translator.t("msg_export_failed_title"),
                f"{self.controller.translator.t('msg_export_failed_body')}\n{e}"
            )

    def apply_manual_scale(self):
        """Read numeric inputs and apply as manual scales (and disable autoscale)."""
        try:
            v_min = float(self.v_min_entry.get())
            v_max = float(self.v_max_entry.get())
            i_min = float(self.i_min_entry.get())
            i_max = float(self.i_max_entry.get())
            p_min = float(self.p_min_entry.get())
            p_max = float(self.p_max_entry.get())
        except Exception:
            messagebox.showerror(
                self.controller.translator.t("msg_error_title"),
                self.controller.translator.t("msg_invalid_minmax")
            )
            return

        self.manual_scale = {
            "v": (v_min, v_max),
            "i": (i_min, i_max),
            "p": (p_min, p_max)
        }
        # disable autoscale and force immediate full redraw to apply manual scales
        self.auto_scale_var.set(False)
        self.force_full_redraw()

    def update_text_labels(self, voltage, current, power):
        """Update main numeric labels and delta labels."""
        try:
            self.voltage_label.config(text=f"{self.controller.translator.t('label_voltage')}: {voltage:.5g} V")
            self.current_label.config(text=f"{self.controller.translator.t('label_current')}: {current:.5g} A")
            self.power_label.config(text=f"{self.controller.translator.t('label_power')}: {power:.5g} W")
            if self.prev_voltage is not None and self.prev_current is not None:
                delta_v = voltage - self.prev_voltage
                delta_c = current - self.prev_current
                sign_v = "+" if delta_v >= 0 else "-"
                sign_c = "+" if delta_c >= 0 else "-"
                self.delta_label.config(
                    text=f"ΔV: {sign_v}{abs(delta_v):.5g} V   ΔI: {sign_c}{abs(delta_c):.5g} A"
                )
            else:
                self.delta_label.config(text="ΔV: -- V   ΔI: -- A")
            self.prev_voltage = voltage
            self.prev_current = current
        except Exception:
            pass

    def flash_alert(self):
        """Flash labels briefly on protection/limit exceed."""
        try:
            self.voltage_label.config(foreground="red")
            self.current_label.config(foreground="red")
            self.after(1000, lambda: self.voltage_label.config(foreground="black"))
            self.after(1000, lambda: self.current_label.config(foreground="black"))
        except Exception:
            pass

    def _update_axes_limits(self, x, y_v, y_c):
        """Incrementally expand axes limits so new points appear immediately."""
        if self.combined:
            # X-axis
            xmin, xmax = self.ax1.get_xlim()
            if x > xmax:
                self.ax1.set_xlim(xmin, x + 1)
            # Y-axis auto-scale
            if self.auto_scale_var.get():
                ymin, ymax = self.ax1.get_ylim()
                new_min = min(ymin, y_v, y_c)
                new_max = max(ymax, y_v, y_c)
                self.ax1.set_ylim(new_min, new_max)
        else:
            for ax_, y in zip([self.ax_voltage, self.ax_current, self.ax_power],
                            [y_v, y_c, y_v*y_c]):
                xmin, xmax = ax_.get_xlim()
                if x > xmax:
                    ax_.set_xlim(xmin, x + 1)
                if self.auto_scale_var.get():
                    ymin, ymax = ax_.get_ylim()
                    new_min = min(ymin, y)
                    new_max = max(ymax, y)
                    ax_.set_ylim(new_min, new_max)


    def import_csv(self):
        """Import a CSV file and plot its data on the graph."""
        file_path = filedialog.askopenfilename(
            title=self.controller.translator.t("dialog_open_csv_title"),
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return

        try:
            time_list, voltage_list, current_list, power_list = [], [], [], []
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Expect columns: Time (HH:MM:SS), Voltage (V), Current (A), Power (W)
                    hh, mm, ss = map(int, row["Time (HH:MM:SS)"].split(":"))
                    seconds = hh*3600 + mm*60 + ss
                    time_list.append(seconds)
                    voltage_list.append(float(row["Voltage (V)"]))
                    current_list.append(float(row["Current (A)"]))
                    power_list.append(float(row["Power (W)"]))

            # Replace current graph data
            self.time_data = deque(time_list, maxlen=self.max_points)
            self.voltage_data = deque(voltage_list, maxlen=self.max_points)
            self.current_data = deque(current_list, maxlen=self.max_points)
            self.power_data = deque(power_list, maxlen=self.max_points)

            # Force redraw
            self.force_full_redraw()
       
            messagebox.showinfo(
                self.controller.translator.t("msg_import_success_title"),
                f"{self.controller.translator.t('msg_import_success_body')}\n{file_path}"
            )
        except Exception as e:
            messagebox.showerror(
                self.controller.translator.t("msg_import_failed_title"),
                f"{self.controller.translator.t('msg_import_failed_body')}\n{e}"
            )
