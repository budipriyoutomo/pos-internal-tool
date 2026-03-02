# views/dashboard_view.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import datetime
import threading

from config.settings import settings
from controllers.dashboard_controller import DashboardController

class DashboardView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.controller = DashboardController(self)
        self.colors = settings.THEME_COLORS
        
        # Variables
        self.date_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y-%m-%d'))
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        self.configure(bg=self.colors['light'])
        self.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(self, bg=self.colors['primary'], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🏪 PROMISE POS CLOSING SYSTEM",
            bg=self.colors['primary'],
            fg='white',
            font=('Helvetica', 14, 'bold')
        ).pack(expand=True)
        
        # Main content
        main = tk.Frame(self, bg=self.colors['light'], padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Input section
        input_frame = tk.LabelFrame(main, text="Input Data", bg=self.colors['white'], padx=15, pady=15)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Date
        tk.Label(input_frame, text="Tanggal:", bg=self.colors['white']).grid(row=0, column=0, sticky='w')
        self.date_picker = DateEntry(
            input_frame,
            textvariable=self.date_var,
            date_pattern='yyyy-mm-dd',
            width=15
        )
        self.date_picker.grid(row=0, column=1, padx=10, pady=5)
        
        # Outlet
        tk.Label(input_frame, text="Outlet:", bg=self.colors['white']).grid(row=1, column=0, sticky='w')
        tk.Label(input_frame, text=settings.get_outlet(), bg=self.colors['light'], 
                relief='sunken', width=15).grid(row=1, column=1, padx=10, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(input_frame, bg=self.colors['white'])
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="Hari Ini", command=self.set_today,
                 bg=self.colors['accent'], fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Kemarin", command=self.set_yesterday,
                 bg=self.colors['accent'], fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Generate & Kirim", command=self.on_generate,
                 bg=self.colors['success'], fg='white', padx=20).pack(side=tk.LEFT, padx=20)
        
        # Log area
        log_frame = tk.LabelFrame(main, text="Activity Log", bg=self.colors['white'])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=15, width=80, bg='black', fg='lime', 
                                font=('Consolas', 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
    
    def set_today(self):
        today = datetime.datetime.now()
        self.date_var.set(today.strftime('%Y-%m-%d'))
        self.date_picker.set_date(today)
        self.log("📅 Tanggal: Hari Ini")
    
    def set_yesterday(self):
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        self.date_var.set(yesterday.strftime('%Y-%m-%d'))
        self.date_picker.set_date(yesterday)
        self.log("📅 Tanggal: Kemarin")
    
    def on_generate(self):
        # Disable button
        self.log("🚀 Memulai proses...")
        
        # Run in thread
        thread = threading.Thread(target=self.run_process, daemon=True)
        thread.start()
    
    def run_process(self):
        date_str = self.date_var.get()
        self.controller.process_closing(date_str)
    
    def log(self, message):
        self.log_text.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.update()
    
    def show_error(self, title, message):
        messagebox.showerror(title, message)
    
    def show_info(self, title, message):
        messagebox.showinfo(title, message)
    
    def ask_yes_no(self, title, message):
        return messagebox.askyesno(title, message)