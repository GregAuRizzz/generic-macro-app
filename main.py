"""
GenericMacro - No-Code Macro Automation Tool
Entry point
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.app import GenericMacroApp

if __name__ == "__main__":
    app = GenericMacroApp()
    app.run()