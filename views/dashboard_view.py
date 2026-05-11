# views/dashboard_view.py
import os
import tkinter as tk
from tkinter import ttk, messagebox 
import datetime
import threading
from urllib import response

from config.settings import settings
from controllers.dashboard_controller import DashboardController
from views.components.simple_datepicker import SimpleDatePicker

class DashboardView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.controller = DashboardController(self)
        self.colors = settings.THEME_COLORS
        
        # Fallbacks for new theme keys in case they missed
        self.text_color = self.colors.get('text', '#1f2937')
        self.border_color = self.colors.get('border', '#e5e7eb')
        
        # Font settings for modern look
        self.font_family = 'Segoe UI' if self._is_windows() else 'Helvetica'
        
        # Variables
        self.date_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y-%m-%d'))
        self.is_processing = False  # Flag untuk menandai proses sedang berjalan
        
        # Setup UI
        self.setup_ui()
        self.start_auto_send()  # Mulai auto send saat view diinisialisasi
        
    def _is_windows(self):
        import platform
        return platform.system() == 'Windows'
    
    def setup_ui(self):
        self.configure(bg=self.colors['light'])
        self.pack(fill=tk.BOTH, expand=True)
        
        # Header (Modern flat header)
        header = tk.Frame(self, bg=self.colors['primary'], height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🏪 PROMISE POS CLOSING",
            bg=self.colors['primary'],
            fg='white',
            font=(self.font_family, 22, 'bold')
        ).pack(side=tk.LEFT, padx=30, pady=25)
        
        # Main content
        main = tk.Frame(self, bg=self.colors['light'], padx=40, pady=40)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Style ttk for modern look
        try:
            style = ttk.Style()
            style.theme_use('clam')
        except:
            pass
        
        # --- INPUT SECTION (Modern Card) ---
        input_card = tk.Frame(
            main, 
            bg=self.colors['white'], 
            highlightbackground=self.border_color,
            highlightcolor=self.border_color,
            highlightthickness=1
        )
        input_card.pack(fill=tk.X, pady=(0, 25))
        
        input_content = tk.Frame(input_card, bg=self.colors['white'], padx=30, pady=30)
        input_content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            input_content,
            text="Data Information",
            bg=self.colors['white'],
            fg=self.colors['primary'],
            font=(self.font_family, 14, 'bold')
        ).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 20))
        
        # Date
        tk.Label(
            input_content, 
            text="Tanggal:", 
            bg=self.colors['white'],
            fg=self.text_color,
            font=(self.font_family, 12)
        ).grid(row=1, column=0, sticky='w', padx=(0, 20), pady=10)
        
        self.date_picker = SimpleDatePicker(
            input_content,
            textvariable=self.date_var
        )
        self.date_picker.grid(row=1, column=1, sticky='w', pady=10)
        
        # Outlet
        tk.Label(
            input_content, 
            text="Outlet:", 
            bg=self.colors['white'],
            fg=self.text_color,
            font=(self.font_family, 12)
        ).grid(row=2, column=0, sticky='w', padx=(0, 20), pady=10)
        
        outlet_frame = tk.Frame(
            input_content, 
            bg=self.colors['light'],
            highlightbackground=self.border_color,
            highlightthickness=1
        )
        outlet_frame.grid(row=2, column=1, sticky='w', pady=10)
        
        outlet_label = tk.Label(
            outlet_frame, 
            text=settings.get_outlet(), 
            bg=self.colors['light'], 
            fg=self.text_color,
            width=15,
            font=(self.font_family, 12, 'bold'),
            padx=10,
            pady=8
        )
        outlet_label.pack()
        
        # --- BUTTONS SECTION ---
        btn_frame = tk.Frame(input_content, bg=self.colors['white'])
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(25, 0), sticky='w')
        
        # Function to create flat modern buttons
        def create_button(parent, text, command, bg_color, is_large=False):
            font_size = 13 if is_large else 11
            pad_y = 12 if is_large else 10
            pad_x = 25 if is_large else 20
            
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg=bg_color,
                fg='white',
                font=(self.font_family, font_size, 'bold'),
                cursor='hand2',
                relief='flat',
                borderwidth=0,
                padx=pad_x,
                pady=pad_y,
                activebackground=self.darken_color(bg_color),
                activeforeground='white'
            )
            return btn
        
                # --- BUTTON SECTION (IMPROVED LAYOUT) ---
        btn_wrapper = tk.Frame(main, bg=self.colors['white'])
        btn_wrapper.pack(fill=tk.X, padx=20, pady=(10, 15))

        # LEFT GROUP (tanggal)
        left_group = tk.Frame(btn_wrapper, bg=self.colors['white'])
        left_group.pack(side=tk.LEFT)
 
        # RIGHT GROUP (actions)
        right_group = tk.Frame(btn_wrapper, bg=self.colors['white'])
        right_group.pack(side=tk.RIGHT)

        self.generate_btn = create_button(
            right_group, "🚀 GENERATE & KIRIM", self.on_generate, self.colors['success'], True
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)
 

        self.colorplate_btn = create_button(
            right_group, "🌐 CLOSING COLORPLATE", self.on_close_colorplate, self.colors['accent']
        )
        self.colorplate_btn.pack(side=tk.LEFT, padx=5)
        
        # --- LOG SECTION (Modern Terminal Look) ---
        log_card = tk.Frame(
            main, 
            bg=self.colors['white'],
            highlightbackground=self.border_color,
            highlightthickness=1
        )
        log_card.pack(fill=tk.BOTH, expand=True)
        
        log_header = tk.Frame(log_card, bg=self.colors['white'], padx=20, pady=15)
        log_header.pack(fill=tk.X)
        
        tk.Label(
            log_header,
            text="Activity Log",
            bg=self.colors['white'],
            fg=self.text_color,
            font=(self.font_family, 12, 'bold')
        ).pack(side=tk.LEFT)
        
        log_container = tk.Frame(log_card, bg='#1e1e1e')  # Dark terminal bg
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_container, 
            height=12, 
            bg='#1e1e1e', 
            fg='#4af626', # Hacker green
            font=('Consolas', 11),
            padx=15,
            pady=15,
            relief='flat',
            borderwidth=0,
            insertbackground='white'
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Modern Scrollbar
        scrollbar = ttk.Scrollbar(
            log_container, 
            orient='vertical',
            command=self.log_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Status bar di dalam dashboard
        self.create_status_bar()
    
    def start_auto_send(self):
        """Mulai auto send tiap 5 menit"""
        self.master.after(300000, self.auto_send_api)

    def auto_send_api(self):
        """Auto kirim API tiap 5 menit"""
        if not self.is_processing:
            self.log("⏰ Auto trigger: Kirim data ke API")
            self.send_api_silent()

        self.start_auto_send()

    def send_api_silent(self):
        """Kirim API otomatis tanpa konfirmasi"""
        self.is_processing = True 
        self.set_status("Auto mengirim ke API...")

        thread = threading.Thread(target=self.run_send_api, daemon=True)
        thread.start()
        
    def darken_color(self, hex_color, factor=0.85):
        """Helper to darken a hex color for hover/active states"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = max(0, int(r * factor))
            g = max(0, int(g * factor))
            b = max(0, int(b * factor))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    def create_status_bar(self):
        """Create status bar at bottom"""
        status_bar = tk.Frame(self, bg=self.colors['secondary'], height=40)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        
        # Status text
        self.status_label = tk.Label(
            status_bar,
            text="✓ Siap",
            bg=self.colors['secondary'],
            fg='white',
            font=(self.font_family, 10, 'bold')
        )
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Date info
        self.date_info_label = tk.Label(
            status_bar,
            text=f"Tanggal: {self.date_var.get()}",
            bg=self.colors['secondary'],
            fg='#94a3b8', # Slate 400
            font=(self.font_family, 10)
        )
        self.date_info_label.pack(side=tk.RIGHT, padx=20)
        
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
        self.generate_btn.config(state='disabled', bg=self.colors['border'])
        self.today_btn.config(state='disabled', bg=self.colors['border'])
        self.yesterday_btn.config(state='disabled', bg=self.colors['border'])
        
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
        
        self.log("🌐 Mengirim data ke API...")
        self.set_status("Mengirim ke API...")
        
        # Run in thread
        thread = threading.Thread(target=self.run_send_api, daemon=True)
        thread.start()

    def on_close_colorplate(self):
        """Handle close colorplate button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return
        
        # Konfirmasi dulu
        if not self.ask_yes_no("Konfirmasi", "Apakah Anda yakin ingin menutup colorplate?"):
            return
        
        self.log("🔒 Menutup colorplate...")

        # Run in thread
        thread = threading.Thread(target=self.run_send_colorplate, daemon=True)
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

    def run_send_colorplate(self):
        """Run close colorplate in thread"""
        date_str = self.date_var.get()
        
        try:
            response = self.controller.close_colorplate(date_str)

            self.log(f"STATUS: {response.status_code}")
            self.log(f"RESPONSE: {response.text}")
            
            if response.status_code == 200:
                self.log("✅ Colorplate berhasil ditutup!")
            else:
                self.log("❌ Gagal menutup colorplate")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            
        finally:  
            self.master.after(0, self.reset_colorplate_button)


    def reset_api_button(self):
        """Reset API button state"""
        self.is_processing = False 
        self.set_status("Siap")

    def reset_colorplate_button(self):
        """Reset Colorplate button state"""
        self.is_processing = False
        self.colorplate_btn.config(
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