# views/components/simple_datepicker.py
import calendar
import datetime
import tkinter as tk

from config.settings import settings
from views.components.widgets import FONT, BULAN, darken, format_tanggal


class SimpleDatePicker(tk.Frame):
    """Date picker dengan popup kalender bulanan, tanpa dependensi babel.

    Nilai disimpan di `textvariable` dalam format 'YYYY-MM-DD'; tampilan
    memakai format Indonesia ('Kamis, 23 Oktober 2026').
    """

    def __init__(self, master, textvariable=None, **kwargs):
        self.colors = settings.THEME_COLORS
        super().__init__(master, bg=self.colors['white'], **kwargs)

        self.variable = textvariable or tk.StringVar()
        self.current_date = datetime.datetime.now()
        self.enabled = True
        self.popup = None

        # Field yang bisa diklik: ikon + tanggal + panah
        self.field = tk.Frame(
            self,
            bg=self.colors['white'],
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['primary'],
            highlightthickness=1,
            cursor='hand2'
        )
        self.field.pack(fill=tk.X)

        self.icon_label = tk.Label(self.field, text="📅", font=(FONT, 13),
                                   bg=self.colors['white'], fg=self.colors['primary'])
        self.icon_label.pack(side=tk.LEFT, padx=(12, 6), pady=5)

        self.text_label = tk.Label(self.field, font=(FONT, 12, 'bold'), anchor='w',
                                   bg=self.colors['white'], fg=self.colors['text'])
        self.text_label.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)

        self.arrow_label = tk.Label(self.field, text="▾", font=(FONT, 12),
                                    bg=self.colors['white'], fg=self.colors['muted'])
        self.arrow_label.pack(side=tk.RIGHT, padx=12)

        for w in (self.field, self.icon_label, self.text_label, self.arrow_label):
            w.bind('<Button-1>', lambda e: self.show_calendar())
            w.bind('<Enter>', lambda e: self._set_hover(True))
            w.bind('<Leave>', lambda e: self._set_hover(False))

        # Sinkronkan tampilan setiap kali variable berubah (dari mana pun)
        self.variable.trace_add('write', lambda *args: self._sync_from_variable())

        if self.variable.get():
            self._sync_from_variable()
        else:
            self.set_date(self.current_date)

    # ---------- API publik ----------
    def set_date(self, date):
        """Set tanggal"""
        if isinstance(date, (datetime.datetime, datetime.date)):
            self.variable.set(date.strftime('%Y-%m-%d'))

    def get_date(self):
        """Get tanggal sebagai datetime"""
        try:
            return datetime.datetime.strptime(self.variable.get(), '%Y-%m-%d')
        except ValueError:
            return self.current_date

    def set_enabled(self, enabled):
        self.enabled = enabled
        fg = self.colors['text'] if enabled else self.colors['disabled_text']
        cursor = 'hand2' if enabled else 'arrow'
        self.text_label.config(fg=fg)
        for w in (self.field, self.icon_label, self.text_label, self.arrow_label):
            w.config(cursor=cursor)

    # ---------- internal ----------
    def _sync_from_variable(self):
        self.current_date = self.get_date()
        self.text_label.config(text=format_tanggal(self.current_date))

    def _set_hover(self, hover):
        if not self.enabled:
            return
        color = self.colors['accent'] if hover else self.colors['border']
        self.field.config(highlightbackground=color)

    def show_calendar(self):
        """Tampilkan popup kalender tepat di bawah field"""
        if not self.enabled:
            return
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return

        top = tk.Toplevel(self)
        self.popup = top
        top.title("Pilih Tanggal")
        top.resizable(False, False)
        top.transient(self.winfo_toplevel())
        top.configure(bg=self.colors['border'])
        top.bind('<Escape>', lambda e: top.destroy())

        card = tk.Frame(top, bg=self.colors['white'], padx=14, pady=12)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Bulan yang sedang ditampilkan (bisa beda dengan tanggal terpilih)
        view = {'year': self.current_date.year, 'month': self.current_date.month}

        # Navigasi bulan
        nav = tk.Frame(card, bg=self.colors['white'])
        nav.pack(fill=tk.X, pady=(0, 8))

        def nav_btn(text, cmd):
            return tk.Button(nav, text=text, command=cmd, font=(FONT, 11, 'bold'),
                             bg=self.colors['white'], fg=self.colors['primary'],
                             activebackground=self.colors['primary_soft'],
                             relief='flat', borderwidth=0, cursor='hand2', width=3)

        title = tk.Label(nav, font=(FONT, 12, 'bold'),
                         bg=self.colors['white'], fg=self.colors['text'])
        nav_btn("‹", lambda: shift(-1)).pack(side=tk.LEFT)
        nav_btn("›", lambda: shift(1)).pack(side=tk.RIGHT)
        title.pack(side=tk.LEFT, expand=True)

        grid = tk.Frame(card, bg=self.colors['white'])
        grid.pack()

        def pick(date):
            self.set_date(date)
            top.destroy()

        def render():
            for w in grid.winfo_children():
                w.destroy()
            title.config(text=f"{BULAN[view['month'] - 1]} {view['year']}")

            for col, name in enumerate(['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']):
                fg = self.colors['danger'] if col == 6 else self.colors['muted']
                tk.Label(grid, text=name, font=(FONT, 9, 'bold'), width=4,
                         bg=self.colors['white'], fg=fg).grid(row=0, column=col, pady=(0, 4))

            today = datetime.date.today()
            selected = self.current_date.date()
            weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(view['year'], view['month'])
            for row, week in enumerate(weeks, start=1):
                for col, day in enumerate(week):
                    if day == 0:
                        continue
                    date = datetime.date(view['year'], view['month'], day)
                    if date == selected:
                        bg, fg, weight = self.colors['accent'], 'white', 'bold'
                    elif date == today:
                        bg, fg, weight = self.colors['primary_soft'], self.colors['primary'], 'bold'
                    else:
                        bg, fg, weight = self.colors['white'], self.colors['text'], 'normal'
                    tk.Button(
                        grid, text=str(day), width=3, font=(FONT, 10, weight),
                        bg=bg, fg=fg, activebackground=darken(bg, 0.93) if bg != 'white' else self.colors['primary_soft'],
                        relief='flat', borderwidth=0, cursor='hand2',
                        command=lambda d=date: pick(datetime.datetime(d.year, d.month, d.day))
                    ).grid(row=row, column=col, padx=1, pady=1, ipady=3)

        def shift(delta):
            month = view['month'] + delta
            view['year'] += (month - 1) // 12
            view['month'] = (month - 1) % 12 + 1
            render()

        render()

        # Footer: shortcut hari ini / kemarin
        footer = tk.Frame(card, bg=self.colors['white'])
        footer.pack(fill=tk.X, pady=(10, 0))
        now = datetime.datetime.now()
        for text, date in (("Hari Ini", now), ("Kemarin", now - datetime.timedelta(days=1))):
            tk.Button(footer, text=text, command=lambda d=date: pick(d),
                      font=(FONT, 9, 'bold'), bg=self.colors['primary_soft'], fg=self.colors['primary'],
                      activebackground=darken(self.colors['primary_soft'], 0.95),
                      relief='flat', borderwidth=0, cursor='hand2', padx=10, pady=4
                      ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(footer, text="Tutup", command=top.destroy,
                  font=(FONT, 9), bg=self.colors['white'], fg=self.colors['muted'],
                  activebackground=self.colors['light'],
                  relief='flat', borderwidth=0, cursor='hand2', padx=10, pady=4
                  ).pack(side=tk.RIGHT)

        # Posisikan di bawah field, tetap di dalam layar
        top.update_idletasks()
        x = self.field.winfo_rootx()
        y = self.field.winfo_rooty() + self.field.winfo_height() + 4
        x = min(x, top.winfo_screenwidth() - top.winfo_reqwidth() - 10)
        if y + top.winfo_reqheight() > top.winfo_screenheight() - 40:
            y = self.field.winfo_rooty() - top.winfo_reqheight() - 4
        top.geometry(f"+{x}+{y}")
        top.grab_set()
        top.focus_set()
