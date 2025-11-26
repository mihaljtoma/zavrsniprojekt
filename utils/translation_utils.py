import json
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class Translator:
    def __init__(self, language='en'):
        self.language = language
        self.translations = {}
        self.load_language(language)

    def load_language(self, language):
        path = resource_path(os.path.join("locale", f"{language}.json"))
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.language = language
        except FileNotFoundError:
            print(f"Warning: translation file for '{language}' not found, fallback to English.")
            if language != 'en':  # avoid infinite recursion
                self.load_language('en')


    def t(self, key):
        return self.translations.get(key, key)
