# views/components/simple_datepicker.py
import tkinter as tk
from tkinter import ttk
import datetime
from config.settings import settings

class SimpleDatePicker(tk.Frame):
    """Date picker modern tanpa dependensi babel"""
    
    def __init__(self, master, textvariable=None, **kwargs):
        super().__init__(master, bg='white')
        
        self.variable = textvariable or tk.StringVar()
        self.current_date = datetime.datetime.now()
        self.colors = settings.THEME_COLORS
        self.border_color = self.colors.get('border', '#e5e7eb')
        self.font_family = 'Segoe UI' if self._is_windows() else 'Helvetica'
        
        # Frame untuk entry dan button dengan border
        border_frame = tk.Frame(
            self, 
            bg=self.colors.get('white', 'white'),
            highlightbackground=self.border_color,
            highlightcolor=self.colors.get('primary', '#4338ca'),
            highlightthickness=1
        )
        border_frame.pack(fill=tk.BOTH, expand=True)
        
        # Entry untuk menampilkan tanggal
        self.entry = tk.Entry(
            border_frame,
            textvariable=self.variable,
            font=(self.font_family, 12),
            width=14,
            justify='center',
            state='readonly',
            readonlybackground='white',
            fg=self.colors.get('text', '#1f2937'),
            relief='flat',
            borderwidth=5 # Internal padding
        )
        self.entry.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Tombol untuk memilih tanggal
        self.btn = tk.Button(
            border_frame,
            text="📅",
            font=(self.font_family, 12),
            command=self.show_calendar,
            bg='white',
            fg=self.colors.get('text', '#1f2937'),
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            activebackground=self.colors.get('light', '#f3f4f6')
        )
        self.btn.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # Set default ke hari ini
        self.set_date(self.current_date)
        
    def _is_windows(self):
        import platform
        return platform.system() == 'Windows'
    
    def set_date(self, date):
        """Set tanggal"""
        if isinstance(date, (datetime.datetime, datetime.date)):
            self.variable.set(date.strftime('%Y-%m-%d'))
            self.current_date = date
    
    def get_date(self):
        """Get tanggal sebagai datetime"""
        try:
            return datetime.datetime.strptime(self.variable.get(), '%Y-%m-%d')
        except:
            return self.current_date
    
    def show_calendar(self):
        """Tampilkan popup calendar modern"""
        top = tk.Toplevel(self)
        top.title("Pilih Tanggal")
        top.geometry("340x300") # A bit wider for modern look
        top.transient(self.master)
        top.grab_set()
        top.configure(bg=self.colors.get('light', '#f3f4f6'))
        
        # Center popup
        top.update_idletasks()
        x = (top.winfo_screenwidth() // 2) - (340 // 2)
        y = (top.winfo_screenheight() // 2) - (300 // 2)
        top.geometry(f"+{x}+{y}")
        
        # Main Card
        card = tk.Frame(
            top, 
            bg='white',
            highlightbackground=self.border_color,
            highlightthickness=1
        )
        card.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        tk.Label(
            card,
            text="Pilih Tanggal",
            font=(self.font_family, 14, 'bold'),
            bg='white',
            fg=self.colors.get('primary', '#4338ca')
        ).pack(pady=(15, 10))
        
        # Frame input
        input_frame = tk.Frame(card, bg='white')
        input_frame.pack(pady=10)
        
        def create_spinbox(parent, label_text, row, from_val, to_val, current_val):
            tk.Label(
                parent, 
                text=label_text, 
                bg='white',
                fg=self.colors.get('text', '#1f2937'),
                font=(self.font_family, 11)
            ).grid(row=row, column=0, padx=10, pady=8, sticky='e')
            
            spin_frame = tk.Frame(
                parent,
                highlightbackground=self.border_color,
                highlightthickness=1
            )
            spin_frame.grid(row=row, column=1, padx=10, pady=8)
            
            spin = ttk.Spinbox(
                spin_frame, 
                from_=from_val, 
                to=to_val, 
                width=8,
                font=(self.font_family, 11)
            )
            spin.pack(padx=2, pady=2)
            spin.delete(0, tk.END)
            spin.insert(0, current_val)
            return spin
            
        year_spin = create_spinbox(input_frame, "Tahun:", 0, 2020, 2030, self.current_date.year)
        month_spin = create_spinbox(input_frame, "Bulan:", 1, 1, 12, self.current_date.month)
        day_spin = create_spinbox(input_frame, "Hari:", 2, 1, 31, self.current_date.day)
        
        # Button frame
        btn_frame = tk.Frame(card, bg='white')
        btn_frame.pack(pady=(15, 15))
        
        def select():
            try:
                year = int(year_spin.get())
                month = int(month_spin.get())
                day = int(day_spin.get())
                selected = datetime.datetime(year, month, day)
                self.set_date(selected)
                top.destroy()
            except ValueError:
                tk.messagebox.showerror("Error", "Tanggal tidak valid")
        
        def select_today():
            self.set_date(datetime.datetime.now())
            top.destroy()
            
        def create_btn(parent, text, cmd, bg_col, is_outline=False):
            if is_outline:
                btn_bg = 'white'
                btn_fg = self.colors.get('text', '#1f2937')
            else:
                btn_bg = bg_col
                btn_fg = 'white'
                
            return tk.Button(
                parent,
                text=text,
                command=cmd,
                bg=btn_bg,
                fg=btn_fg,
                font=(self.font_family, 10, 'bold'),
                width=8,
                cursor='hand2',
                relief='flat' if not is_outline else 'solid',
                borderwidth=0 if not is_outline else 1,
                padx=5,
                pady=6
            )
        
        btn_today = create_btn(btn_frame, "Hari Ini", select_today, self.colors.get('accent', '#4f46e5'))
        btn_today.pack(side=tk.LEFT, padx=5)
        
        btn_select = tk.Button(
            btn_frame,
            text="Pilih",
            command=select,
            bg=self.colors.get('success', '#059669'),
            fg='white',
            font=(self.font_family, 10, 'bold'),
            width=8,
            cursor='hand2',
            relief='flat',
            padx=5,
            pady=6
        )
        btn_select.pack(side=tk.LEFT, padx=5)
        
        btn_cancel = create_btn(btn_frame, "Batal", top.destroy, self.colors.get('danger', '#dc2626'), is_outline=True)
        btn_cancel.pack(side=tk.LEFT, padx=5)