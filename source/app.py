import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, json, calendar, threading, queue, sys
from pathlib import Path
from datetime import date, timedelta
from core import Store, monthly, export_csv
from connectors import read_mdb, download
from settings import migrate_settings
from appearance import apply_theme
from branding import brand_asset
from company_profile import normalize_logo, MAX_LOGO_BYTES
from report_exports import asset, PRODUCER, COPYRIGHT, export_pdf, export_excel, export_print_html
from datepicker import DateRange, preset_range
from biotime_ui import open_biotime, TRANSLATIONS as BIOTIME_TRANSLATIONS
from device_session import DirectConnectionRejected
from adms_ui import open_adms, stop_receiver, TRANSLATIONS as ADMS_TRANSLATIONS

AR={'Oasis Attend':'حضور أوايسس','Dashboard':'الرئيسية','Employees':'الموظفون','Attendance':'سجل الحضور','Shifts':'الورديات','Assignments':'تعيين الورديات','Reports':'التقارير','Devices':'الأجهزة','Accounts':'الحسابات','Settings':'الإعدادات','Audit':'سجل العمليات','Logout':'تسجيل الخروج','Save':'حفظ','Cancel':'إلغاء','Add / Edit':'إضافة / تعديل','Refresh':'تحديث','Export CSV':'تصدير CSV','Download users + logs':'تنزيل المستخدمين والحضور','Import ZKTime MDB':'استيراد قاعدة ZKTime','Generate':'إنشاء التقرير','Daily':'يومي','Monthly':'شهري','Period':'فترة محددة','Remove selected':'حذف التعيين المحدد','Create shift':'إنشاء وردية','Assign shift':'تعيين وردية','Backup database':'نسخ احتياطي','Choose database':'اختيار قاعدة البيانات','Login':'دخول','Username':'اسم المستخدم','Password':'كلمة المرور','Create administrator':'إنشاء حساب المدير','Database':'قاعدة البيانات','Role':'الصلاحية','Name':'الاسم','Badge':'رقم الموظف','Department':'القسم','Active (1/0)':'نشط (1/0)','Start (HH:MM)':'البداية (ساعة:دقيقة)','End (HH:MM)':'النهاية (ساعة:دقيقة)','Grace minutes':'دقائق السماح','Break minutes':'دقائق الاستراحة','Weekdays (Mon=0, Sun=6)':'أيام الأسبوع (الاثنين=0، الأحد=6)','From (YYYY-MM-DD)':'من (سنة-شهر-يوم)','To (YYYY-MM-DD)':'إلى (سنة-شهر-يوم)','Shift ID':'رقم الوردية','IP address':'عنوان IP','Port':'المنفذ','UDP (1/0)':'UDP (1/0)','Communication key (0 if none)':'مفتاح الاتصال (0 إن لم يوجد)','All employees: leave badge empty':'كل الموظفين: اترك الرقم فارغاً','Ready':'جاهز','Working…':'جارٍ العمل…','Present':'حاضر','Absent':'غائب','Late':'متأخر','Missing punch':'بصمة ناقصة','Off / Unscheduled':'راحة / غير مجدول','date':'التاريخ','badge':'رقم الموظف','name':'الاسم','department':'القسم','shift':'الوردية','first':'أول بصمة','last':'آخر بصمة','punches':'البصمات','worked_minutes':'دقائق العمل','late_minutes':'دقائق التأخير','early_minutes':'دقائق الخروج المبكر','status':'الحالة','active':'نشط','stamp':'الوقت','kind':'النوع','source':'المصدر','id':'الرقم','start':'البداية','end':'النهاية','grace':'السماح','break_mins':'الاستراحة','days':'الأيام','begin':'من','finish':'إلى','shift_id':'رقم الوردية','username':'المستخدم','role':'الصلاحية','actor':'المستخدم','action':'العملية','present_days':'أيام الحضور','absent_days':'أيام الغياب','missing_punch_days':'أيام البصمة الناقصة'}

AR.update({'New':'جديد','Pending':'لم تبدأ الوردية','In progress':'الوردية جارية','Invalid username or password.':'اسم المستخدم أو كلمة المرور غير صحيحة.','Account temporarily locked. Try again in 5 minutes.':'الحساب مقفل مؤقتاً. حاول بعد خمس دقائق.','Select a row first.':'اختر صفاً أولاً.','No rows to export.':'لا توجد بيانات للتصدير.','Badge and name are required.':'الرقم والاسم مطلوبان.','Your account does not have permission for this action.':'حسابك لا يملك صلاحية تنفيذ هذا الإجراء.','No records':'لا توجد سجلات','Use a username, a password of at least 8 characters, and a valid role.':'أدخل اسم المستخدم وكلمة مرور لا تقل عن ثمانية أحرف وصلاحية صحيحة.'})

AR.update({'From':'من','To':'إلى','Calendar':'التقويم','If the device has a COMM Key set under Comm. > Security, enter that number when downloading.':'إذا كان الجهاز مضبوطاً عليه COMM Key من Comm. > Security أدخل نفس الرقم عند التنزيل.','Report type':'نوع التقرير','Summary':'الملخص','Attendance today':'حضور اليوم','Total':'الإجمالي','Rows':'عدد الصفوف','Days present':'أيام الحضور','Worked hours':'ساعات العمل','Late minutes':'دقائق التأخير','Early leave minutes':'دقائق الخروج المبكر','Late days':'أيام التأخير','Absent days':'أيام الغياب','Missing punch days':'أيام البصمة الناقصة','No attendance records for today.':'لا توجد سجلات حضور لليوم.','Import a ZKTime database or download from a device to see today here.':'استورد قاعدة ZKTime أو نزّل من الجهاز ليظهر حضور اليوم هنا.','Remove device':'حذف الجهاز','Remove this device from the list?':'حذف هذا الجهاز من القائمة؟','Attendance records already downloaded from it are kept.':'سجلات الحضور التي نزلت منه تبقى كما هي.','Device removed':'تم حذف الجهاز','That device no longer exists. Refresh the list.':'هذا الجهاز لم يعد موجوداً. حدّث القائمة.','Start date':'تاريخ البداية','End date':'تاريخ النهاية','Choose date':'اختر التاريخ','The end date is before the start date.':'تاريخ النهاية قبل تاريخ البداية.','No daily rows for this period. The punches exist but their badges are not in the employee list. Use Show raw punches, or import the employees.':'لا توجد صفوف يومية في هذه الفترة. البصمات موجودة لكن أرقامها غير مسجلة في قائمة الموظفين. استخدم عرض البصمات الخام أو استورد الموظفين.','Today':'اليوم','Yesterday':'أمس','This week':'هذا الأسبوع','This month':'هذا الشهر','Last month':'الشهر الماضي','Full range':'كل الفترة','Print PDF':'طباعة PDF','Show raw punches':'عرض البصمات الخام','Show daily summary':'عرض الملخص اليومي','in':'الدخول','out':'الخروج','worked':'ساعات العمل','weekday':'اليوم','note':'ملاحظة','Missing out punch':'بصمة انصراف ناقصة','Odd punch count':'عدد بصمات فردي','Worked is last punch minus first punch. Breaks are not deducted.':'ساعات العمل = آخر بصمة ناقص أول بصمة، دون خصم الاستراحة.','The From date must not be after the To date.':'تاريخ البداية يجب ألا يتجاوز تاريخ النهاية.','No attendance records for this period.':'لا توجد سجلات حضور في هذه الفترة.','No punches in the database yet. Import a ZKTime database or download from a device first.':'لا توجد بصمات بعد. استورد قاعدة ZKTime أو نزّل البيانات من الجهاز أولاً.','Results were trimmed. Narrow the period or choose one employee.':'تم اختصار النتائج. اختر فترة أقصر أو موظفاً واحداً.','Mon':'اثنين','Tue':'ثلاثاء','Wed':'أربعاء','Thu':'خميس','Fri':'جمعة','Sat':'سبت','Sun':'أحد','January':'يناير','February':'فبراير','March':'مارس','April':'أبريل','May':'مايو','June':'يونيو','July':'يوليو','August':'أغسطس','September':'سبتمبر','October':'أكتوبر','November':'نوفمبر','December':'ديسمبر'})

