#!/usr/bin/env python3
"""
Promise POS Internal Tool
Main application entry point
"""

# ==================== IMPORTS ====================  
import sys
import os
import locale
import subprocess
from queue_db import recreate_db 

recreate_db()  # Buat database queue baru setiap kali aplikasi dibuka

# Hapus file lock worker jika tertinggal
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

lock_file = os.path.join(base_dir, "worker.lock")
if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
        print(f"🧹 Leftover lock file removed: {lock_file}")
    except Exception as e:
        print(f"⚠️ Failed to remove leftover lock: {e}")

os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "English_United States")
    except:
        pass

import tkinter as tk
from tkinter import messagebox
import datetime

  

from config.settings import settings
from views.dashboard_view import DashboardView

# ==================== MAIN APP ====================
class PromisePOSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Window configuration - 1/3 layar
        self.set_window_size()
        
        # Set icon jika ada
        self.set_icon()
        
        # Handle window closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create menu bar
        self.create_menu()
        
        # Show dashboard
        self.dashboard = DashboardView(self)
        self.dashboard.pack(fill=tk.BOTH, expand=True)
        
        # Center window di layar
        self.center_window()
        
        # Bind keyboard shortcuts
        self.bind_shortcuts()
        
        # Start background worker
        self.start_worker()
        
        print(f"✅ {settings.APP_NAME} started")
        print(f"📐 Window size: {self.window_width}x{self.window_height}")
    
    def start_worker(self):
        """Mulai background worker.py sebagai subprocess"""
        try:
            if getattr(sys, 'frozen', False):
                # Cari di _MEIPASS (jika onefile bundle) atau di folder exe (jika onedir)
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                worker_exe = os.path.join(base_dir, "worker.exe")
                if os.path.exists(worker_exe):
                    self.worker_process = subprocess.Popen(
                        [worker_exe],
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                else:
                    # Fallback jika worker.exe diletakkan di luar folder bundel (di folder exe yang sama)
                    exe_dir = os.path.dirname(sys.executable)
                    worker_exe_fallback = os.path.join(exe_dir, "worker.exe")
                    if os.path.exists(worker_exe_fallback):
                        self.worker_process = subprocess.Popen(
                            [worker_exe_fallback],
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                        )
                    else:
                        worker_script = os.path.join(exe_dir, "worker.py")
                        self.worker_process = subprocess.Popen(
                            [sys.executable, worker_script],
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                        )
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                worker_script = os.path.join(base_dir, "worker.py")
                self.worker_process = subprocess.Popen(
                    [sys.executable, worker_script]
                )
            print("🚀 Worker process started successfully")
        except Exception as e:
            print(f"❌ Failed to start worker process: {e}")
            self.worker_process = None

    def set_window_size(self):
        """Set window size to 1/3 of screen"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        self.window_width = int(screen_width * 0.6)
        self.window_height = int(screen_height * 0.6)
        
        if self.window_width < 900:
            self.window_width = 900
        if self.window_height < 700:
            self.window_height = 700
        
        self.geometry(f"{self.window_width}x{self.window_height}")
        self.minsize(800, 600)
        
        print(f"🖥️  Screen: {screen_width}x{screen_height}")
        print(f"📐 Window: {self.window_width}x{self.window_height}")
    
    def center_window(self):
        """Center window on screen"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (self.window_width // 2)
        y = (screen_height // 2) - (self.window_height // 2)
        self.geometry(f"+{x}+{y}")
        print(f"📍 Window position: ({x}, {y})")
    
    def set_icon(self):
        """Set application icon"""
        try:
            icon_path = settings.ASSETS_DIR / 'icons' / 'app.ico'
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except:
            pass
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Generate Report", command=self.on_generate_menu, accelerator="Ctrl+G")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Full Screen", command=self.toggle_fullscreen, accelerator="F11")
        view_menu.add_command(label="Normal Size", command=self.set_one_third_screen)
        view_menu.add_separator()
        view_menu.add_command(label="Center Window", command=self.center_window)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Open Reports Folder", command=self.open_reports_folder)
        tools_menu.add_command(label="Open Logs Folder", command=self.open_logs_folder)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Check Config", command=self.check_config)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
    
    def bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.bind('<Control-g>', lambda e: self.on_generate_menu())
        self.bind('<Control-G>', lambda e: self.on_generate_menu())
        self.bind('<F5>', lambda e: self.on_generate_menu())
        self.bind('<F1>', lambda e: self.show_about())
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.bind('<Escape>', lambda e: self.exit_fullscreen())
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        self.attributes('-fullscreen', not self.attributes('-fullscreen'))
        if not self.attributes('-fullscreen'):
            self.set_one_third_screen()
    
    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        if self.attributes('-fullscreen'):
            self.attributes('-fullscreen', False)
            self.set_one_third_screen()
    
    def set_one_third_screen(self):
        """Set window to 1/3 of screen size"""
        self.attributes('-fullscreen', False)
        self.set_window_size()
        self.center_window()
    
    def on_generate_menu(self):
        """Menu item: Generate Report"""
        if hasattr(self.dashboard, 'on_generate'):
            self.dashboard.on_generate()
    
    def open_reports_folder(self):
        """Open reports folder in explorer"""
        try:
            reports_path = settings.REPORTS_DIR
            if reports_path.exists():
                if sys.platform == 'win32':
                    os.startfile(str(reports_path))
                else:
                    import subprocess
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(reports_path)])
            else:
                messagebox.showinfo("Info", f"Folder reports belum dibuat:\n{reports_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka folder: {e}")
    
    def open_logs_folder(self):
        """Open logs folder in explorer"""
        try:
            logs_path = settings.LOGS_DIR
            if logs_path.exists():
                if sys.platform == 'win32':
                    os.startfile(str(logs_path))
                else:
                    import subprocess
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(logs_path)])
            else:
                messagebox.showinfo("Info", f"Folder logs belum dibuat:\n{logs_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka folder: {e}")
    
    def check_config(self):
        """Check configuration"""
        config_path = settings.config_path
        
        info = []
        info.append("📋 KONFIGURASI APLIKASI")
        info.append("="*40)
        info.append(f"Config file: {config_path}")
        info.append(f"Config exists: {'✅' if config_path.exists() else '❌'}")
        info.append("")
        
        if config_path.exists():
            try:
                info.append("Database Settings:")
                db = settings.get_db_config()
                info.append(f"  - Host: {db['host']}")
                info.append(f"  - Database: {db['database']}")
                info.append(f"  - User: {db['user']}")
                info.append(f"  - Password: {'✅' if db['password'] else '❌'} (kosong)")
                
                info.append("")
                info.append("Email Settings:")
                mail = settings.get_mail_config()
                info.append(f"  - Sender: {mail['sender']}")
                info.append(f"  - Receiver: {mail['receiver']}")
                info.append(f"  - Password: {'✅' if mail['password'] else '❌'} (kosong)")
                
                info.append("")
                info.append("App Settings:")
                info.append(f"  - Outlet: {settings.get_outlet()}")
                info.append(f"  - Version: {settings.APP_VERSION}")
            except Exception as e:
                info.append(f"❌ Error membaca config: {e}")
        else:
            info.append("❌ File config tidak ditemukan!")
            info.append("")
            info.append("📝 Cara membuat config:")
            info.append("1. Copy config.ini.example menjadi config.ini")
            info.append("2. Edit config.ini dengan setting Anda")
        
        messagebox.showinfo("Configuration", "\\n".join(info))
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
{settings.APP_NAME}
Version {settings.APP_VERSION}

