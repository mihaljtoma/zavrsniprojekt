import tkinter as tk
from tkinter import ttk

STB_BITS = [
    ("Bit 7", "OPE", "Standard Operation Summary"),
    ("Bit 6", "RQS", "Request Service"),
    ("Bit 5", "ESB", "Standard Event Summary"),
    ("Bit 4", "MAV", "Message Available Summary"),
    ("Bit 3", "QUES", "Questionable Data Summary"),
    ("Bit 2", "EQ", "Error Queue"),
    ("Bit 1", "Not Used", ""),
    ("Bit 0", "Not Used", "")
]

ESR_BITS = [
    ("Bit 7", "PON", "Power On"),
    ("Bit 6", "Not used", ""),
    ("Bit 5", "CME", "Command Error"),
    ("Bit 4", "EXE", "Execution Error"),
    ("Bit 3", "DOE", "Device-Specific Error"),
    ("Bit 2", "QYE", "Query Error"),
    ("Bit 1", "Not Used", ""),
    ("Bit 0", "OPC", "Operation Complete")
]

class StatusPage(tk.Frame):
    def __init__(self, parent, controller, device=None, mm=None):
        super().__init__(parent)
        self.controller = controller
        self.device = device

        # --- STB Table ---
        stb_frame = ttk.LabelFrame(self, text="STB Status")
        stb_frame.pack(padx=10, pady=5, fill="x")
        self.stb_tree = ttk.Treeview(stb_frame, columns=("Bit", "Name", "Description", "Status"), show="headings", height=8)
        for col in ("Bit", "Name", "Description", "Status"):
            self.stb_tree.heading(col, text=col)
            self.stb_tree.column(col, width=150)
        self.stb_tree.pack(padx=5, pady=5)
        self.stb_items = []
        for bit in STB_BITS:
            item_id = self.stb_tree.insert("", "end", values=(bit[0], bit[1], bit[2], "OFF"))
            self.stb_items.append(item_id)

        # --- ESR Table ---
        esr_frame = ttk.LabelFrame(self, text="ESR Status")
        esr_frame.pack(padx=10, pady=5, fill="x")
        self.esr_tree = ttk.Treeview(esr_frame, columns=("Bit", "Name", "Description", "Status"), show="headings", height=8)
        for col in ("Bit", "Name", "Description", "Status"):
            self.esr_tree.heading(col, text=col)
            self.esr_tree.column(col, width=150)
        self.esr_tree.pack(padx=5, pady=5)
        self.esr_items = []
        for bit in ESR_BITS:
            item_id = self.esr_tree.insert("", "end", values=(bit[0], bit[1], bit[2], "OFF"))
            self.esr_items.append(item_id)

        # --- Buttons Row Frame ---
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=10)

        refresh_btn = ttk.Button(buttons_frame, text="", command=self.refresh_status)
        refresh_btn.trans_key = "button_refresh_status"
        refresh_btn.pack(side="left", padx=5)

        clear_btn = ttk.Button(buttons_frame, text="", command=self.clear_device)
        clear_btn.trans_key = "button_clear_device"
        clear_btn.pack(side="left", padx=5)

        test_btn = ttk.Button(buttons_frame, text="", command=self.open_test_popup)
        test_btn.trans_key = "button_test_page"
        test_btn.pack(side="left", padx=5)

        # Init with simulated values
        self.refresh_status(simulate=True)

    # --- Bit parsing ---
    def parse_bits(self, value, bits):
        tmp_value = value
        status = []
        for bit in bits:
            power = 2 ** int(bit[0].split()[1])
            bit_set, tmp_value = divmod(tmp_value, power)
            status.append((bit[0], bit[1], bit[2], bool(bit_set)))
        return status

    def update_table(self, tree, status_list, item_ids):
        for item_id, (_, _, _, bit_set) in zip(item_ids, status_list):
            tree.set(item_id, "Status", "ON" if bit_set else "OFF")
            tree.item(item_id, tags=("alert" if bit_set else "normal",))
        tree.tag_configure("alert", background="red")
        tree.tag_configure("normal", background="green")

    # --- Refresh handler ---
    def refresh_status(self, simulate=False):
        if simulate or self.device is None or not getattr(self.device, "is_connected", lambda: False)():
            # simulated example
            stb_value = 0b10101010
            esr_value = 0b01010101
        else:
            stb_value = int(self.device.query("*STB?"))
            esr_value = int(self.device.query("*ESR?"))

        self.update_table(self.stb_tree, self.parse_bits(stb_value, STB_BITS), self.stb_items)
        self.update_table(self.esr_tree, self.parse_bits(esr_value, ESR_BITS), self.esr_items)

    # --- Clear / Reset handlers ---
    def clear_device(self):
        if self.device is not None and getattr(self.device, "is_connected", lambda: False)():
            try:
                self.device.clear()  # šalje *CLS uređaju
                print("Device cleared (*CLS).")
            except Exception as e:
                print("Error clearing device:", e)
        else:
            print("Simulating device clear...")
        
        # Osvježavamo STB/ESR tablice nakon clear
        self.refresh_status(simulate=self.device is None or not getattr(self.device, "is_connected", lambda: False)())

   
    # --- Test Page ---
    def open_test_popup(self):
        popup = tk.Toplevel(self)
        popup.title("SCPI Command Test")
        popup.geometry("400x300")
        popup.transient(self)

        # --- SCPI Commands Dropdown ---
        cmd_frame = ttk.LabelFrame(popup, text="Select SCPI Command", padding=10)
        cmd_frame.pack(fill="x", padx=10, pady=10)

        commands = [
            "*IDN?",       # Standard Device ID query
            ":VOLT 5",     # Set voltage to 5V
            ":CURR 1",     # Set current to 1A
            ":MEAS:VOLT?", # Measure voltage
            ":FAKE?"       # Non-existent command to test error response
        ]

        self.selected_cmd = tk.StringVar(value=commands[0])
        cmd_dropdown = ttk.OptionMenu(cmd_frame, self.selected_cmd, commands[0], *commands)
        cmd_dropdown.pack(side="left", padx=5)

        # --- Send Button ---
        send_btn = ttk.Button(cmd_frame, text="Send Command", command=self.send_test_command)
        send_btn.pack(side="left", padx=5)

        # --- Feedback Label ---
        self.cmd_feedback = tk.Label(popup, text="", fg="blue")
        self.cmd_feedback.pack(pady=10)

    def send_test_command(self):
        cmd = self.selected_cmd.get()
        self.cmd_feedback.config(text=f"Sending: {cmd}")
        print(f"Sending command: {cmd}")

        if self.device is not None and getattr(self.device, "is_connected", lambda: False)():
            try:
                resp = self.device.query(cmd)  # šalje komandu uređaju
                self.cmd_feedback.config(text=f"Response: {resp}")
            except Exception as e:
                self.cmd_feedback.config(text=f"Device Error: {e}")
                print(f"Device responded with error: {e}")

            # Nakon svake komande, osvježavamo STB/ESR tabele sa stvarnim vrijednostima
            stb_value = int(self.device.query("*STB?"))
            esr_value = int(self.device.query("*ESR?"))
        else:
            # Ako uređaj nije spojen, simuliramo STB/ESR vrijednosti za test
            import random
            stb_value = random.randint(0, 255)
            esr_value = random.randint(0, 255)
            self.cmd_feedback.config(text=f"Simulated STB/ESR updated")
            print(f"Simulated STB: {stb_value}, ESR: {esr_value}")

        self.update_table(self.stb_tree, self.parse_bits(stb_value, STB_BITS), self.stb_items)
        self.update_table(self.esr_tree, self.parse_bits(esr_value, ESR_BITS), self.esr_items)

