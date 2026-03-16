# views/components/simple_datepicker.py
import tkinter as tk
from tkinter import ttk
import datetime

class SimpleDatePicker(tk.Frame):
    """Date picker tanpa dependensi babel"""
    
    def __init__(self, master, textvariable=None, **kwargs):
        super().__init__(master, bg='white')
        
        self.variable = textvariable or tk.StringVar()
        self.current_date = datetime.datetime.now()
        
        # Frame untuk entry dan button
        entry_frame = tk.Frame(self, bg='white')
        entry_frame.pack()
        
        # Entry untuk menampilkan tanggal
        self.entry = tk.Entry(
            entry_frame,
            textvariable=self.variable,
            font=('Helvetica', 12),
            width=15,
            justify='center',
            state='readonly'
        )
        self.entry.pack(side=tk.LEFT, padx=5)
        
        # Tombol untuk memilih tanggal
        self.btn = tk.Button(
            entry_frame,
            text="📅",
            font=('Helvetica', 12),
            command=self.show_calendar,
            width=3,
            cursor='hand2'
        )
        self.btn.pack(side=tk.LEFT)
        
        # Set default ke hari ini
        self.set_date(self.current_date)
    
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
        """Tampilkan popup calendar sederhana"""
        top = tk.Toplevel(self)
        top.title("Pilih Tanggal")
        top.geometry("300x250")
        top.transient(self.master)
        top.grab_set()
        top.configure(bg='white')
        
        # Center popup
        top.update_idletasks()
        x = (top.winfo_screenwidth() // 2) - (300 // 2)
        y = (top.winfo_screenheight() // 2) - (250 // 2)
        top.geometry(f"+{x}+{y}")
        
        # Title
        tk.Label(
            top,
            text="Pilih Tanggal",
            font=('Helvetica', 14, 'bold'),
            bg='white'
        ).pack(pady=10)
        
        # Frame input
        input_frame = tk.Frame(top, bg='white')
        input_frame.pack(pady=10)
        
        # Year
        tk.Label(input_frame, text="Tahun:", bg='white').grid(row=0, column=0, padx=5)
        year_spin = tk.Spinbox(
            input_frame, 
            from_=2020, 
            to=2030, 
            width=8,
            font=('Helvetica', 11)
        )
        year_spin.grid(row=0, column=1, padx=5)
        year_spin.delete(0, tk.END)
        year_spin.insert(0, self.current_date.year)
        
        # Month
        tk.Label(input_frame, text="Bulan:", bg='white').grid(row=1, column=0, padx=5)
        month_spin = tk.Spinbox(
            input_frame, 
            from_=1, 
            to=12, 
            width=8,
            font=('Helvetica', 11)
        )
        month_spin.grid(row=1, column=1, padx=5)
        month_spin.delete(0, tk.END)
        month_spin.insert(0, self.current_date.month)
        
        # Day
        tk.Label(input_frame, text="Hari:", bg='white').grid(row=2, column=0, padx=5)
        day_spin = tk.Spinbox(
            input_frame, 
            from_=1, 
            to=31, 
            width=8,
            font=('Helvetica', 11)
        )
        day_spin.grid(row=2, column=1, padx=5)
        day_spin.delete(0, tk.END)
        day_spin.insert(0, self.current_date.day)
        
        # Button frame
        btn_frame = tk.Frame(top, bg='white')
        btn_frame.pack(pady=15)
        
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
        
        tk.Button(
            btn_frame,
            text="Pilih",
            command=select,
            bg='#27ae60',
            fg='white',
            font=('Helvetica', 11, 'bold'),
            width=8,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Hari Ini",
            command=select_today,
            bg='#3498db',
            fg='white',
            font=('Helvetica', 11),
            width=8,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Batal",
            command=top.destroy,
            bg='#e74c3c',
            fg='white',
            font=('Helvetica', 11),
            width=8,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=5)