AR.update({'Employee':'الموظف','All employees':'كل الموظفين','Export PDF':'تصدير PDF','Export Excel':'تصدير Excel','Print preview':'معاينة الطباعة','Database selection is remembered automatically.':'يتم حفظ اختيار قاعدة البيانات تلقائياً.','Select a saved database or restore its location.':'اختر قاعدة بيانات محفوظة أو أعدها إلى موقعها.'})

AR.update({'Company details':'بيانات الشركة','Company name':'اسم الشركة','Branch':'الفرع','Company logo':'شعار الشركة','Choose logo':'اختيار الشعار','Remove logo':'إزالة الشعار','No company logo':'لم يُحدد شعار للشركة','Company details saved.':'تم حفظ بيانات الشركة.','Saved in the selected database and included in reports.':'تُحفظ في قاعدة البيانات المختارة وتظهر في التقارير.','Choose a PNG or JPEG logo no larger than 5 MB.':'اختر شعار PNG أو JPEG بحجم لا يتجاوز 5 ميجابايت.','Choose a valid PNG or JPEG logo (up to 16 million pixels).':'اختر صورة PNG أو JPEG صالحة لا تتجاوز 16 مليون بكسل.','Company and branch must each be one line of up to 160 characters.':'اسم الشركة والفرع: سطر واحد لكل منهما لا يتجاوز 160 حرفاً.'})

AR.update({'comm_key':'مفتاح الاتصال','Save the device communication key beside its IP address. Downloads use this saved value.':'احفظ مفتاح اتصال الجهاز بجوار عنوان IP. يُستخدم المفتاح المحفوظ عند التنزيل.'})

AR.update({'Appearance':'المظهر','Light':'فاتح','Dark':'داكن','Choose light or dark. Your choice is saved on this PC.':'اختر المظهر الفاتح أو الداكن. يُحفظ اختيارك على هذا الكمبيوتر.'})

