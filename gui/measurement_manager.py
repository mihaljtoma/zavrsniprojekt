import tkinter as tk

class MeasurementManager:
    def __init__(self, root, device, interval=1000):
        self.root = root
        self.device = device
        self.interval = interval  # ms
        self.subscribers = []                # measurement callbacks
        self.protection_subscribers = []     # protection event callbacks
        self.limit_callbacks = []            # new: callbacks for OVP/OCP changes

        # Latest measurement values
        self.latest_voltage = 0.0
        self.latest_current = 0.0
        self.latest_power = 0.0
        self.running = False
        self._after_id = None  # keep track of scheduled callback

        # --- Protection Settings ---
        self.ovp_enabled = False
        self.ocp_enabled = False
        self.ovp_limit = 30.0
        self.ocp_limit = 3.0
        self.protection_tripped = None  # "OVP", "OCP", or None

    # ---------- Protection Configuration ----------
    def set_ovp(self, enabled: bool, limit: float):
        """Enable/disable and set OVP limit."""
        self.ovp_enabled = enabled
        self.ovp_limit = limit
        self._notify_limit_change()  # notify subscribers

    def set_ocp(self, enabled: bool, limit: float):
        """Enable/disable and set OCP limit."""
        self.ocp_enabled = enabled
        self.ocp_limit = limit
        self._notify_limit_change()  # notify subscribers

    # ---------- Limit Subscription ----------
    def subscribe_limits(self, callback):
        """UI or control page subscribes to OVP/OCP changes."""
        if callback not in self.limit_callbacks:
            self.limit_callbacks.append(callback)

    def _notify_limit_change(self):
        """Notify subscribers of updated OVP/OCP limits."""
        for cb in self.limit_callbacks:
            try:
                cb(self.ovp_limit, self.ocp_limit)
            except Exception as e:
                print(f"[WARN] Limit callback failed: {e}")

    # ---------- Measurement Access ----------
    def get_ovp(self):
        return {"enabled": self.ovp_enabled, "limit": self.ovp_limit}

    def get_ocp(self):
        return {"enabled": self.ocp_enabled, "limit": self.ocp_limit}

    def reset_protection(self):
        self.protection_tripped = None

    # ---------- Measurement Control ----------
    def start(self):
        if not self.running:
            self.running = True
            self._measure()

    def stop(self):
        """Stop measurement loop safely."""
        self.running = False
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception as e:
                print(f"[WARN] Failed to cancel after() callback: {e}")
            self._after_id = None
        print("[INFO] MeasurementManager stopped")

    # ---------- Subscriptions ----------
    def subscribe(self, callback):
        self.subscribers.append(callback)

    def subscribe_protection(self, callback):
        self.protection_subscribers.append(callback)
        
    def subscribe_connection_status(self, callback):
        self._connection_callback = callback
        self._last_connection_state = None  # track last state to avoid spamming

    # ---------- Main Measurement Loop ----------
    def _measure(self):
        if not self.running:
            return

        # --- Check connection state and notify if changed ---
        current_state = self.device.is_connected()
        if hasattr(self, "_connection_callback") and current_state != getattr(self, "_last_connection_state", None):
            try:
                self._connection_callback(current_state)
            except Exception as e:
                print(f"[WARN] Connection callback failed: {e}")
            self._last_connection_state = current_state

        # --- Read measurements ---
        if self.device.is_connected():
            try:
                v = self.device.read_voltage()
                i = self.device.read_current()
                p = self.device.read_power()
            except Exception as e:
                print(f"[WARN] Measurement failed: {e}")
                v, i, p = 0.0, 0.0, 0.0
        else:
            v, i, p = 0.0, 0.0, 0.0

        self.latest_voltage = v
        self.latest_current = i
        self.latest_power = p

        # --- Protection logic ---
        if self.protection_tripped is None:
            if self.ovp_enabled and v > self.ovp_limit:
                self.protection_tripped = "OVP"
                print(f"[PROTECTION] OVP TRIPPED: {v:.3f} V > {self.ovp_limit:.3f} V")
                self._handle_trip()
            elif self.ocp_enabled and i > self.ocp_limit:
                self.protection_tripped = "OCP"
                print(f"[PROTECTION] OCP TRIPPED: {i:.3f} A > {self.ocp_limit:.3f} A")
                self._handle_trip()

        # --- Notify subscribers ---
        for callback in self.subscribers:
            try:
                callback(v, i, p)
            except Exception as e:
                print(f"[WARN] Measurement callback failed: {e}")

        # ✅ Store the after() ID so it can be canceled later
        self._after_id = self.root.after(self.interval, self._measure)

    # ---------- Protection Handling ----------
    def _handle_trip(self):
        try:
            self.device.set_output(False)
        except Exception as e:
            print(f"[ERROR] Could not disable output after protection trip: {e}")

        for callback in self.protection_subscribers:
            try:
                callback(self.protection_tripped)
            except Exception as e:
                print(f"[WARN] Protection callback failed: {e}")
