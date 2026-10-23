# views/components/widgets.py
"""Komponen UI kecil yang dipakai ulang: tombol modern, badge status, format tanggal."""
import platform
import tkinter as tk

from config.settings import settings

FONT = 'Segoe UI' if platform.system() == 'Windows' else 'Helvetica'

# Locale aplikasi dipaksa en_US (lihat main.py), jadi nama hari/bulan ditulis manual
HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
BULAN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
         'Agustus', 'September', 'Oktober', 'November', 'Desember']


def format_tanggal(date):
    """datetime -> 'Kamis, 23 Oktober 2026'"""
    return f"{HARI[date.weekday()]}, {date.day} {BULAN[date.month - 1]} {date.year}"


def darken(hex_color, factor=0.88):
    """Gelapkan warna hex untuk efek hover/active"""
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"
    except (ValueError, TypeError):
        return f"#{hex_color}"


class ModernButton(tk.Button):
    """Tombol flat dengan efek hover dan state enabled/disabled yang konsisten"""

    def __init__(self, master, text, command, variant='primary', size='md', **kwargs):
        c = settings.THEME_COLORS
        # variant -> (background, foreground)
        variants = {
            'primary': (c['accent'], 'white'),
            'success': (c['success'], 'white'),
            'soft': (c['primary_soft'], c['primary']),
            'ghost': (c['white'], c['text']),
        }
        self.colors = c
        self.variant_bg, self.variant_fg = variants.get(variant, variants['primary'])
        font_size, pad_x, pad_y = {'sm': (10, 12, 5), 'md': (11, 18, 9), 'lg': (12, 22, 12)}[size]

        super().__init__(
            master,
            text=text,
            command=command,
            bg=self.variant_bg,
            fg=self.variant_fg,
            activebackground=darken(self.variant_bg),
            activeforeground=self.variant_fg,
            disabledforeground=c['disabled_text'],
            font=(FONT, font_size, 'bold'),
            relief='flat',
            borderwidth=0,
            highlightthickness=1 if variant == 'ghost' else 0,
            highlightbackground=c['border'],
            cursor='hand2',
            padx=pad_x,
            pady=pad_y,
            **kwargs
        )
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, _event):
        if str(self['state']) != 'disabled':
            self.config(bg=darken(self.variant_bg, 0.94))

    def _on_leave(self, _event):
        if str(self['state']) != 'disabled':
            self.config(bg=self.variant_bg)

    def set_variant_colors(self, bg, fg):
        """Ganti warna tombol (mis. chip aktif/tidak aktif)"""
        self.variant_bg, self.variant_fg = bg, fg
        if str(self['state']) != 'disabled':
            self.config(bg=bg, fg=fg, activebackground=darken(bg), activeforeground=fg)

    def set_enabled(self, enabled):
        if enabled:
            self.config(state='normal', bg=self.variant_bg, fg=self.variant_fg, cursor='hand2')
        else:
            self.config(state='disabled', bg=self.colors['disabled'], cursor='arrow')


class StatusBadge(tk.Label):
    """Badge kecil berwarna untuk status sebuah langkah"""

    def __init__(self, master, **kwargs):
        c = settings.THEME_COLORS
        # state -> (teks, background, foreground)
        self.states = {
            'idle': ("Belum", c['light'], c['muted']),
            'running': ("⏳ Berjalan", c['warning_soft'], c['warning']),
            'success': ("✓ Selesai", c['success_soft'], c['success']),
            'error': ("✕ Gagal", c['danger_soft'], c['danger']),
        }
        super().__init__(master, font=(FONT, 9, 'bold'), padx=8, pady=2, **kwargs)
        self.set_state('idle')

    def set_state(self, state):
        text, bg, fg = self.states[state]
        self.config(text=text, bg=bg, fg=fg)
