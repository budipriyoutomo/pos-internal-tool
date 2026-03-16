# pos_closing_clean.spec

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

mysql_datas = collect_data_files('mysql.connector')

datas = [
    ('config.ini.example', '.'),
    ('README.md', '.'),
] + mysql_datas

hiddenimports = [
    'mysql.connector',
    'mysql.connector.plugins',
    'mysql.connector.locales.eng',
    'configparser',
    'datetime',
    'email.message',
    'smtplib',
    'ssl',
    'threading',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'requests',
    'csv',
    'io',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['locale_fix.py'],
    excludes=['babel', 'tkcalendar'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='POS_Closing',
    console=False,
)