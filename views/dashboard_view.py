# views/dashboard_view.py
import tkinter as tk
from tkinter import ttk, messagebox 
import datetime
import threading

from config.settings import settings
from controllers.dashboard_controller import DashboardController
from views.components.simple_datepicker import SimpleDatePicker

class DashboardView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.controller = DashboardController(self)
        self.colors = settings.THEME_COLORS
        
        # Variables
        self.date_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y-%m-%d'))
        self.is_processing = False  # Flag untuk menandai proses sedang berjalan
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        self.configure(bg=self.colors['light'])
        self.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(self, bg=self.colors['primary'], height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🏪 PROMISE POS CLOSING SYSTEM",
            bg=self.colors['primary'],
            fg='white',
            font=('Helvetica', 18, 'bold')
        ).pack(expand=True)
        
        # Main content
        main = tk.Frame(self, bg=self.colors['light'], padx=30, pady=30)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Input section
        input_frame = tk.LabelFrame(
            main, 
            text="Input Data", 
            bg=self.colors['white'], 
            padx=25,
            pady=25,
            font=('Helvetica', 12, 'bold')
        )
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Date
        tk.Label(
            input_frame, 
            text="Tanggal:", 
            bg=self.colors['white'],
            font=('Helvetica', 12)
        ).grid(row=0, column=0, sticky='w', padx=5, pady=10)
        
        self.date_picker = SimpleDatePicker(
            input_frame,
            textvariable=self.date_var
        )
        self.date_picker.grid(row=0, column=1, padx=15, pady=10, sticky='w')
        
        # Outlet
        tk.Label(
            input_frame, 
            text="Outlet:", 
            bg=self.colors['white'],
            font=('Helvetica', 12)
        ).grid(row=1, column=0, sticky='w', padx=5, pady=10)
        
        outlet_label = tk.Label(
            input_frame, 
            text=settings.get_outlet(), 
            bg=self.colors['light'], 
            relief='sunken', 
            width=15,
            font=('Helvetica', 12, 'bold'),
            padx=10,
            pady=8
        )
        outlet_label.grid(row=1, column=1, padx=15, pady=10, sticky='w')
        
        # Buttons
        btn_frame = tk.Frame(input_frame, bg=self.colors['white'])
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Tombol Hari Ini
        self.today_btn = tk.Button(
            btn_frame, 
            text="📅 Hari Ini",
            command=self.set_today,
            bg=self.colors['accent'], 
            fg='white',
            font=('Helvetica', 12, 'bold'),
            width=8,  # Ditambah dari 6 ke 8
            height=1,
            padx=15,
            pady=10,
            cursor='hand2',
            relief='raised',
            borderwidth=3
        )
        self.today_btn.pack(side=tk.LEFT, padx=10)
        
        # Tombol Kemarin
        self.yesterday_btn = tk.Button(
            btn_frame, 
            text="📅 Kemarin",
            command=self.set_yesterday,
            bg=self.colors['accent'], 
            fg='white',
            font=('Helvetica', 12, 'bold'),
            width=8,  # Ditambah dari 6 ke 8
            height=1,
            padx=15,
            pady=10,
            cursor='hand2',
            relief='raised',
            borderwidth=3
        )
        self.yesterday_btn.pack(side=tk.LEFT, padx=10)
        
        # Tombol Generate
        self.generate_btn = tk.Button(
            btn_frame, 
            text="🚀 GENERATE & KIRIM",
            command=self.on_generate,
            bg=self.colors['success'], 
            fg='white',
            font=('Helvetica', 14, 'bold'),  # Ditambah dari 13 ke 14
            width=15,  # Ditambah dari 8 ke 15
            height=1,
            padx=20,  # Ditambah dari 15 ke 20
            pady=12,  # Ditambah dari 10 ke 12
            cursor='hand2',
            relief='raised',
            borderwidth=4
        )
        self.generate_btn.pack(side=tk.LEFT, padx=20)

        #Tombol Kirim ke API
        self.api_btn = tk.Button(
            btn_frame, 
            text="🌐 KIRIM KE API",
            command=self.on_send_api,
            bg=self.colors['accent'], 
            fg='white',
            font=('Helvetica', 12, 'bold'),
            width=10,
            height=1,
            padx=15,
            pady=10,
            cursor='hand2',
            relief='raised',
            borderwidth=3
        )
        self.api_btn.pack(side=tk.LEFT, padx=10)
        
        # Log area
        log_frame = tk.LabelFrame(
            main, 
            text="Activity Log", 
            bg=self.colors['white'],
            font=('Helvetica', 12, 'bold'),
            padx=10,
            pady=10
        )
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame untuk log dan scrollbar
        log_container = tk.Frame(log_frame, bg=self.colors['white'])
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Text widget
        self.log_text = tk.Text(
            log_container, 
            height=12, 
            width=80, 
            bg='black', 
            fg='lime', 
            font=('Consolas', 11),
            padx=10,
            pady=10
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(
            log_container, 
            width=20,
            cursor='hand2'
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # Status bar di dalam dashboard
        self.create_status_bar()
    
    def create_status_bar(self):
        """Create status bar at bottom"""
        status_bar = tk.Frame(self, bg=self.colors['secondary'], height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        
        # Status text
        self.status_label = tk.Label(
            status_bar,
            text="✓ Siap",
            bg=self.colors['secondary'],
            fg='white',
            font=('Helvetica', 10)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Date info
        self.date_info_label = tk.Label(
            status_bar,
            text=f"Tanggal: {self.date_var.get()}",
            bg=self.colors['secondary'],
            fg='white',
            font=('Helvetica', 10)
        )
        self.date_info_label.pack(side=tk.RIGHT, padx=10)
        
        # Update date info when date changes
        self.date_var.trace('w', lambda *args: self.date_info_label.config(
            text=f"Tanggal: {self.date_var.get()}"
        ))
    
    def set_today(self):
        """Set date to today"""
        today = datetime.datetime.now()
        self.date_var.set(today.strftime('%Y-%m-%d'))
        try:
            self.date_picker.set_date(today)
        except:
            pass
        self.log("📅 Tanggal: Hari Ini")
    
    def set_yesterday(self):
        """Set date to yesterday"""
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        self.date_var.set(yesterday.strftime('%Y-%m-%d'))
        try:
            self.date_picker.set_date(yesterday)
        except:
            pass
        self.log("📅 Tanggal: Kemarin")
    
    def on_generate(self):
        """Handle generate button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return
        
        # Disable buttons
        self.is_processing = True
        self.generate_btn.config(state='disabled', bg=self.colors['secondary'])
        self.today_btn.config(state='disabled', bg=self.colors['secondary'])
        self.yesterday_btn.config(state='disabled', bg=self.colors['secondary'])
        
        self.log("🚀 Memulai proses...")
        self.set_status("Memproses...")
        
        # Run in thread
        thread = threading.Thread(target=self.run_process, daemon=True)
        thread.start()
    
    def run_process(self):
        """Run the closing process in thread"""
        date_str = self.date_var.get()
        
        try:
            # Panggil controller
            success = self.controller.process_closing(date_str)
            
            if success:
                self.log("✅ Proses selesai!")
                self.set_status("Selesai")
            else:
                self.set_status("Gagal")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.set_status("Error")
            
        finally:
            # Re-enable buttons di main thread
            self.master.after(0, self.reset_buttons)

    def on_send_api(self):
        """Handle send to API button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return
        
        # Konfirmasi dulu
        if not self.ask_yes_no("Konfirmasi", "Kirim data menu ke API maharasa.id?"):
            return
        
        # Disable buttons
        self.is_processing = True
        self.api_btn.config(state='disabled', bg=self.colors['secondary'])
        
        self.log("🌐 Mengirim data ke API...")
        self.set_status("Mengirim ke API...")
        
        # Run in thread
        thread = threading.Thread(target=self.run_send_api, daemon=True)
        thread.start()

    def run_send_api(self):
        """Run send to API in thread"""
        date_str = self.date_var.get()
        
        try:
            success = self.controller.send_to_api(date_str)
            
            if success:
                self.log("✅ Data berhasil dikirim ke API!")
            else:
                self.log("❌ Gagal mengirim ke API")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            
        finally:
            self.master.after(0, self.reset_api_button)

    def reset_api_button(self):
        """Reset API button state"""
        self.is_processing = False
        self.api_btn.config(
            state='normal', 
            bg=self.colors['accent']
        )
        self.set_status("Siap")
        
    def reset_buttons(self):
        """Reset button states"""
        self.is_processing = False
        self.generate_btn.config(
            state='normal', 
            bg=self.colors['success']
        )
        self.today_btn.config(
            state='normal', 
            bg=self.colors['accent']
        )
        self.yesterday_btn.config(
            state='normal', 
            bg=self.colors['accent']
        )
        self.api_btn.config(state='normal', bg=self.colors['accent'])
        self.set_status("Siap")
    
    def set_status(self, status):
        """Update status bar"""
        self.status_label.config(text=f"✓ {status}")
    
    def log(self, message):
        """Add message to log area"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.update()
    
    def clear_log(self):
        """Clear log area"""
        self.log_text.delete(1.0, tk.END)
        self.log("📋 Log dibersihkan")
    
    # Dialog methods
    def show_error(self, title, message):
        """Show error dialog"""
        self.master.after(0, lambda: messagebox.showerror(title, message))
    
    def show_info(self, title, message):
        """Show info dialog"""
        self.master.after(0, lambda: messagebox.showinfo(title, message))
    
    def show_warning(self, title, message):
        """Show warning dialog"""
        self.master.after(0, lambda: messagebox.showwarning(title, message))
    
    def ask_yes_no(self, title, message):
        """Ask yes/no question"""
        return messagebox.askyesno(title, message)