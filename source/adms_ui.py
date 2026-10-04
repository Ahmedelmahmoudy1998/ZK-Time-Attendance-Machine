"""Standalone device reception settings and live status."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from adms import configuration, local_addresses, start_receiver
from datepicker import DateField

TRANSLATIONS = {
    'Receive from device (ADMS)': 'استقبال من الجهاز (ADMS)',
    'PC IP address': 'عنوان IP لهذا الكمبيوتر',
    'Device IP address': 'عنوان IP للجهاز',
    'Receiver port': 'منفذ الاستقبال',
    'Start receiver': 'تشغيل الاستقبال', 'Stop receiver': 'إيقاف الاستقبال',
    'Close window': 'إغلاق النافذة', 'Last contact': 'آخر اتصال',
    'Waiting for device': 'بانتظار الجهاز', 'Receiver stopped': 'الاستقبال متوقف',
    'New punches this session': 'البصمات الجديدة في هذه الجلسة',
    'Last saved upload': 'آخر دفعة محفوظة',
    'Received punches': 'البصمات المستلمة',
    'The receiver uses this PC’s clock and time zone.': 'يستخدم الاستقبال ساعة هذا الكمبيوتر ومنطقته الزمنية.',
    'Request older attendance': 'طلب سجلات حضور سابقة',
    'Cancel pending request': 'إلغاء الطلب المعلق',
    'Set the device Cloud Server to ADMS, the PC IP and receiver port shown above, with HTTPS off. BioTime is not needed.': 'اضبط خادم الجهاز على ADMS وعنوان الكمبيوتر ومنفذ الاستقبال أعلاه، مع إيقاف HTTPS. لا يلزم تشغيل BioTime.',
    'Keep Oasis Attend open and logged in. Reception stops on logout, database change or exit. Refresh Attendance or regenerate Reports to see new records.': 'اترك Oasis Attend مفتوحاً مع تسجيل الدخول. يتوقف الاستقبال عند الخروج أو تغيير قاعدة البيانات. حدّث سجل الحضور أو أعد إنشاء التقرير لعرض السجلات الجديدة.',
    'A database backup is created before reception starts. Existing punches and employee details are preserved.': 'تُنشأ نسخة احتياطية قبل بدء الاستقبال. تُحفظ سجلات الحضور وبيانات الموظفين الحالية.',
    'Stop the receiver before changing its settings.': 'أوقف الاستقبال قبل تغيير إعداداته.',
    'Start the receiver first.': 'شغّل الاستقبال أولاً.',
    'The device rejected the direct download (6001). Use Receive from device (ADMS) to receive attendance without BioTime. Open receiver settings?': 'رفض الجهاز التنزيل المباشر (6001). استخدم الاستقبال من الجهاز (ADMS) لاستلام الحضور دون BioTime. هل تريد فتح إعدادات الاستقبال؟',
    'Start with the device serial number from its information screen.': 'أدخل الرقم التسلسلي من شاشة معلومات الجهاز.',
}


def stop_receiver(app):
    receiver = getattr(app, 'adms_receiver', None)
    if receiver:
        receiver.stop()
        app.adms_receiver = None


def open_adms(app, device=None):
    app.store.require('admin')
    if app.busy:
        raise ValueError('Wait for the current download/import to finish.')
    old = getattr(app, 'adms_dialog', None)
    if old and old.winfo_exists():
        old.lift()
        return old
    device = device or {}
    tr = app.tr
    top = tk.Toplevel(app)
    app.adms_dialog = top
    top.title(tr('Receive from device (ADMS)'))
    top.transient(app)
    top.configure(background=app.colors['bg'])
    box = ttk.Frame(top, padding=20)
    box.pack(fill='both', expand=True)
    box.columnconfigure(1, weight=1)
    addresses = local_addresses()
    saved = app.settings.get('adms', {}).get(app.store.path, {})
    receiver = getattr(app, 'adms_receiver', None)
    if receiver:
        saved = receiver.config
    defaults = {'host': addresses[0] if addresses else '', 'port': 8081,
                'peer': device.get('ip', ''), 'serial': app.settings.get('biotime', {}).get('serial', '')}
    fields, entries = {}, []
    for i, (key, label) in enumerate((('host', 'PC IP address'), ('port', 'Receiver port'),
                                    ('peer', 'Device IP address'), ('serial', 'Device serial number'))):
        ttk.Label(box, text=tr(label)).grid(row=i, column=0, sticky='e', padx=10, pady=5)
        var = tk.StringVar(value=saved.get(key, defaults[key]))
        fields[key] = var
        entry = (ttk.Combobox(box, textvariable=var, values=addresses, width=36) if key == 'host'
                 else ttk.Entry(box, textvariable=var, width=38))
        entry.grid(row=i, column=1, sticky='ew')
        entries.append(entry)
    for i, label in enumerate((
            'Set the device Cloud Server to ADMS, the PC IP and receiver port shown above, with HTTPS off. BioTime is not needed.',
            'Keep Oasis Attend open and logged in. Reception stops on logout, database change or exit. Refresh Attendance or regenerate Reports to see new records.',
            'A database backup is created before reception starts. Existing punches and employee details are preserved.'), 4):
        ttk.Label(box, text=tr(label), wraplength=610).grid(row=i, column=0, columnspan=2, sticky='w', pady=6)
    status = tk.StringVar()
    ttk.Label(box, textvariable=status, wraplength=610).grid(row=7, column=0, columnspan=2, sticky='w', pady=10)
    bar = ttk.Frame(box)
    bar.grid(row=8, column=0, columnspan=2)

    def start():
        if app.busy:
            raise ValueError('Wait for the current download/import to finish.')
        if getattr(app, 'adms_receiver', None):
            raise ValueError('Stop the receiver before changing its settings.')
        config = configuration(**{key: var.get().strip() for key, var in fields.items()})
        app.adms_receiver, backup = start_receiver(app.store, config, app.config_dir / 'backups')
        app.settings.setdefault('adms', {})[app.store.path] = config
        app.remember()
        messagebox.showinfo(tr('Start receiver'), f'{config["host"]}:{config["port"]}\n\n{tr("Backup")}: {backup}', parent=top)

    start_button = app.button(bar, 'Start receiver', start)
    start_button.configure(style='Primary.TButton')
    stop_button = app.button(bar, 'Stop receiver', lambda: stop_receiver(app))
    app.button(bar, 'Close window', top.destroy)
    dates = ttk.Frame(box)
    dates.grid(row=9, column=0, columnspan=2, pady=10)
    begin = DateField(dates, 'Start date', date.today().replace(day=1), lambda: None, tr, app.lang == 'ar')
    finish = DateField(dates, 'End date', date.today(), lambda: None, tr, app.lang == 'ar')
    begin.pack(side='left', padx=8)
    finish.pack(side='left', padx=8)
    history = ttk.Frame(box)
    history.grid(row=10, column=0, columnspan=2)
    ttk.Label(box, text=tr('The receiver uses this PC’s clock and time zone.'), style='Muted.TLabel').grid(row=11, column=0, columnspan=2, pady=6)

    def request_history(cancel=False):
        current = getattr(app, 'adms_receiver', None)
        if not current:
            raise ValueError('Start the receiver first.')
        if cancel:
            current.cancel_history()
        else:
            current.request_history(begin.value.isoformat(), finish.value.isoformat())

    app.button(history, 'Request older attendance', request_history)
    app.button(history, 'Cancel pending request', lambda: request_history(True))

    def refresh():
        if not top.winfo_exists():
            return
        current = getattr(app, 'adms_receiver', None)
        start_button.configure(state='disabled' if current else 'normal')
        stop_button.configure(state='normal' if current else 'disabled')
        for entry in entries:
            entry.configure(state='disabled' if current else 'normal')
        if current:
            data = current.status()
            status.set(f'{current.config["host"]}:{current.config["port"]}\n'
                       f'{tr("Last contact")}: {data["last_seen"] or tr("Waiting for device")}\n'
                       f'{tr("Last saved upload")}: {data["last_upload"] or "—"}\n'
                       f'{tr("Received punches")}: {data["received_punches"]}\n'
                       f'{tr("New punches this session")}: {data["new_punches"]}\n'
                       f'{data["error"] or data["command"]}')
        else:
            status.set(tr('Receiver stopped'))
        app.after(1000, refresh)

    refresh()
    return top
