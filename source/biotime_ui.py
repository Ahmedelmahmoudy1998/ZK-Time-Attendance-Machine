"""BioTime import dialog; passwords/tokens never enter saved settings."""
import sqlite3
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path
from biotime import BioTimeClient, server_url
from datepicker import DateField

TRANSLATIONS = {
    'The device rejected the direct download (6001). If it is connected to BioTime, import its attendance through BioTime. Open Import from BioTime now?': 'رفض الجهاز التنزيل المباشر (6001). إذا كان متصلاً بـ BioTime، يمكنك استيراد الحضور من خلاله. هل تريد فتح الاستيراد من BioTime الآن؟',
    'Import from BioTime': 'استيراد من BioTime',
    'BioTime server URL': 'عنوان خادم BioTime',
    'BioTime username': 'اسم مستخدم BioTime',
    'BioTime password': 'كلمة مرور BioTime',
    'Device serial number': 'الرقم التسلسلي للجهاز',
    'Read attendance': 'قراءة الحضور',
    'Import preview': 'معاينة الاستيراد',
    'Import these records?': 'هل تريد استيراد هذه السجلات؟',
    'Employees': 'الموظفون', 'Punches': 'البصمات',
    'New employees': 'موظفون جدد', 'New punches': 'بصمات جديدة',
    'Backup': 'نسخة احتياطية',
    'No attendance records for this device and date range.': 'لا توجد سجلات حضور لهذا الجهاز خلال الفترة المحددة.',
    'Use your BioTime login. The password is not saved.': 'استخدم حساب BioTime. لا تُحفظ كلمة المرور.',
    'Reads attendance already received by BioTime. Existing employees and punches are preserved.': 'يقرأ الحضور الذي استلمه BioTime. تُحفظ بيانات الموظفين والبصمات الموجودة دون تغيير.',
    'Find the serial number in BioTime → Device.': 'ستجد الرقم التسلسلي في BioTime ← الأجهزة.',
    'Keep BioTime running and the terminal connected to its ADMS server.': 'اترك BioTime قيد التشغيل والجهاز متصلاً بخادم ADMS الخاص به.',
    'Enter your BioTime username and password.': 'أدخل اسم المستخدم وكلمة المرور لحساب BioTime.',
    'Enter the device serial number shown in BioTime.': 'أدخل الرقم التسلسلي للجهاز كما يظهر في BioTime.',
    'Choose valid start and end dates.': 'اختر تاريخ بداية ونهاية صحيحين.',
    'Choose a date range of no more than 367 days, with start before end.': 'اختر فترة لا تتجاوز ٣٦٧ يوماً، ويكون تاريخ البداية قبل النهاية أو مساوياً لها.',
    'Use HTTPS for a remote BioTime server, or http://127.0.0.1 for BioTime on this PC.': 'استخدم HTTPS لخادم BioTime على كمبيوتر آخر، أو http://127.0.0.1 على هذا الكمبيوتر.',
    'Enter the BioTime server URL, for example http://127.0.0.1.': 'أدخل عنوان خادم BioTime، مثل http://127.0.0.1.',
    'BioTime login failed. Check your BioTime username and password.': 'تعذر تسجيل الدخول إلى BioTime. تحقق من اسم المستخدم وكلمة المرور.',
    'BioTime denied API access. Check account permissions and API availability in BioTime.': 'رفض BioTime الوصول عبر API. تحقق من صلاحيات الحساب وإتاحة API في BioTime.',
    'BioTime redirected the request. Enter its direct server URL.': 'أعاد BioTime توجيه الطلب. أدخل عنوان الخادم المباشر.',
    'Cannot reach BioTime securely. Check the server address, service and HTTPS certificate.': 'تعذر الاتصال بـ BioTime. تحقق من عنوان الخادم وتشغيل الخدمة وصلاحية شهادة HTTPS.',
    'BioTime returned an unexpected response. Check its API availability.': 'أعاد BioTime استجابة غير متوقعة. تحقق من إتاحة API.',
    'BioTime did not return an API token. Check API availability for your account.': 'لم يُصدر BioTime رمز وصول API. تحقق من إتاحة API لحسابك.',
    'BioTime returned too much data. Choose a shorter date range.': 'أعاد BioTime بيانات كثيرة. اختر فترة أقصر.',
    'BioTime download did not finish. Choose a shorter date range and retry.': 'لم يكتمل التنزيل من BioTime. اختر فترة أقصر وأعد المحاولة.',
    'BioTime returned an invalid attendance page. Nothing was imported.': 'أعاد BioTime صفحة حضور غير صالحة. لم يتم استيراد أي بيانات.',
    'BioTime attendance changed during download. Retry to obtain a complete import.': 'تغيرت سجلات BioTime أثناء التنزيل. أعد المحاولة للحصول على بيانات مكتملة.',
    'BioTime returned duplicate or invalid page records. Nothing was imported.': 'أعاد BioTime سجلات مكررة أو غير صالحة. لم يتم الاستيراد.',
    'BioTime returned an invalid punch date. Nothing was imported.': 'أعاد BioTime تاريخ بصمة غير صالح. لم يتم الاستيراد.',
    'BioTime returned a record outside the selected device/date range or an invalid badge/time. Nothing was imported.': 'تحتوي استجابة BioTime على سجل خارج الجهاز أو الفترة المحددة، أو رقم موظف أو وقت غير صالح. لم يتم الاستيراد.',
    'BioTime returned an invalid department. Nothing was imported.': 'أعاد BioTime قسماً غير صالح. لم يتم الاستيراد.',
    'BioTime returned invalid pagination. Nothing was imported.': 'تعذر التحقق من صفحات BioTime. لم يتم الاستيراد.',
    'BioTime returned an unsafe pagination address. Nothing was imported.': 'أعاد BioTime عنوان صفحة غير آمن. لم يتم الاستيراد.',
    'BioTime returned an incomplete download. Nothing was imported.': 'أعاد BioTime بيانات غير مكتملة. لم يتم الاستيراد.',
}


