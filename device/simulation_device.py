import random
import time


class SimulationDevice:
    """
    Simulates an AX6003P programmable power supply with a resistor load model.
    Provides realistic voltage, current, and power readings with small noise.
    """

    def __init__(self):
        # PSU parameters
        self.voltage_setpoint = 0.0
        self.current_setpoint = 0.0
        self.output_enabled = False
        self.connected = True

        # Resistor load
        self.load_resistance = 10.0  # Ohms

        # Timing for potential dynamic updates
        self._last_time = time.time()

    # ---------- Device API ----------
    def is_connected(self):
        """Return connection state (always True in simulation)."""
        return self.connected

    def set_voltage(self, voltage: float):
        """Set the simulated output voltage setpoint."""
        self.voltage_setpoint = voltage

    def set_current(self, current: float):
        """Set the simulated current limit."""
        self.current_setpoint = current

    def set_output(self, state: bool):
        """Turn simulated output ON or OFF."""
        self.output_enabled = state

    def read_voltage(self):
        """Return simulated measured voltage."""
        return self._simulate_resistor_load()[0] if self.output_enabled else 0.0

    def read_current(self):
        """Return simulated measured current."""
        return self._simulate_resistor_load()[1] if self.output_enabled else 0.0

    def read_power(self):
        """Return simulated measured power."""
        return self._simulate_resistor_load()[2] if self.output_enabled else 0.0

    # ---------- Simulation Logic ----------
    def _simulate_resistor_load(self):
        """
        Simulate a simple resistive load (Ohm's law + noise).
        V = I * R, limited by current setpoint.
        """
        # Avoid divide-by-zero
        if self.load_resistance <= 0:
            self.load_resistance = 0.1

        # Ideal current from V/R
        i_ideal = self.voltage_setpoint / self.load_resistance

        # Apply current limit
        i = min(i_ideal, self.current_setpoint)

        # Actual measured voltage and power
        v = i * self.load_resistance
        p = v * i

        # Add small measurement noise
        v += random.uniform(-0.001, 0.001)
        i += random.uniform(-0.0001, 0.0001)
        p = v * i

        return v, i, p

    # ---------- Simulation Settings ----------
    def set_load_resistance(self, resistance: float):
        """Set the simulated resistor load value."""
        self.load_resistance = max(0.1, resistance)
