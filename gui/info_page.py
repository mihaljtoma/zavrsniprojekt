# gui/control_page.py

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # koristimo PIL za slike
import os

class InfoPage(ttk.Frame):
    def __init__(self, parent, controller, device, mm):
        super().__init__(parent)
        self.controller = controller
        self.device = device
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")

        # Glavni okvir
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Naslov
        title_label = ttk.Label(main_frame, text="", font=("Helvetica", 20, "bold"), foreground="#2c3e50")
        title_label.trans_key = "label_app_title"
        title_label.pack(pady=(0, 10))

        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)

        # Frame za dvije kolone
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=10)

        # Lijeva kolona: Funkcionalnosti
        func_frame = ttk.Frame(content_frame, padding=10)
        func_frame.pack(side="left", fill="both", expand=True)

        func_title = ttk.Label(func_frame, text="", font=("Helvetica", 14, "bold"), foreground="#2980b9")
        func_title.trans_key = "label_features_title"
        func_title.pack(anchor="w", pady=(0,5))

        features = [
            "feature_connect",
            "feature_simulation",
            "feature_status",
            "feature_stb_esr",
            "feature_voltage_current",
            "feature_ovp_ocp",
            "feature_cc_cv",
            "feature_live_data",
            "feature_graph",
            "feature_csv",
            "feature_languages"

        ]

        for feat_key in features:
            lbl = ttk.Label(func_frame, text="")
            lbl.trans_key = feat_key
            lbl.config(font=("Helvetica", 11), justify="left")
            lbl.pack(anchor="w", pady=2)

        # Desna kolona: Slika
        image_frame = ttk.Frame(content_frame, padding=10)
        image_frame.pack(side="right", fill="both", expand=True)

        # Učitavanje slike
        icon_path = os.path.join(base_path, "ax_img.png")
        try:
            img = Image.open(icon_path).resize((250, 250), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label_img = ttk.Label(image_frame, image=photo)
            label_img.image = photo  # čuvamo referencu
            label_img.pack()
        except Exception as e:
            lbl_error = ttk.Label(image_frame, text="")
            lbl_error.trans_key = "label_image_unavailable"
            lbl_error.pack()
            print(f"[WARN] Could not load image: {e}")

        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)

        # Kontakt / podrška
        contact_frame = ttk.Frame(main_frame, padding=10)
        contact_frame.pack(fill="x", pady=5)

        author_lbl = ttk.Label(contact_frame, text="",font=("Helvetica", 10), foreground="#95a5a6")
        author_lbl.trans_key = "label_author"
        author_lbl.pack(anchor="w")

        contact_lbl = ttk.Label(contact_frame, text="",font=("Helvetica", 10), foreground="#95a5a6")
        contact_lbl.trans_key = "label_contact"
        contact_lbl.pack(anchor="w")

        version_lbl = ttk.Label(contact_frame, text="",font=("Helvetica", 10), foreground="#95a5a6")
        version_lbl.trans_key = "label_version"
        version_lbl.pack(anchor="w")

        note_lbl = ttk.Label(contact_frame, text="", font=("Helvetica", 10, "italic"), foreground="#95a5a6")
        note_lbl.trans_key = "label_disclaimer"
        note_lbl.pack(anchor="w", pady=(5,0))

        thanks_lbl = ttk.Label(contact_frame, text="",font=("Helvetica", 10, "italic"), foreground="#95a5a6")
        thanks_lbl.trans_key = "label_thanks"
        thanks_lbl.pack(anchor="w")