🏪 Promise POS Closing System
© 2024 Promise System

Fitur:
- Generate laporan penjualan
- Kirim email otomatis
- Multi-outlet support
- Touch screen friendly
- Export ke API

Teknologi:
- Python 3.11
- Tkinter
- MySQL Connector

Folder:
- Reports: {settings.REPORTS_DIR}
- Logs: {settings.LOGS_DIR}
- Config: {settings.config_path}

Shortcut:
- Ctrl+G : Generate Report
- F11    : Fullscreen
- Esc    : Exit Fullscreen
- F1     : About
        """
        messagebox.showinfo(f"About {settings.APP_NAME}", about_text.strip())
    
    def on_closing(self):
        """Handle window closing"""
        try:
            # Log shutdown
            print("🔄 Shutting down application...")
            
            # Hentikan worker subprocess
            if hasattr(self, 'worker_process') and self.worker_process:
                print("🔄 Terminating worker process...")
                try:
                    self.worker_process.terminate()
                    self.worker_process.wait(timeout=3)
                except Exception as ex:
                    print(f"⚠️ Error terminating worker: {ex}")
                print("✅ Worker process terminated")

            # Ask confirmation jika ada proses running
            if hasattr(self.dashboard, 'is_processing') and self.dashboard.is_processing:
                if not messagebox.askyesno("Konfirmasi", "Ada proses sedang berjalan. Yakin ingin keluar?"):
                    return
            
            # Destroy window
            self.destroy()
            print("👋 Application terminated")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.destroy()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:   
        # Print startup info
        print("="*60)
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
        print("="*60)
        print(f"📁 Base directory: {settings.BASE_DIR}")
        print(f"📁 Reports: {settings.REPORTS_DIR}")
        print(f"📁 Logs: {settings.LOGS_DIR}")
        print(f"📄 Config: {settings.config_path}")
        print("="*60)
        
        # Create and run app
        app = PromisePOSApp() 
        app.mainloop()

    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")