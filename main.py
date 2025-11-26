from device.device_wrapper import DeviceWrapper
from gui.main_app import MainApp

if __name__ == "__main__":
    try:
        device = DeviceWrapper(use_simulation=False)  # start in simulation mode
        
        app = MainApp(device)
        app.mainloop()
    except Exception as e:
        print(f"[FATAL] Failed to start application: {e}")
