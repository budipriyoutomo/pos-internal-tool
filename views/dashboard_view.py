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
        header = tk.Frame(self, bg=self.colors['primary'], height=80)  # Tinggi header ditambah
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🏪 PROMISE POS CLOSING SYSTEM",
            bg=self.colors['primary'],
            fg='white',
            font=('Helvetica', 18, 'bold')  # Font lebih besar
        ).pack(expand=True)
        
        # Main content
        main = tk.Frame(self, bg=self.colors['light'], padx=30, pady=30)  # Padding lebih besar
        main.pack(fill=tk.BOTH, expand=True)
        
        # Input section
        input_frame = tk.LabelFrame(
            main, 
            text="Input Data", 
            bg=self.colors['white'], 
            padx=25,  # Padding lebih besar
            pady=25,  # Padding lebih besar
            font=('Helvetica', 12, 'bold')  # Font label frame lebih besar
        )
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Date - dengan font lebih besar
        tk.Label(
            input_frame, 
            text="Tanggal:", 
            bg=self.colors['white'],
            font=('Helvetica', 12)  # Font lebih besar
        ).grid(row=0, column=0, sticky='w', padx=5, pady=10)
        
        self.date_picker = DateEntry(
            input_frame,
            textvariable=self.date_var,
            date_pattern='yyyy-mm-dd',
            width=15,
            font=('Helvetica', 12),  # Font lebih besar
            background=self.colors['accent'],
            foreground='white',
            borderwidth=3  # Border lebih tebal
        )
        self.date_picker.grid(row=0, column=1, padx=15, pady=10, sticky='w')
        
        # Outlet - dengan font lebih besar
        tk.Label(
            input_frame, 
            text="Outlet:", 
            bg=self.colors['white'],
            font=('Helvetica', 12)  # Font lebih besar
        ).grid(row=1, column=0, sticky='w', padx=5, pady=10)
        
        outlet_label = tk.Label(
            input_frame, 
            text=settings.get_outlet(), 
            bg=self.colors['light'], 
            relief='sunken', 
            width=15,
            font=('Helvetica', 12, 'bold'),  # Font lebih besar dan bold
            padx=10,
            pady=8  # Padding vertikal
        )
        outlet_label.grid(row=1, column=1, padx=15, pady=10, sticky='w')
        
        # Buttons - DIPERBESAR UKURANNYA
        btn_frame = tk.Frame(input_frame, bg=self.colors['white'])
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Tombol Hari Ini - lebih besar
        today_btn = tk.Button(
            btn_frame, 
            text="📅 Hari Ini",
            command=self.set_today,
            bg=self.colors['accent'], 
            fg='white',
            font=('Helvetica', 14, 'bold'),  # Font besar
            width=12,  # Lebar dalam karakter
            height=2,  # Tinggi dalam baris teks
            padx=15,
            pady=10,
            cursor='hand2',
            relief='raised',
            borderwidth=3
        )
        today_btn.pack(side=tk.LEFT, padx=10)
        
        # Tombol Kemarin - lebih besar
        yesterday_btn = tk.Button(
            btn_frame, 
            text="📅 Kemarin",
            command=self.set_yesterday,
            bg=self.colors['accent'], 
            fg='white',
            font=('Helvetica', 14, 'bold'),  # Font besar
            width=12,  # Lebar dalam karakter
            height=2,  # Tinggi dalam baris teks
            padx=15,
            pady=10,
            cursor='hand2',
            relief='raised',
            borderwidth=3
        )
        yesterday_btn.pack(side=tk.LEFT, padx=10)
        
        # Tombol Generate - DIPERBESAR PALING BESAR (tombol utama)
        generate_btn = tk.Button(
            btn_frame, 
            text="🚀 GENERATE & KIRIM",
            command=self.on_generate,
            bg=self.colors['success'], 
            fg='white',
            font=('Helvetica', 16, 'bold'),  # Font paling besar
            width=20,  # Lebar lebih besar
            height=2,  # Tinggi 2 baris
            padx=25,
            pady=15,
            cursor='hand2',
            relief='raised',
            borderwidth=4  # Border lebih tebal
        )
        generate_btn.pack(side=tk.LEFT, padx=20)
        
        # Log area - juga diperbesar
        log_frame = tk.LabelFrame(
            main, 
            text="Activity Log", 
            bg=self.colors['white'],
            font=('Helvetica', 12, 'bold'),  # Font label frame lebih besar
            padx=10,
            pady=10
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame untuk log dan scrollbar
        log_container = tk.Frame(log_frame, bg=self.colors['white'])
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text widget dengan font lebih besar untuk touch
        self.log_text = tk.Text(
            log_container, 
            height=12, 
            width=80, 
            bg='black', 
            fg='lime', 
            font=('Consolas', 11),  # Font lebih besar
            padx=10,
            pady=10
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar juga diperbesar
        scrollbar = tk.Scrollbar(
            log_container, 
            width=20,  # Lebar scrollbar ditambah
            cursor='hand2'
        )
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
        # Disable button (opsional - bisa ditambahkan efek disable)
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