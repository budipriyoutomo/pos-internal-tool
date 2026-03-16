import os
import locale

# Paksa locale supaya tidak membaca 'eng'
os.environ["LC_ALL"] = "C"
os.environ["LANG"] = "C"

try:
    locale.setlocale(locale.LC_ALL, "C")
except:
    pass