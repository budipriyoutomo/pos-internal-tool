#!/usr/bin/env python3
"""
Promise POS Internal Tool
"""

import tkinter as tk
from config.settings import settings
from views.dashboard_view import DashboardView

class PromisePOSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title(settings.APP_NAME)
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Show dashboard
        DashboardView(self)
        
        # Center window
        self.center_window()
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

if __name__ == "__main__":
    app = PromisePOSApp()
    app.mainloop()