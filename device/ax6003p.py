import pyvisa
import time

class AX6003PDevice:
    def __init__(
        self, 
        address='ASRL/dev/ttyUSB0::INSTR', 
        baud_rate=19200, 
        timeout=5000, 
        parity='NONE', 
        stop_bits=1, 
        data_bits=8
    ):
        self.address = address
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.parity = parity
        self.stop_bits = stop_bits
        self.data_bits = data_bits
        self.instrument = None
        self.connected = False
        self._connect()

    def _connect(self):
        """Internal: create or re-create the instrument connection."""
        try:
            self.rm = pyvisa.ResourceManager()
            time.sleep(0.1)
            self.instrument = self.rm.open_resource(self.address)
            self.instrument.baud_rate = self.baud_rate
            self.instrument.timeout = self.timeout
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'

            # ✅ Serial-specific settings
            if self.address.startswith("ASRL") or "tty" in self.address:
                # Parity
                parity_map = {"NONE": 0, "ODD": 1, "EVEN": 2, "MARK": 3, "SPACE": 4}
                self.instrument.parity = parity_map.get(self.parity.upper(), 0)

                # Stop bits (1, 1.5, or 2)
                self.instrument.stop_bits = float(self.stop_bits)

                # Data bits (typically 7 or 8)
                self.instrument.data_bits = int(self.data_bits)

            self.connected = True
        except Exception as e:
            self.instrument = None
            self.connected = False
            print(f"[WARN] Could not connect to device at {self.address}: {e}")

    def apply_connection(self, address=None, baud_rate=None, timeout=None, parity=None, stop_bits=None, data_bits=None):
        """Update connection settings dynamically."""
        if address: self.address = address
        if baud_rate: self.baud_rate = baud_rate
        if timeout: self.timeout = timeout
        if parity: self.parity = parity
        if stop_bits: self.stop_bits = stop_bits
        if data_bits: self.data_bits = data_bits

        try:
            if self.instrument:
                self.instrument.close()
        except Exception:
            pass
        self._connect()

    # ------------------- Utility -------------------
    def is_connected(self):
        """Try *IDN? to verify the device is responsive."""
        if not self.instrument:
            return False
        try:
            _ = self.get_id()
            self.connected = True
            return True
        except Exception:
            self.connected = False
            return False

    # ------------------- Core I/O -------------------
    def query(self, cmd):
        if not self.instrument:
            raise RuntimeError("Device not connected.")
        try:
            return self.instrument.query(cmd)
        except Exception as e:
            raise RuntimeError(f"Query failed: {cmd} — {e}")

    def write(self, cmd):
        if not self.instrument:
            raise RuntimeError("Device not connected.")
        try:
            self.instrument.write(cmd)
        except Exception as e:
            raise RuntimeError(f"Write failed: {cmd} — {e}")

    # ------------------- Measurements -------------------
    def read_voltage(self):
        if not self.is_connected():
            raise RuntimeError("Device not reachable for voltage measurement.")
        msg=float(self.query("MEAS:VOLT?"))
        return float(f"{msg:.5g}")
        

    def read_current(self):
        if not self.is_connected():
            raise RuntimeError("Device not reachable for current measurement.")
        msg=float(self.query("MEAS:CURR?"))
        return float(f"{msg:.5g}")

    def read_power(self):
        if not self.is_connected():
            raise RuntimeError("Device not reachable for power measurement.")
        msg=float(self.query("MEAS:POW?"))
        return float(f"{msg:.5g}")
    # ------------------- Control -------------------
    def set_output(self, state: bool):
        if not self.is_connected():
            raise RuntimeError("Cannot set output — device not connected.")
        self.write("OUTP ON" if state else "OUTP OFF")

    def get_id(self):
        return self.query("*IDN?")

    def is_output_on(self):
        if not self.is_connected():
            return False
        return self.query("OUTP?").strip() == '1'

    def set_voltage(self, voltage: float):
        if not self.is_connected():
            raise RuntimeError("Cannot set voltage — device not connected.")
        self.write(f"VOLT {voltage:6.4f}")

    def set_current(self, current: float):
        if not self.is_connected():
            raise RuntimeError("Cannot set current — device not connected.")
        self.write(f"CURR {current:5.4f}")

        # ------------------- Device Control -------------------
    def clear(self):
        """Clear the device status (*CLS)."""
        if not self.is_connected():
            raise RuntimeError("Cannot clear — device not connected.")
        self.write("*CLS")

    def reset(self):
        """Reset the device (*RST)."""
        if not self.is_connected():
            raise RuntimeError("Cannot reset — device not connected.")
        self.write("*RST")
