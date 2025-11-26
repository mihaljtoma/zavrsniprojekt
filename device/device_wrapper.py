# device/device_wrapper.py
from device.ax6003p import AX6003PDevice
from device.simulation_device import SimulationDevice

class DeviceWrapper:
    def __init__(self, use_simulation=True):
        self.use_simulation = use_simulation
        self.real_device = AX6003PDevice()
        self.sim_device = SimulationDevice()
        self.device = self.sim_device if use_simulation else self.real_device

    # ---------- Methods that forward to current device ----------
    def __getattr__(self, name):
        """Forward all calls to the currently active device."""
        return getattr(self.device, name)

    def enable_simulation(self, enable: bool):
        self.use_simulation = enable
        self.device = self.sim_device if enable else self.real_device