def import_records(store, data, source, backup_dir):
    """Back up the selected Oasis database before the atomic, additive import."""
    store.require('admin')
    folder = Path(backup_dir)
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('before-biotime-' + uuid.uuid4().hex + '.sqlite')
    target = sqlite3.connect(backup)
    try:
        store.db.backup(target)
    finally:
        target.close()
    before = [store.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
              for table in ('employees', 'punches')]
    store.ingest(*data, source=source)
    after = [store.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
             for table in ('employees', 'punches')]
    return after[0] - before[0], after[1] - before[1], backup


def open_biotime(app):
    app.store.require('admin')
    if app.busy:
        raise ValueError('Wait for the current download/import to finish.')
    tr = app.tr
    top = tk.Toplevel(app)
    top.title(tr('Import from BioTime'))
    top.transient(app)
    top.configure(background=app.colors['bg'])
    top.grab_set()
    box = ttk.Frame(top, padding=22)
    box.pack(fill='both', expand=True)
    box.columnconfigure(1, weight=1)
    saved = app.settings.get('biotime', {})
    fields = {}
    for i, (key, label, default) in enumerate((
            ('url', 'BioTime server URL', 'http://127.0.0.1'),
            ('username', 'BioTime username', ''),
            ('password', 'BioTime password', ''),
            ('serial', 'Device serial number', ''))):
        ttk.Label(box, text=tr(label)).grid(row=i, column=0, sticky='e', padx=(0, 12), pady=7)
        var = tk.StringVar(value='' if key == 'password' else saved.get(key, default))
        fields[key] = var
        ttk.Entry(box, textvariable=var, show='•' if key == 'password' else '', width=42
                  ).grid(row=i, column=1, sticky='ew')
    ttk.Label(box, text=tr('Find the serial number in BioTime → Device.'), style='Muted.TLabel'
              ).grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
    dates = ttk.Frame(box)
    dates.grid(row=5, column=0, columnspan=2, sticky='w', pady=10)
    start = DateField(dates, 'Start date', date.today().replace(day=1), lambda: None, tr, app.lang == 'ar')
    end = DateField(dates, 'End date', date.today(), lambda: None, tr, app.lang == 'ar')
    start.pack(side='left', padx=(0, 16)); end.pack(side='left')
    for row, label in enumerate((
            'Use your BioTime login. The password is not saved.',
            'Reads attendance already received by BioTime. Existing employees and punches are preserved.',
            'Keep BioTime running and the terminal connected to its ADMS server.'), 6):
        ttk.Label(box, text=tr(label), wraplength=580).grid(row=row, column=0, columnspan=2, sticky='w', pady=4)
    bar = ttk.Frame(box)
    bar.grid(row=9, column=0, columnspan=2, pady=(14, 0))

    def close():
        if app.busy:
            raise ValueError('Wait for the current download/import to finish.')
        fields['password'].set('')
        top.destroy()

    def submit():
        if app.busy:
            raise ValueError('Wait for the current download/import to finish.')
        url = server_url(fields['url'].get())
        username, password = fields['username'].get().strip(), fields['password'].get()
        serial = fields['serial'].get().strip()
        begin, finish = start.value.isoformat(), end.value.isoformat()
        if not username or not password:
            raise ValueError('Enter your BioTime username and password.')
        if not serial:
            raise ValueError('Enter the device serial number shown in BioTime.')
        if start.value > end.value or (end.value - start.value).days > 366:
            raise ValueError('Choose a date range of no more than 367 days, with start before end.')
        fields['password'].set('')

        def done(data):
            app.settings['biotime'] = {'url': url, 'username': username, 'serial': serial}
            app.remember()
            employees, punches = data
            if not punches:
                messagebox.showinfo(tr('Import from BioTime'), tr('No attendance records for this device and date range.'), parent=top)
                return
            preview = (f'{url}\n{serial}\n{begin} → {finish}\n\n'
                       f'{tr("Employees")}: {len(employees)}\n{tr("Punches")}: {len(punches)}\n\n'
                       + tr('Import these records?'))
            if not messagebox.askyesno(tr('Import preview'), preview, parent=top):
                return
            new_employees, new_punches, backup = import_records(
                app.store, data, f'BioTime {url} / {serial}', app.config_dir / 'backups')
            top.destroy()
            app.home()
            messagebox.showinfo(tr('Import from BioTime'),
                                f'{tr("New employees")}: {new_employees}\n{tr("New punches")}: {new_punches}\n\n'
                                f'{tr("Backup")}: {backup}', parent=app)

        app.background(lambda: BioTimeClient(url).download(username, password, serial, begin, finish), done)

    app.button(bar, 'Read attendance', submit).configure(style='Primary.TButton')
    app.button(bar, 'Cancel', close)
    top.protocol('WM_DELETE_WINDOW', lambda: app.guard(close))
    return top