AR.update(BIOTIME_TRANSLATIONS)
AR.update(ADMS_TRANSLATIONS)

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Oasis Attend | Attendance'); self.geometry('1220x780'); self.minsize(980,680)
        self.config_dir=Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'Oasis Attend'; self.config_dir.mkdir(parents=True,exist_ok=True)
        self.config_file=migrate_settings(self.config_dir.parent)
        try: self.settings=json.loads(self.config_file.read_text('utf-8'))
        except (OSError,ValueError): self.settings={}
        self.lang=self.settings.get('language','en'); self.store=None; self.busy=False; self.results=queue.Queue()
        self.theme_var=tk.StringVar(value=self.settings.get('appearance','light'))
        apply_theme(self,self.theme_var.get()); self.theme_var.set(self.theme)
        self.iconbitmap(default=str(brand_asset('app-icon.ico')))
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.startup_id=self.after(50,self.open_database); self.after(100,self.poll)

    def change_appearance(self):
        apply_theme(self,self.theme_var.get())
        self.settings['appearance']=self.theme
        self.remember()

    def appearance_picker(self,parent,side=None):
        box=ttk.Frame(parent,padding=(8,4))
        box.pack(side=side or 'top',pady=3)
        ttk.Label(box,text=self.tr('Appearance'),style='Muted.TLabel').pack(side='left',padx=(0,8))
        for mode,label in (('light','Light'),('dark','Dark')):
            ttk.Radiobutton(box,text=self.tr(label),variable=self.theme_var,value=mode,
                            command=lambda:self.guard(self.change_appearance)).pack(side='left',padx=3)
        return box

    def tr(self,s): return AR.get(s,s) if self.lang=='ar' else s
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def remember(self):
        self.settings['language']=self.lang
        pending=self.config_file.with_suffix('.tmp')
        pending.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(pending,self.config_file)
    def guard(self,fn):
        try: return fn()
        except Exception as e: messagebox.showerror('Oasis Attend',self.tr(str(e)),parent=self)
    def button(self,parent,label,fn):
        b=ttk.Button(parent,text=self.tr(label),style='Primary.TButton' if label in ('Login','Create administrator','Save','Generate','Print preview','Download users + logs') else 'TButton',command=lambda:self.guard(fn)); b.pack(side='left',padx=4,pady=4); return b
    def form(self,title,fields,callback):
        top=tk.Toplevel(self); top.title(self.tr(title)); top.transient(self); top.grab_set(); box=ttk.Frame(top,padding=22); box.pack(fill='both',expand=True); values={}
        for i,(label,value,choices) in enumerate(fields):
            ttk.Label(box,text=self.tr(label)).grid(row=i,column=0,sticky='e',padx=10,pady=7)
            var=tk.StringVar(value=str(value)); values[label]=var
            ent=ttk.Combobox(box,textvariable=var,values=choices,state='readonly',width=35) if choices else ttk.Entry(box,textvariable=var,width=38,show='•' if 'password' in label.lower() else '')
            ent.grid(row=i,column=1,sticky='ew')
        def submit():
            callback({k:v.get() for k,v in values.items()}); top.destroy()
        bar=ttk.Frame(box); bar.grid(row=len(fields),column=0,columnspan=2,pady=14)
        self.button(bar,'Save',submit); self.button(bar,'Cancel',top.destroy)

    def open_database(self,choose=False):
        if self.busy: raise ValueError('Wait for the current download/import to finish.')
        path=self.settings.get('database')
        saved_path=path
        if path and not choose and not Path(path).is_file():
            self.database_unavailable('Saved database is unavailable: '+path); return
        if choose or not path:
            path=filedialog.asksaveasfilename(title='Choose or create Oasis Attend database (.sqlite)',initialdir=str(self.config_dir),initialfile='attendance.sqlite',defaultextension='.sqlite',filetypes=[('Oasis Attend database','*.sqlite')],confirmoverwrite=False)
            if not path:
                if not self.store: self.destroy()
                return
        if Path(path).suffix.lower()!='.sqlite': raise ValueError('Choose a .sqlite app database. Import MDB after login.')
        path=str(Path(path).expanduser().resolve())
        try: new=Store(path)
        except Exception as e:
            self.database_unavailable(str(e)); return
        stop_receiver(self)
        if self.store: self.store.db.close()
        self.store=new; self.settings['database']=path; self.remember(); self.login_screen()

    def database_unavailable(self,error):
        self.clear()
        box=ttk.Frame(self,padding=35);box.pack(fill='both',expand=True)
        ttk.Label(box,text=self.tr('Database'),style='Title.TLabel').pack(pady=15)
        ttk.Label(box,text=error,wraplength=850).pack(pady=15)
        ttk.Label(box,text=self.tr('Select a saved database or restore its location.')).pack(pady=10)
        buttons=ttk.Frame(box);buttons.pack()
        self.button(buttons,'Refresh',self.open_database)
        self.button(buttons,'Choose database',lambda:self.open_database(True))

    def employee_picker(self,parent,callback=None):
        box=ttk.Frame(parent);box.pack(side='left',padx=6,pady=6)
        ttk.Label(box,text=self.tr('Employee')).pack(anchor='w')
        employees=self.store.rows('SELECT badge,name FROM employees ORDER BY badge')
        options=[self.tr('All employees')]+[str(r['badge'])+' — '+r['name'] for r in employees]
        picker=ttk.Combobox(box,values=options,state='readonly',width=32);picker.current(0);picker.pack()
        def badge():
            i=picker.current()
            return employees[i-1]['badge'] if i>0 else ''
        picker.badge=badge
        if callback:picker.bind('<<ComboboxSelected>>',lambda event:self.guard(lambda:callback(badge())))
        return picker

    def toggle_language(self):
        self.lang='ar' if self.lang=='en' else 'en'; self.remember()
        self.home() if self.store and self.store.actor else self.login_screen()

    def login_screen(self):
        stop_receiver(self)
        self.clear(); self.store.actor=None
        # The login block is the whole screen here, so the window shrinks to it
        # instead of framing it with empty space. home() restores the full size.
        self.minsize(1,1)
        frame=ttk.Frame(self,padding=20); frame.pack(expand=True)
        self.product_logo=tk.PhotoImage(file=str(brand_asset('app-logo-128.png')))
        ttk.Label(frame,image=self.product_logo).pack(pady=2)
        if asset('ods-logo.png').exists():
            self.logo=tk.PhotoImage(file=str(asset('ods-logo.png')));ttk.Label(frame,image=self.logo).pack(pady=2)
        ttk.Label(frame,text='Oasis Attend',style='Title.TLabel').pack(pady=2)
        ttk.Label(frame,text='Attendance & workforce  |  الحضور وإدارة الموظفين').pack(pady=2)
        self.company_header(frame)
        self.appearance_picker(frame)
        language_bar=ttk.Frame(frame);language_bar.pack();self.button(language_bar,'العربية / English',self.toggle_language)
        initial=not self.store.rows('SELECT username FROM accounts')
        ttk.Label(frame,text=self.tr('Create administrator' if initial else 'Login')).pack(pady=2)
        u=tk.StringVar(); p=tk.StringVar()
        for text,var,mask in [('Username',u,''),('Password',p,'•')]:
            ttk.Label(frame,text=self.tr(text)).pack(anchor='w'); ttk.Entry(frame,textvariable=var,show=mask,width=34).pack(pady=2)
        def enter():
            if initial: self.store.account(u.get(),p.get(),'admin',bootstrap=True)
            self.store.login(u.get(),p.get()); self.home()
        bar=ttk.Frame(frame); bar.pack(pady=2); self.button(bar,'Create administrator' if initial else 'Login',enter)
        # Enter submits from either field, and from the window itself.
        for widget in (frame,self):
            widget.bind('<Return>',lambda event:self.guard(enter))
            widget.bind('<KP_Enter>',lambda event:self.guard(enter))
        self.button(bar,'Choose database',lambda:self.open_database(True))
        ttk.Label(frame,text=str(self.store.path),wraplength=650).pack(pady=2)
        ttk.Label(frame,text=self.tr('Database selection is remembered automatically.')).pack(pady=0)
        ttk.Label(frame,text=PRODUCER).pack(pady=(3,0))
        ttk.Label(frame,text='Mob : 05555-69319').pack(pady=(2,0))
        ttk.Label(frame,text=COPYRIGHT,font=('Segoe UI',9)).pack()
        self.fit_to_content(frame)
        for child in frame.winfo_children():
            if isinstance(child,ttk.Entry): child.focus_set(); break

    def table(self,parent,rows,columns=None):
        wrap=ttk.Frame(parent); wrap.pack(fill='both',expand=True,pady=8)
        cols=columns or (list(rows[0]) if rows else ['No records'])
        tree=ttk.Treeview(wrap,columns=cols,show='headings',selectmode='browse'); vs=ttk.Scrollbar(wrap,orient='vertical',command=tree.yview); hs=ttk.Scrollbar(wrap,orient='horizontal',command=tree.xview); tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        tree.grid(row=0,column=0,sticky='nsew'); vs.grid(row=0,column=1,sticky='ns'); hs.grid(row=1,column=0,sticky='ew'); wrap.rowconfigure(0,weight=1); wrap.columnconfigure(0,weight=1)
        for c in cols: tree.heading(c,text=self.tr(c)); tree.column(c,width=155,minwidth=90,anchor='e' if self.lang=='ar' else 'w')
        tree.tag_configure('stripe',background=self.colors['stripe'])
        for i,r in enumerate(rows): tree.insert('', 'end',iid=str(i),values=[self.tr(str(r.get(c,''))) for c in cols],tags=('stripe',) if i%2 else ())
        tree.records=rows; return tree

    def selected(self,tree):
        sel=tree.selection()
        if not sel: raise ValueError('Select a row first.')
        return tree.records[int(sel[0])]

    def fit_to_content(self,widget,margin=24):
        """Size the window to the block it is showing and centre it on screen."""
        self.update_idletasks()
        width=widget.winfo_reqwidth()+margin
        height=widget.winfo_reqheight()+margin
        screen_w,screen_h=self.winfo_screenwidth(),self.winfo_screenheight()
        width=min(width,screen_w-80); height=min(height,screen_h-120)
        x=max(0,(screen_w-width)//2); y=max(0,(screen_h-height)//3)
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(width,height)

    def home(self):
        self.clear()
        # Drop the login Enter binding, otherwise Enter keeps firing it in the app.
        for sequence in ('<Return>','<KP_Enter>'):
            try: self.unbind(sequence)
            except Exception: pass
        self.minsize(980,680)
        width,height=1220,780
        screen_w,screen_h=self.winfo_screenwidth(),self.winfo_screenheight()
        self.geometry(f'{width}x{height}+{max(0,(screen_w-width)//2)}+{max(0,(screen_h-height)//2)}')
        bar=ttk.Frame(self,padding=(18,12)); bar.pack(fill='x')
        ttk.Label(bar,text='Oasis Attend',style='Title.TLabel').pack(side='left',padx=15)
        ttk.Label(bar,text=f"{self.store.actor['username']} · {self.store.actor['role']}").pack(side='left',padx=18)
        self.appearance_picker(bar,side='right')
        self.button(bar,'العربية / English',self.toggle_language); self.button(bar,'Logout',self.logout)
        self.company_header(self)
        self.status=tk.StringVar(value=self.tr('Working…' if self.busy else 'Ready')); ttk.Label(self,textvariable=self.status,padding=8).pack(side='bottom',fill='x')
        self.notebook=ttk.Notebook(self); self.notebook.pack(fill='both',expand=True,padx=18,pady=8)
        role=self.store.actor['role']; sections=['Dashboard','Reports']
        if role in ('admin','manager'): sections+=['Employees','Attendance','Shifts','Assignments']
        if role=='admin': sections+=['Devices','Accounts','Audit','Settings']
        self.pages={}
        for name in sections:
            f=ttk.Frame(self.notebook,padding=16); self.notebook.add(f,text=self.tr(name)); self.pages[name]=f
        self.dashboard(); self.reports()
        for name in sections[2:]:
            self.attendance_page() if name=='Attendance' else self.render(name)

    # ------------------------------------------------------------- Dashboard

    STATUS_COLORS = (('Present','#2E7D32'),('Late','#C77700'),('Absent','#B3261E'),
                     ('Missing punch','#6A4FBF'),('In progress','#1F5FA8'),
                     ('Pending','#607089'),('Off / Unscheduled','#9AA3B0'))

    def dashboard(self):
        f=self.pages['Dashboard']
        for w in f.winfo_children(): w.destroy()
        # pack(expand=True) centres the block in the page, horizontally and vertically.
        wrap=ttk.Frame(f); wrap.pack(expand=True)

        ttk.Label(wrap,text=self.tr('Dashboard'),style='Title.TLabel').pack(pady=(0,14))

        tiles=ttk.Frame(wrap); tiles.pack(pady=(0,18))
        for title,table in [('Employees','employees'),('Attendance','punches'),
                            ('Shifts','shifts'),('Devices','devices')]:
            n=self.store.rows('SELECT COUNT(*) AS n FROM '+table)[0]['n']
            cell=ttk.Frame(tiles,padding=(28,18),style='Card.TFrame'); cell.pack(side='left',padx=6)
            ttk.Label(cell,text=str(n),style='Metric.Card.TLabel').pack()
            ttk.Label(cell,text=self.tr(title),style='Card.TLabel').pack()

        today=date.today().isoformat()
        try:
            rows=self.store.report(today,today,'')
        except Exception:
            rows=[]
        counts={}
        for r in rows:
            counts[r['status']]=counts.get(r['status'],0)+1
        counts={k:v for k,v in counts.items() if v}

        ttk.Label(wrap,text=self.tr('Attendance today')+'  ·  '+today,
                  font=('Segoe UI',13,'bold')).pack(pady=(0,8))
        if counts:
            self.pie(wrap,counts)
        else:
            box=ttk.Frame(wrap,padding=24); box.pack()
            ttk.Label(box,text=self.tr('No attendance records for today.'),
                      font=('Segoe UI',12)).pack()
            ttk.Label(box,text=self.tr('Import a ZKTime database or download from a device to see today here.'),
                      wraplength=520).pack(pady=(6,0))

        ttk.Label(wrap,text=('الأوقات حسب ساعة الجهاز. راجع البصمات الناقصة قبل اعتماد التقرير.'
                             if self.lang=='ar' else
                             'Times follow the device clock. Review missing punches before approving reports.'),
                  wraplength=760).pack(pady=(18,6))
        bar=ttk.Frame(wrap); bar.pack()
        self.button(bar,'Refresh',self.dashboard)

    def pie(self,parent,counts):
        """Pie of today's statuses on a plain Canvas, with a counted legend.

        No chart library is added for one pie. Colour is never the only signal:
        every slice is named with its count and its share in the legend.
        """
        block=ttk.Frame(parent); block.pack()
        size=250; pad=10
        canvas=tk.Canvas(block,width=size,height=size,highlightthickness=0,
                         background=self.colors['surface'])
        canvas.pack(side='left',padx=(0,22))
        total=sum(counts.values())
        order=[(name,colour) for name,colour in self.STATUS_COLORS if counts.get(name)]
        for name in counts:
            if name not in dict(order): order.append((name,'#8A93A5'))

        if len(order)==1:
            canvas.create_oval(pad,pad,size-pad,size-pad,fill=order[0][1],outline='white',width=2)
        else:
            start=90.0
            for name,colour in order:
                extent=-360.0*counts[name]/total
                canvas.create_arc(pad,pad,size-pad,size-pad,start=start,extent=extent,
                                  fill=colour,outline='white',width=2)
                start+=extent

        legend=ttk.Frame(block); legend.pack(side='left',anchor='n')
        for name,colour in order:
            n=counts[name]; share=round(100*n/total)
            row=ttk.Frame(legend); row.pack(anchor='w',pady=3)
            swatch=tk.Canvas(row,width=14,height=14,highlightthickness=0,
                             background=self.colors['surface'])
            swatch.create_rectangle(0,0,14,14,fill=colour,outline=colour)
            swatch.pack(side='left',padx=(0,8))
            ttk.Label(row,text=f'{self.tr(name)}   {n}  ({share}%)').pack(side='left')
        ttk.Separator(legend).pack(fill='x',pady=6)
        ttk.Label(legend,text=f"{self.tr('Total')}   {total}",font=('Segoe UI',10,'bold')).pack(anchor='w')

    def company_header(self,parent):
        profile=self.store.company_profile()
        if not any(profile.values()): return
        box=ttk.Frame(parent,padding=(8,3));box.pack(fill='x')
        if profile['logo']:
            from PIL import Image,ImageTk
            from io import BytesIO
            with Image.open(BytesIO(profile['logo'])) as image:
                image.thumbnail((120,48))
                photo=ImageTk.PhotoImage(image)
            label=ttk.Label(box,image=photo);label.image=photo;label.pack(side='left',padx=8)
        words=ttk.Frame(box);words.pack(fill='x')
        if profile['company_name']:
            ttk.Label(words,text=profile['company_name'],font=('Segoe UI',12,'bold'),wraplength=460).pack()
        if profile['branch']:
            ttk.Label(words,text=self.tr('Branch')+': '+profile['branch'],wraplength=460).pack()

    def company_settings(self,parent):
        self.store.require('admin')
        saved=self.store.company_profile(); pending={'logo':saved['logo']}
        box=ttk.LabelFrame(parent,text=self.tr('Company details'),padding=12);box.pack(fill='x',pady=8)
        company=tk.StringVar(value=saved['company_name']);branch=tk.StringVar(value=saved['branch'])
        box.columnconfigure(1,weight=1)
        for row,(label,var) in enumerate((('Company name',company),('Branch',branch))):
            ttk.Label(box,text=self.tr(label)).grid(row=row,column=0,padx=8,pady=5,sticky='e')
            ttk.Entry(box,textvariable=var,width=48,justify='right' if self.lang=='ar' else 'left').grid(row=row,column=1,pady=5,sticky='ew')
        ttk.Label(box,text=self.tr('Company logo')).grid(row=2,column=0,padx=8,sticky='e')
        preview=ttk.Label(box);preview.grid(row=2,column=1,pady=4)
        def show_logo():
            preview.image=None
            if pending['logo']:
                from PIL import Image,ImageTk
                from io import BytesIO
                with Image.open(BytesIO(pending['logo'])) as image:
                    image.thumbnail((200,72));preview.image=ImageTk.PhotoImage(image)
                preview.configure(image=preview.image,text='')
            else:preview.configure(image='',text=self.tr('No company logo'))
        def choose():
            path=filedialog.askopenfilename(parent=self,title=self.tr('Choose logo'),filetypes=[('PNG / JPEG','*.png *.jpg *.jpeg')])
            if not path:return
            with open(path,'rb') as image: data=image.read(MAX_LOGO_BYTES+1)
            pending['logo']=normalize_logo(data);show_logo()
        def remove():pending['logo']=b'';show_logo()
        def save():
            self.store.save_company_profile(company.get(),branch.get(),pending['logo'])
            self.home();self.notebook.select(self.pages['Settings']);self.status.set(self.tr('Company details saved.'))
        buttons=ttk.Frame(box);buttons.grid(row=3,column=0,columnspan=2)
        self.button(buttons,'Choose logo',choose);self.button(buttons,'Remove logo',remove);self.button(buttons,'Save',save)
        ttk.Label(box,text=self.tr('Saved in the selected database and included in reports.'),wraplength=600).grid(row=4,column=0,columnspan=2,pady=6)
        show_logo()

    def render(self,name):
        f=self.pages[name]
        for w in f.winfo_children(): w.destroy()
        bar=ttk.Frame(f); bar.pack(fill='x')
        if name=='Settings':
            self.store.require('admin')
            appearance=ttk.LabelFrame(f,text=self.tr('Appearance'),padding=10); appearance.pack(fill='x',pady=8)
            self.appearance_picker(appearance)
            ttk.Label(appearance,text=self.tr('Choose light or dark. Your choice is saved on this PC.'),style='Muted.TLabel').pack()
            self.company_settings(f)
            ttk.Label(f,text=self.store.path,wraplength=800).pack(pady=16)
            ttk.Label(f,text=self.tr('Database selection is remembered automatically.')).pack(pady=8)
            self.button(bar,'Choose database',lambda:self.open_database(True)); self.button(bar,'Backup database',self.backup); self.button(bar,'Import ZKTime MDB',self.import_mdb); return
        queries={'Employees':'SELECT * FROM employees ORDER BY badge','Attendance':'SELECT * FROM punches ORDER BY stamp DESC LIMIT 10000','Shifts':'SELECT * FROM shifts','Assignments':'SELECT * FROM assignments','Devices':'SELECT * FROM devices','Accounts':'SELECT username,role FROM accounts','Audit':'SELECT * FROM audit ORDER BY id DESC LIMIT 1000'}
        if name in ('Employees','Attendance'):
            filters=ttk.Frame(f);filters.pack(fill='x')
            picker=self.employee_picker(filters)
        if name=='Attendance':queries[name]='SELECT p.badge,COALESCE(e.name,"") AS name,p.stamp,p.kind,p.source FROM punches p LEFT JOIN employees e ON p.badge=e.badge ORDER BY p.stamp DESC LIMIT 10000'
        if name=='Devices':queries[name]='SELECT id,name,ip,comm_key,port,udp FROM devices ORDER BY id'
        rows=self.store.rows(queries[name]); tree=self.table(f,rows);
        if name in ('Employees','Attendance'):
            def filter_rows(event=None):
                badge=picker.badge()
                if name=='Employees':filtered=self.store.rows('SELECT * FROM employees WHERE (?="" OR badge=?) ORDER BY badge',(badge,badge))
                else:filtered=self.store.rows('SELECT p.badge,COALESCE(e.name,"") AS name,p.stamp,p.kind,p.source FROM punches p LEFT JOIN employees e ON p.badge=e.badge WHERE (?="" OR p.badge=?) ORDER BY p.stamp DESC LIMIT 10000',(badge,badge))
                tree.delete(*tree.get_children());tree.records=filtered
                for i,r in enumerate(filtered):tree.insert('', 'end',iid=str(i),values=list(r.values()))
                if name=='Employees' and filtered and badge:tree.selection_set('0')
            picker.bind('<<ComboboxSelected>>',filter_rows)
        self.button(bar,'Refresh',lambda:self.render(name)); self.button(bar,'Export CSV',lambda:self.export(tree.records))
        if name=='Employees':
            def edit():
                r=self.selected(tree) if tree.selection() else {}
                self.form('Employees',[(k,r.get(key,default),None) for k,key,default in [('Badge','badge',''),('Name','name',''),('Department','department',''),('Active (1/0)','active',1)]],lambda v:self.saved(name,lambda:self.store.employee(v['Badge'],v['Name'],v['Department'],v['Active (1/0)'])))
            self.button(bar,'Add / Edit',edit)
            self.button(bar,'New',lambda:self.form('Employees',[(k,v,None) for k,v in [('Badge',''),('Name',''),('Department',''),('Active (1/0)',1)]],lambda v:self.saved(name,lambda:self.store.employee(v['Badge'],v['Name'],v['Department'],v['Active (1/0)']))))
        elif name=='Shifts':
            self.button(bar,'Create shift',lambda:self.form(name,[(k,v,None) for k,v in [('Name',''),('Start (HH:MM)','08:00'),('End (HH:MM)','17:00'),('Grace minutes',5),('Break minutes',60),('Weekdays (Mon=0, Sun=6)','0,1,2,3,6')]],lambda v:self.saved(name,lambda:self.store.shift(*v.values()))))
        elif name=='Assignments':
            self.button(bar,'Assign shift',lambda:self.form(name,[('Badge','',[r['badge'] for r in self.store.rows('SELECT badge FROM employees')]),('Shift ID','',[r['id'] for r in self.store.rows('SELECT id FROM shifts')]),('From (YYYY-MM-DD)',date.today().isoformat(),None),('To (YYYY-MM-DD)',date.today().replace(month=12,day=31).isoformat(),None)],lambda v:self.saved(name,lambda:self.store.assign(*v.values()))))
            self.button(bar,'Remove selected',lambda:self.saved(name,lambda:self.store.remove_assignment(self.selected(tree)['id'])))
        elif name=='Devices':
            def edit_device():
                selected=self.selected(tree) if tree.selection() else {}
                self.form(name,[(label,selected.get(key,default),None) for label,key,default in
                    [('Name','name',''),('IP address','ip','192.168.1.201'),('Communication key (0 if none)','comm_key',0),('Port','port',4370),('UDP (1/0)','udp',0)]],
                    lambda v:self.saved(name,lambda:self.store.device(v['Name'],v['IP address'],v['Port'],v['UDP (1/0)'],v['Communication key (0 if none)'],selected.get('id'))))
            self.button(bar,'Add / Edit',edit_device)
            self.button(bar,'Download users + logs',lambda:self.device_download(self.selected(tree)))
            self.button(bar,'Remove device',lambda:self.remove_device(self.selected(tree)))
            self.button(bar,'Import from BioTime',lambda:open_biotime(self))
            adms_bar=ttk.Frame(f);adms_bar.pack()
            self.button(adms_bar,'Receive from device (ADMS)',lambda:open_adms(self,self.selected(tree) if tree.selection() else {}))
            ttk.Label(f,text='MB20 · MB1000 · MB2000 · uFace800 | TCP · 4370 (pyzatt)').pack()
            ttk.Label(f,text=self.tr('Save the device communication key beside its IP address. Downloads use this saved value.'),wraplength=800).pack()
        elif name=='Accounts':
            self.button(bar,'Add / Edit',lambda:self.form(name,[('Username','',None),('Password','',None),('Role','reports',['reports','manager','admin'])],lambda v:self.saved(name,lambda:self.store.account(*v.values()))))
    def saved(self,page,fn): fn(); self.render(page)

    # ------------------------------------------------------------ Attendance

    ATTENDANCE_COLUMNS = ('date','weekday','badge','name','in','out','worked','punches','status','note')
    ATTENDANCE_ROW_CAP = 50000
    ATTENDANCE_MAX_DAYS = 36600   # open range; row_cap is the real guard

    @staticmethod
    def hours_minutes(minutes):
        """Minutes as H:MM. Never returns 0:00 for an unpaired day, the caller
        passes None for that so the cell stays empty."""
        if minutes is None: return ''
        return f'{int(minutes)//60}:{int(minutes)%60:02d}'

    def attendance_view(self, rows):
        """core.report rows to grid rows. The pairing is core.report's own, so
        Attendance and Reports can never disagree about a day."""
        view=[]
        for r in rows:
            if r.get('truncated'): self.attendance_truncated=True
            first=r['first'] or ''; last=r['last'] or ''
            paired=bool(last)
            note=''
            if r['punches']==1: note='Missing out punch'
            elif r['punches']>1 and r['punches']%2: note='Odd punch count'
            view.append({'date':r['date'],
                         'weekday':date.fromisoformat(r['date']).strftime('%a'),
                         'badge':r['badge'],'name':r['name'],
                         'in':first[11:16] if first else '',
                         'out':last[11:16] if last else '',
                         'worked':self.hours_minutes(r['worked_minutes'] if paired else None),
                         'punches':r['punches'],'status':r['status'],'note':note})
        return view

    def attendance_query(self,store,raw,begin,finish,badge):
        """Runs on the worker thread against its own connection.

        The date range is pushed into SQL. Nothing is fetched and then filtered
        in Python, and no value is ever concatenated into the statement.
        """
        if raw:
            stop=(date.fromisoformat(finish)+timedelta(days=1)).isoformat()
            return store.rows('SELECT p.badge,COALESCE(e.name,"") AS name,p.stamp,p.kind,p.source '
                              'FROM punches p LEFT JOIN employees e ON p.badge=e.badge '
                              'WHERE p.stamp>=? AND p.stamp<? AND (?="" OR p.badge=?) '
                              'ORDER BY p.stamp DESC LIMIT ?',
                              (begin,stop,badge,badge,self.ATTENDANCE_ROW_CAP))
        return store.report(begin,finish,badge,max_days=self.ATTENDANCE_MAX_DAYS,
                            row_cap=self.ATTENDANCE_ROW_CAP)

    def attendance_page(self):
        f=self.pages['Attendance']
        for w in f.winfo_children(): w.destroy()
        self.attendance_rows=[]; self.attendance_truncated=False
        self.attendance_raw=tk.BooleanVar(value=False)
        low,high=self.store.punch_bounds()
        empty=not self.store.rows('SELECT 1 FROM punches LIMIT 1')

        filters=ttk.Frame(f); filters.pack(fill='x',pady=(0,6))
        employee=self.employee_picker(filters)
        picker=DateRange(filters,(low,high),lambda a,b:self.guard(self.attendance_load),
                         translate=self.tr,rtl=self.lang=='ar',default='Full range')
        picker.pack(side='left',padx=(14,0))
        actions=ttk.Frame(f); actions.pack(fill='x',pady=(0,4))
        result=ttk.Frame(f); result.pack(fill='both',expand=True)
        self.attendance_widgets={'picker':picker,'employee':employee,'result':result}
        employee.bind('<<ComboboxSelected>>',lambda e:self.guard(self.attendance_load))

        left=ttk.Frame(actions); left.pack(side='left')
        right=ttk.Frame(actions); right.pack(side='right')
        self.button(left,'Refresh',self.attendance_page)
        ttk.Checkbutton(left,text=self.tr('Show raw punches'),variable=self.attendance_raw,
                        command=lambda:self.guard(self.attendance_load)).pack(side='left',padx=14)
        self.button(right,'Export CSV',lambda:self.export(self.attendance_rows))
        self.button(right,'Print PDF',lambda:self.attendance_output('pdf'))
        self.button(right,'Print preview',lambda:self.attendance_output('print'))
        ttk.Label(f,text=self.tr('Worked is last punch minus first punch. Breaks are not deducted.'),
                  wraplength=900).pack(anchor='e' if self.lang=='ar' else 'w',pady=(4,0))

        if empty:
            ttk.Label(result,text=self.tr('No punches in the database yet. Import a ZKTime database or download from a device first.'),
                      wraplength=700).pack(pady=40)
            return
        self.attendance_load()

    def attendance_load(self):
        w=self.attendance_widgets
        begin,finish=w['picker'].values(); badge=w['employee'].badge()
        if begin>finish or not w['picker'].valid(): return
        raw=self.attendance_raw.get()
        title=f"Oasis Attend | {self.tr('Attendance')} | {begin} - {finish} | {w['employee'].get()}"
        self.attendance_title=title
        def work():
            store=self.store.read_clone()
            try:
                return self.attendance_query(store,raw,begin,finish,badge)
            finally:
                store.close()

        def done(rows):
            self.attendance_truncated=False
            self.attendance_rows=rows if raw else self.attendance_view(rows)
            for child in w['result'].winfo_children(): child.destroy()
            if not self.attendance_rows:
                message='No attendance records for this period.'
                if not raw:
                    stop=(date.fromisoformat(finish)+timedelta(days=1)).isoformat()
                    loose=self.store.rows('SELECT COUNT(*) AS n FROM punches WHERE stamp>=? AND stamp<? AND (?="" OR badge=?)',
                                          (begin,stop,badge,badge))[0]['n']
                    if loose:
                        message=('No daily rows for this period. The punches exist but their badges '
                                 'are not in the employee list. Use Show raw punches, or import the employees.')
                ttk.Label(w['result'],text=self.tr(message),wraplength=760).pack(pady=40)
            else:
                self.table(w['result'],self.attendance_rows,
                           None if raw else list(self.ATTENDANCE_COLUMNS))
            if self.attendance_truncated or len(self.attendance_rows)>=self.ATTENDANCE_ROW_CAP:
                w['picker'].show_error(self.tr('Results were trimmed. Narrow the period or choose one employee.'))
            self.status.set(f'{len(self.attendance_rows)} rows  |  {begin} - {finish}')
        self.background(work,done)

    def attendance_output(self,kind):
        if not self.attendance_rows: raise ValueError('No rows to export.')
        rows=[{k:v for k,v in r.items() if k!='truncated'} for r in self.attendance_rows]
        kwargs=dict(title=self.attendance_title,translate=self.tr,arabic=self.lang=='ar',company=self.store.company_profile())
        if kind=='print':
            import uuid,webbrowser
            folder=self.config_dir/'print-previews'; folder.mkdir(exist_ok=True)
            path=folder/(uuid.uuid4().hex+'.html')
            export_print_html(path,rows,**kwargs); webbrowser.open(path.as_uri())
            self.status.set(str(path)); return
        path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
        if not path: return
        self.background(lambda:(export_pdf(path,rows,**kwargs),path)[1],
                        lambda p:self.status.set(str(p)))

    # Columns that a total is meaningful for. Anything else stays blank on the
    # summary line, because a summed badge number or a summed date is nonsense.
    SUMMARY_FIELDS = ('punches','worked_minutes','late_minutes','early_minutes',
                      'present_days','absent_days','missing_punch_days')

    def totals_row(self,rows):
        """Build the end line of the report: sums for the numeric columns only."""
        if not rows: return None
        columns=list(rows[0])
        total={c:'' for c in columns}
        for c in columns:
            if c in self.SUMMARY_FIELDS:
                total[c]=sum(int(r.get(c) or 0) for r in rows)
        total[columns[0]]=self.tr('Total')
        return total

    def report_summary(self,rows):
        """Counts a payroll clerk asks for, in words rather than only in columns."""
        worked=sum(int(r.get('worked_minutes') or 0) for r in rows)
        late_minutes=sum(int(r.get('late_minutes') or 0) for r in rows)
        early=sum(int(r.get('early_minutes') or 0) for r in rows)
        if 'status' in rows[0]:
            late_days=sum(1 for r in rows if r['status']=='Late')
            absent=sum(1 for r in rows if r['status']=='Absent')
            missing=sum(1 for r in rows if r['status']=='Missing punch')
            present=sum(1 for r in rows if int(r.get('punches') or 0)>0)
        else:
            late_days=None
            absent=sum(int(r.get('absent_days') or 0) for r in rows)
            missing=sum(int(r.get('missing_punch_days') or 0) for r in rows)
            present=sum(int(r.get('present_days') or 0) for r in rows)
        parts=[(self.tr('Rows'),len(rows)),
               (self.tr('Days present'),present),
               (self.tr('Worked hours'),self.hours_minutes(worked)),
               (self.tr('Late minutes'),late_minutes),
               (self.tr('Early leave minutes'),early),
               (self.tr('Absent days'),absent),
               (self.tr('Missing punch days'),missing)]
        if late_days is not None:
            parts.insert(4,(self.tr('Late days'),late_days))
        return parts

    def reports(self):
        f=self.pages['Reports']
        for w in f.winfo_children(): w.destroy()
        self.report_data=[]; self.report_summary_pairs=[]
        self.report_title='Oasis Attend | Attendance report'
        # Employee and report type on their own row, so neither is pushed off
        # the right edge by the date fields and the preset strip.
        who=ttk.Frame(f); who.pack(fill='x')
        employee=self.employee_picker(who)
        mode=ttk.Frame(who); mode.pack(side='left',padx=10,pady=6)
        ttk.Label(mode,text=self.tr('Report type')).pack(anchor='e' if self.lang=='ar' else 'w')
        pick=ttk.Combobox(mode,values=[self.tr(x) for x in ['Daily','Monthly','Period']],
                          state='readonly',width=14)
        pick.set(self.tr('Daily')); pick.pack()

        bar=ttk.Frame(f); bar.pack(fill='x')
        actions=ttk.Frame(f); actions.pack(fill='x',pady=(4,0))

        # The same picker component as Attendance. One component, two call sites.
        low,high=self.store.punch_bounds()
        picker=DateRange(bar,(low,high),lambda a,b:None,translate=self.tr,
                         rtl=self.lang=='ar',default='Today')
        picker.pack(side='left')
        result=ttk.Frame(f); result.pack(fill='both',expand=True)

        def generate():
            a=date.fromisoformat(picker.values()[0]); b=date.fromisoformat(picker.values()[1])
            selected=pick.current()
            if selected==0: b=a                      # Daily: the start day only
            if selected==1:                          # Monthly: the whole month
                a=a.replace(day=1); b=a.replace(day=calendar.monthrange(a.year,a.month)[1])
            picker.set_range(a,b)
            rows=self.store.report(a.isoformat(),b.isoformat(),employee.badge(),
                                   max_days=self.ATTENDANCE_MAX_DAYS,
                                   row_cap=self.ATTENDANCE_ROW_CAP)
            body=monthly(rows) if selected==1 else rows
            self.report_title=f'Oasis Attend | {pick.get()} | {a.isoformat()} - {b.isoformat()} | {employee.get()}'
            for w in result.winfo_children(): w.destroy()
            if not body:
                self.report_data=[]; self.report_summary_pairs=[]
                ttk.Label(result,text=self.tr('No attendance records for this period.')).pack(pady=40)
                self.status.set(f'0 rows  |  {a.isoformat()} - {b.isoformat()}')
                return
            summary=self.report_summary(body)
            self.report_summary_pairs=summary
            # The totals line travels with the data, so CSV, Excel, PDF and the
            # print preview all carry the same end line the screen shows.
            self.report_data=body+[self.totals_row(body)]
            tree=self.table(result,self.report_data)
            tree.item(str(len(self.report_data)-1),tags=('total',))
            tree.tag_configure('total',font=('Segoe UI',10,'bold'),background=self.colors['hover'],foreground=self.colors['text'])
            strip=ttk.Frame(result,padding=(0,8)); strip.pack(fill='x')
            for label,value in summary:
                cell=ttk.Frame(strip,padding=(0,0,22,0)); cell.pack(side='left')
                ttk.Label(cell,text=str(value),font=('Segoe UI',13,'bold')).pack(anchor='w')
                ttk.Label(cell,text=label).pack(anchor='w')
            self.status.set(f'{len(body)} rows  |  {a.isoformat()} - {b.isoformat()}')

        self.button(actions,'Generate',generate)
        self.button(actions,'Export CSV',lambda:self.export(self.report_data))
        self.button(actions,'Export PDF',lambda:self.report_output('pdf'))
        self.button(actions,'Export Excel',lambda:self.report_output('excel'))
        self.button(actions,'Print preview',lambda:self.report_output('print'))

    def report_output(self,kind):
        if not self.report_data:raise ValueError('No rows to export.')
        kwargs=dict(title=self.report_title,translate=self.tr,arabic=self.lang=='ar',company=self.store.company_profile(),
                    summary=getattr(self,'report_summary_pairs',[]))
        if kind=='print':
            import uuid,webbrowser
            folder=self.config_dir/'print-previews';folder.mkdir(exist_ok=True)
            path=folder/(uuid.uuid4().hex+'.html')
            export_print_html(path,self.report_data,**kwargs);webbrowser.open(path.as_uri())
        else:
            types=[('PDF','*.pdf')] if kind=='pdf' else [('Excel 97-2003','*.xls'),('Excel workbook','*.xlsx')]
            path=filedialog.asksaveasfilename(defaultextension='.pdf' if kind=='pdf' else '.xls',filetypes=types)
            if not path:return
            (export_pdf if kind=='pdf' else export_excel)(path,self.report_data,**kwargs)
        self.status.set(str(path))

    def export(self,rows):
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if p: export_csv(p,rows,company=self.store.company_profile()); self.status.set(p)
    def backup(self):
        self.store.require('admin'); p=filedialog.asksaveasfilename(defaultextension='.sqlite',initialfile='Oasis Attend-backup.sqlite')
        if p:
            if Path(p).resolve()==Path(self.store.path).resolve(): raise ValueError('Choose a different backup file.')
            import sqlite3
            target=sqlite3.connect(p)
            try: self.store.db.backup(target)
            finally: target.close()
            self.status.set('Backup saved: '+p)
    def background(self,work,done):
        if self.busy: raise ValueError('An operation is already running.')
        self.busy=True; self.status.set(self.tr('Working…'))
        def run():
            try: self.results.put((done,work(),None))
            except Exception as e: self.results.put((done,None,e))
        threading.Thread(target=run,daemon=True).start()
    def poll(self):
        try:
            done,result,error=self.results.get_nowait(); self.busy=False
            if error: self.guard(lambda:self.operation_error(error))
            else: self.guard(lambda:done(result))
            if hasattr(self,'status'): self.status.set(self.tr('Ready'))
        except queue.Empty: pass
        self.after(100,self.poll)
    def operation_error(self,error):
        if isinstance(error,DirectConnectionRejected) and error.reply_code==6001:
            if messagebox.askyesno('Oasis Attend',self.tr(
                    'The device rejected the direct download (6001). Use Receive from device (ADMS) to receive attendance without BioTime. Open receiver settings?'),parent=self):
                open_adms(self)
            return
        messagebox.showerror('Oasis Attend',self.tr(str(error)),parent=self)
    def import_mdb(self):
        self.store.require('admin'); path=filedialog.askopenfilename(filetypes=[('ZKTime Access database','*.mdb')])
        if not path:return
        def done(data):
            count=self.store.ingest(data['employees'],data['punches'],'ZKTime MDB')
            for d in data.get('devices',[]):
                if d['ip']:
                    try:self.store.device(d['name'] or d['ip'],d['ip'],int(d['port'] or 4370),0)
                    except ValueError: pass
            self.home(); messagebox.showinfo('Import',f'{count} new records imported.\nLegacy schedules are not migrated. Configure shifts in Oasis Attend.')
        self.background(lambda:read_mdb(path),done)
    def remove_device(self,device):
        """Irreversible, so it asks first and names the row being deleted."""
        self.store.require('admin')
        label=f"{device.get('name') or ''}  {device['ip']}:{device['port']}".strip()
        if not messagebox.askyesno('Oasis Attend',
                self.tr('Remove this device from the list?')+'\n\n'+label+'\n\n'
                +self.tr('Attendance records already downloaded from it are kept.'),
                parent=self,default='no'):
            return
        self.store.remove_device(device['id'])
        self.render('Devices')
        self.status.set(self.tr('Device removed')+': '+label)

    def device_download(self,device):
        self.store.require('admin')
        def done(data):
            count=self.store.ingest(*data,source=device['ip']+':'+str(device['port'])); self.home(); messagebox.showinfo('Download',f'{count} new records imported.')
        self.background(lambda:download(device),done)
    def logout(self):
        if self.busy: raise ValueError('Wait for the current operation to finish before logging out.')
        self.login_screen()
    def close(self):
        if self.busy: messagebox.showinfo('Oasis Attend','Wait for the current download/import to finish.'); return
        stop_receiver(self)
        if self.store:self.store.db.close()
        self.destroy()

def self_test(folder):
    """Explicit diagnostic mode, with all test data under the supplied folder."""
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    os.environ['LOCALAPPDATA']=str(folder)
    from pyzatt.pyzatt import ZKSS
    cfg=folder/'Oasis Attend';cfg.mkdir(exist_ok=True)
    db=folder/'smoke.sqlite'
    if not db.exists():Store(db).db.close()
    (cfg/'settings.json').write_text(json.dumps({'database':str(db),'language':'en'}))
    app=App();app.withdraw();app.after_cancel(app.startup_id);app.open_database()
    if not app.store.rows('SELECT username FROM accounts'):app.store.account('smoke-admin','smoke-only-password','admin',True)
    app.store.login('smoke-admin','smoke-only-password')
    from PIL import Image,ImageDraw
    from io import BytesIO
    logo_image=Image.new('RGB',(240,100),'#D39340');ImageDraw.Draw(logo_image).text((20,35),'TEST COMPANY',fill='black')
    logo_buffer=BytesIO();logo_image.save(logo_buffer,format='PNG')
    app.store.save_company_profile('Example Company / شركة اختبار','Riyadh / الرياض',logo_buffer.getvalue())
    company=app.store.company_profile()
    for language in ('en','ar'):
        app.lang=language;app.home();app.update_idletasks()
        assert len(app.pages)==10
        for page in app.pages.values():app.notebook.select(page);app.update_idletasks()
        def walk(widget):
            yield widget
            for child in widget.winfo_children():yield from walk(child)
        for label in ('Company name','Branch','Choose logo','Remove logo'):
            assert any(w.cget('text')==app.tr(label) for w in walk(app.pages['Settings']) if 'text' in w.keys())
    # Switching appearance must preserve an open page, unsaved entry and table selection.
    for language in ('en','ar'):
        app.lang=language;app.home()
        page=app.pages['Settings'];app.notebook.select(page)
        pending=ttk.Entry(page);pending.insert(0,'Unsaved company edit');pending.pack()
        tree=app.table(page,[{'badge':'001'},{'badge':'002'}]);tree.selection_set('1')
        for mode in ('dark','light'):
            app.theme_var.set(mode);app.change_appearance();app.update_idletasks()
            assert app.notebook.select()==str(page)
            assert pending.get()=='Unsaved company edit' and tree.selection()==('1',)
            assert json.loads(app.config_file.read_text('utf-8'))['appearance']==mode
            assert ttk.Style(app).lookup('TEntry','foreground')==app.colors['text']
            dialog=open_biotime(app);app.update_idletasks()
            assert any(w.cget('text')==app.tr('Read attendance') for w in walk(dialog) if 'text' in w.keys())
            password_fields=[w for w in walk(dialog) if isinstance(w,ttk.Entry) and w.cget('show')=='•']
            assert len(password_fields)==1 and password_fields[0].get()==''
            assert dialog.winfo_reqwidth()<app.winfo_screenwidth()
            dialog.destroy()
            dialog=open_adms(app);app.update_idletasks()
            assert any(w.cget('text')==app.tr('Start receiver') for w in walk(dialog) if 'text' in w.keys())
            assert dialog.winfo_reqwidth()<app.winfo_screenwidth()
            dialog.destroy()
    app.store.account('smoke-reader','smoke-only-password','reports')
    app.store.login('smoke-reader','smoke-only-password');app.home();app.update_idletasks()
    assert list(app.pages)==['Dashboard','Reports']
    assert asset('ods-logo.png').is_file()
    import bidi,pyzatt
    assert Path(bidi.__file__).suffix=='.py', 'bidi must remain externally replaceable'
    (folder/'dependency-paths.json').write_text(json.dumps({'bidi':bidi.__file__,'pyzatt':pyzatt.__file__}))
    sample=[{'badge':'001','name':'محمد أحمد','worked_minutes':480}]
    export_pdf(folder/'check.pdf',sample,translate=app.tr,arabic=True,company=company)
    export_excel(folder/'check.xls',sample,company=company)
    export_excel(folder/'check.xlsx',sample,company=company)
    export_print_html(folder/'check.html',sample,company=company)
    app.close();(folder/'self-test.json').write_text(json.dumps({'ok':True,'languages':['en','ar'],'device_connector_import':True,'reader_tabs':2,'admin_tabs':10,'appearance':['light','dark'],'theme_preserves_edits':True}))

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        try:self_test(sys.argv[2])
        except Exception:
            import traceback
            Path(sys.argv[2]).mkdir(parents=True,exist_ok=True)
            (Path(sys.argv[2])/'self-test-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            sys.exit(1)
    else:App().mainloop()
