# views/dashboard_view.py
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import settings
from controllers.dashboard_controller import DashboardController
from views.components.simple_datepicker import SimpleDatePicker
from views.components.widgets import FONT, ModernButton, StatusBadge


class DashboardView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.controller = DashboardController(self)
        self.colors = settings.THEME_COLORS
        self.font_family = FONT

        # Variables
        self.date_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y-%m-%d'))
        self.is_processing = False  # Flag untuk menandai proses sedang berjalan
        self._last_date = self.date_var.get()

        # Setup UI
        self.setup_ui()
        self.date_var.trace_add('write', lambda *args: self.on_date_changed())
        self.on_date_changed()
        self.log(f"👋 Siap. Outlet {settings.get_outlet()} — pilih tanggal lalu jalankan langkah 1.")

    # ==================== LAYOUT ====================
    def setup_ui(self):
        self.configure(bg=self.colors['light'])
        self.pack(fill=tk.BOTH, expand=True)

        try:
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('Busy.Horizontal.TProgressbar',
                            troughcolor=self.colors['secondary'],
                            background=self.colors['header_sub'],
                            bordercolor=self.colors['secondary'],
                            lightcolor=self.colors['header_sub'],
                            darkcolor=self.colors['header_sub'])
        except tk.TclError:
            pass

        self.create_header()
        self.create_status_bar()  # pack BOTTOM sebelum body supaya tidak terdorong keluar

        body = tk.Frame(self, bg=self.colors['light'], padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=self.colors['light'])
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        self.create_steps_card(left)

        right = tk.Frame(body, bg=self.colors['light'])
        right.grid(row=0, column=1, sticky='nsew')
        self.create_log_card(right)

    def create_header(self):
        header = tk.Frame(self, bg=self.colors['secondary'], padx=24, pady=10)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg=self.colors['secondary'])
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text="🏪  Promise POS Closing", bg=self.colors['secondary'],
                 fg='white', font=(FONT, 15, 'bold')).pack(anchor='w')
        tk.Label(title_box, text="Closing harian outlet · laporan, email & Colorplate",
                 bg=self.colors['secondary'], fg=self.colors['header_sub'],
                 font=(FONT, 10)).pack(anchor='w')

        tk.Label(header, text=f"🏬  {settings.get_outlet()}", bg=self.colors['primary'],
                 fg='white', font=(FONT, 11, 'bold'), padx=14, pady=6
                 ).pack(side=tk.RIGHT)

    def _card(self, parent, **pack_opts):
        """Kartu putih dengan border tipis"""
        card = tk.Frame(parent, bg=self.colors['white'],
                        highlightbackground=self.colors['border'], highlightthickness=1)
        card.pack(**pack_opts)
        inner = tk.Frame(card, bg=self.colors['white'], padx=20, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)
        return inner

    def _section_label(self, parent, text):
        tk.Label(parent, text=text.upper(), bg=self.colors['white'], fg=self.colors['muted'],
                 font=(FONT, 9, 'bold')).pack(anchor='w', pady=(0, 6))

    def create_steps_card(self, parent):
        card = self._card(parent, fill=tk.BOTH, expand=True)

        # --- Tanggal ---
        self._section_label(card, "Tanggal closing")
        self.date_picker = SimpleDatePicker(card, textvariable=self.date_var)
        self.date_picker.pack(fill=tk.X)

        hint_row = tk.Frame(card, bg=self.colors['white'])
        hint_row.pack(fill=tk.X, pady=(8, 0))
        self.date_hint = tk.Label(hint_row, bg=self.colors['white'], fg=self.colors['muted'],
                                  font=(FONT, 9))
        self.date_hint.pack(side=tk.LEFT)

        self.yesterday_btn = ModernButton(hint_row, "Kemarin", self.set_yesterday, 'soft', 'sm')
        self.yesterday_btn.pack(side=tk.RIGHT)
        self.today_btn = ModernButton(hint_row, "Hari Ini", self.set_today, 'soft', 'sm')
        self.today_btn.pack(side=tk.RIGHT, padx=(0, 6))

        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill=tk.X, pady=(12, 14))

        # --- Langkah ---
        self.step_generate = self.create_step(
            card, 1, "Generate & Kirim Report",
            "Data POS → report .txt → kirim email.",
            "🚀  GENERATE & KIRIM", self.on_generate, 'success')
        self.generate_btn = self.step_generate['button']

        self.step_colorplate = self.create_step(
            card, 2, "POS Closing",
            "Publish ke server, setelah langkah 1.",
            "🌐  CLOSING POS", self.on_close_colorplate, 'primary')
        self.colorplate_btn = self.step_colorplate['button']


    def create_step(self, parent, number, title, description, button_text, command, variant):
        """Satu baris langkah: nomor bulat, judul, badge status, deskripsi, tombol"""
        row = tk.Frame(parent, bg=self.colors['white'])
        row.pack(fill=tk.X, pady=(2, 12))

        circle = tk.Canvas(row, width=30, height=30, bg=self.colors['white'], highlightthickness=0)
        circle.pack(side=tk.LEFT, anchor='n', padx=(0, 12))
        oval = circle.create_oval(1, 1, 29, 29, fill=self.colors['primary_soft'], outline='')
        label = circle.create_text(15, 15, text=str(number), fill=self.colors['primary'],
                                   font=(FONT, 11, 'bold'))

        content = tk.Frame(row, bg=self.colors['white'])
        content.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_row = tk.Frame(content, bg=self.colors['white'])
        title_row.pack(fill=tk.X)
        tk.Label(title_row, text=title, bg=self.colors['white'], fg=self.colors['text'],
                 font=(FONT, 11, 'bold')).pack(side=tk.LEFT)
        badge = StatusBadge(title_row)
        badge.pack(side=tk.RIGHT)

        tk.Label(content, text=description, bg=self.colors['white'], fg=self.colors['muted'],
                 font=(FONT, 10), justify='left', anchor='w', wraplength=290
                 ).pack(fill=tk.X, pady=(0, 8))

        button = ModernButton(content, button_text, command, variant, 'md')
        button.pack(fill=tk.X)

        return {'canvas': circle, 'oval': oval, 'label': label, 'number': number,
                'badge': badge, 'button': button}

    def set_step_state(self, step, state):
        """Update badge + lingkaran nomor sebuah langkah"""
        step['badge'].set_state(state)
        fill, fg, text = {
            'success': (self.colors['success'], 'white', '✓'),
            'error': (self.colors['danger'], 'white', '!'),
            'running': (self.colors['warning'], 'white', str(step['number'])),
        }.get(state, (self.colors['primary_soft'], self.colors['primary'], str(step['number'])))
        step['canvas'].itemconfig(step['oval'], fill=fill)
        step['canvas'].itemconfig(step['label'], fill=fg, text=text)

    def create_log_card(self, parent):
        card = tk.Frame(parent, bg=self.colors['white'],
                        highlightbackground=self.colors['border'], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        log_header = tk.Frame(card, bg=self.colors['white'], padx=16, pady=10)
        log_header.pack(fill=tk.X)
        tk.Label(log_header, text="Activity Log", bg=self.colors['white'],
                 fg=self.colors['text'], font=(FONT, 12, 'bold')).pack(side=tk.LEFT)
        ModernButton(log_header, "🗑 Bersihkan", self.clear_log, 'soft', 'sm').pack(side=tk.RIGHT)
        ModernButton(log_header, "📋 Salin", self.copy_log, 'soft', 'sm').pack(side=tk.RIGHT, padx=(0, 6))

        log_container = tk.Frame(card, bg=self.colors['log_bg'])
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_container,
            height=12,
            bg=self.colors['log_bg'],
            fg=self.colors['log_text'],
            font=('Consolas', 10),
            padx=14,
            pady=12,
            relief='flat',
            borderwidth=0,
            wrap='word',
            spacing1=2,
            spacing3=2,
            state='disabled',
            cursor='arrow'
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.tag_configure('time', foreground=self.colors['log_muted'])
        self.log_text.tag_configure('success', foreground=self.colors['log_success'])
        self.log_text.tag_configure('warning', foreground=self.colors['log_warning'])
        self.log_text.tag_configure('error', foreground=self.colors['log_error'])

        scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def create_status_bar(self):
        """Create status bar at bottom"""
        status_bar = tk.Frame(self, bg=self.colors['secondary'], height=34)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_dot = tk.Label(status_bar, text="●", bg=self.colors['secondary'],
                                   fg=self.colors['log_success'], font=(FONT, 10))
        self.status_dot.pack(side=tk.LEFT, padx=(20, 6))

        self.status_label = tk.Label(status_bar, text="Siap", bg=self.colors['secondary'],
                                     fg='white', font=(FONT, 10, 'bold'))
        self.status_label.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(status_bar, mode='indeterminate', length=140,
                                        style='Busy.Horizontal.TProgressbar')

        self.date_info_label = tk.Label(status_bar, bg=self.colors['secondary'],
                                        fg=self.colors['header_sub'], font=(FONT, 9))
        self.date_info_label.pack(side=tk.RIGHT, padx=20)

    # ==================== TANGGAL ====================
    def on_date_changed(self):
        """Update petunjuk tanggal, chip aktif, dan reset status langkah bila tanggal berganti"""
        date = self.date_picker.get_date().date()
        delta = (datetime.date.today() - date).days

        if delta == 0:
            hint, fg = "Hari ini", self.colors['muted']
        elif delta == 1:
            hint, fg = "Kemarin", self.colors['muted']
        elif delta > 1:
            hint, fg = f"{delta} hari yang lalu", self.colors['warning']
        else:
            hint, fg = "⚠ Tanggal di masa depan", self.colors['danger']
        self.date_hint.config(text=f"{hint}  ·  {self.date_var.get()}", fg=fg)

        # Chip yang sesuai tanggal terpilih ditampilkan aktif
        for btn, active in ((self.today_btn, delta == 0), (self.yesterday_btn, delta == 1)):
            if active:
                btn.set_variant_colors(self.colors['accent'], 'white')
            else:
                btn.set_variant_colors(self.colors['primary_soft'], self.colors['primary'])

        self.date_info_label.config(text=f"Tanggal {self.date_var.get()}  ·  Ctrl+G / F5 = Generate")

        if self.date_var.get() != self._last_date:
            self._last_date = self.date_var.get()
            self.set_step_state(self.step_generate, 'idle')
            self.set_step_state(self.step_colorplate, 'idle')

    def set_today(self):
        """Set date to today"""
        self.date_picker.set_date(datetime.datetime.now())
        self.log("📅 Tanggal: Hari Ini")

    def set_yesterday(self):
        """Set date to yesterday"""
        self.date_picker.set_date(datetime.datetime.now() - datetime.timedelta(days=1))
        self.log("📅 Tanggal: Kemarin")

    # ==================== AKSI ====================
    def set_busy(self, busy, status=None):
        """Kunci/buka semua kontrol saat proses berjalan (main thread saja)"""
        self.is_processing = busy
        for btn in (self.generate_btn, self.colorplate_btn, self.today_btn, self.yesterday_btn):
            btn.set_enabled(not busy)
        self.date_picker.set_enabled(not busy)

        if busy:
            self.progress.pack(side=tk.LEFT, padx=16)
            self.progress.start(12)
            self.status_dot.config(fg=self.colors['log_warning'])
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.status_dot.config(fg=self.colors['log_success'])
        if status:
            self.status_label.config(text=status)

    def on_generate(self):
        """Handle generate button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return

        self.set_busy(True, "Membuat & mengirim report...")
        self.set_step_state(self.step_generate, 'running')
        self.log("🚀 Memulai proses...")

        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        """Run the closing process in thread"""
        date_str = self.date_var.get()
        success = False

        try:
            # Panggil controller
            success = self.controller.process_closing(date_str)
            if success:
                self.log("✅ Proses selesai!")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
        finally:
            # Re-enable buttons di main thread
            self.master.after(0, lambda: self.finish_step(self.step_generate, success))

    def on_close_colorplate(self):
        """Handle close colorplate button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return

        # Konfirmasi dulu
        if not self.ask_yes_no(
            "Konfirmasi",
            f"Tutup Colorplate untuk tanggal {self.date_var.get()}?\n\n"
            "Pastikan langkah 1 (Generate & Kirim) sudah dijalankan."
        ):
            return

        self.set_busy(True, "Menutup Colorplate...")
        self.set_step_state(self.step_colorplate, 'running')

        threading.Thread(target=self.run_send_colorplate, daemon=True).start()

    def run_send_colorplate(self):
        """Run close colorplate in thread"""
        date_str = self.date_var.get()
        success = False

        try:
            success = self.controller.close_colorplate(date_str)
            if success:
                self.log("✅ Silahkan Lanjutkan ke Colorplate App!")
            else:
                self.log("❌ Gagal menutup colorplate")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
        finally:
            self.master.after(0, lambda: self.finish_step(self.step_colorplate, success))

    def finish_step(self, step, success):
        """Dipanggil di main thread setelah proses thread selesai"""
        self.set_step_state(step, 'success' if success else 'error')
        self.set_busy(False, "Selesai" if success else "Gagal — lihat Activity Log")

    def on_send_api(self):
        """Handle send to API button click"""
        if self.is_processing:
            self.log("⚠️ Proses sedang berjalan, harap tunggu...")
            return

        # Konfirmasi dulu
        if not self.ask_yes_no("Konfirmasi", "Kirim data menu ke API maharasa.id?"):
            return

        self.set_busy(True, "Mengirim ke API...")
        self.log("🌐 Mengirim data ke API...")

        threading.Thread(target=self.run_send_api, daemon=True).start()

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
        self.set_busy(False, "Siap")

    def reset_buttons(self):
        """Reset button states"""
        self.set_busy(False, "Siap")

    # ==================== STATUS & LOG ====================
    def _on_main_thread(self):
        return threading.current_thread() is threading.main_thread()

    def set_status(self, status):
        """Update status bar (aman dipanggil dari thread mana pun)"""
        if not self._on_main_thread():
            self.master.after(0, lambda: self.set_status(status))
            return
        self.status_label.config(text=status)

    def log(self, message):
        """Add message to log area (aman dipanggil dari thread mana pun)"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        if not self._on_main_thread():
            self.master.after(0, lambda: self._append_log(timestamp, message))
            return
        self._append_log(timestamp, message)
        self.update_idletasks()

    def _append_log(self, timestamp, message):
        if message.startswith('❌'):
            tag = 'error'
        elif message.startswith('⚠'):
            tag = 'warning'
        elif message.startswith('✅'):
            tag = 'success'
        else:
            tag = ()
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{timestamp}  ", 'time')
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def clear_log(self):
        """Clear log area"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log("📋 Log dibersihkan")

    def copy_log(self):
        """Salin seluruh isi log ke clipboard (untuk dikirim ke tim IT)"""
        self.clipboard_clear()
        self.clipboard_append(self.log_text.get(1.0, tk.END).strip())
        self.set_status("Log disalin ke clipboard")

    # ==================== DIALOG ====================
    def show_error(self, title, message):
        """Show error dialog"""
        self.master.after(0, lambda: messagebox.showerror(title, message, parent=self.master))

    def show_info(self, title, message):
        """Show info dialog"""
        self.master.after(0, lambda: messagebox.showinfo(title, message, parent=self.master))

    def show_warning(self, title, message):
        """Show warning dialog"""
        self.master.after(0, lambda: messagebox.showwarning(title, message, parent=self.master))

    def ask_yes_no(self, title, message):
        """Ask yes/no question.

        Controller memanggil ini dari thread proses; messagebox harus dibuka di
        main thread, jadi thread pemanggil menunggu sampai user menjawab.
        """
        if self._on_main_thread():
            return messagebox.askyesno(title, message, parent=self.master)

        result = {'answer': False}
        answered = threading.Event()

        def ask():
            try:
                result['answer'] = messagebox.askyesno(title, message, parent=self.master)
            finally:
                answered.set()

        self.master.after(0, ask)
        answered.wait()
        return result['answer']
