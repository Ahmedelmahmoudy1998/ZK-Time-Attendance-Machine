import sqlite3, hashlib, secrets, hmac, json, csv
from datetime import datetime, date, time, timedelta
from company_profile import CompanyProfileStore

ROLES = ('admin', 'manager', 'reports')

class Store(CompanyProfileStore):
    def __init__(self, path):
        self.path = str(path)
        self.db = sqlite3.connect(path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(username TEXT PRIMARY KEY, salt TEXT NOT NULL, hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','manager','reports')), failures INTEGER DEFAULT 0, locked_until TEXT);
        CREATE TABLE IF NOT EXISTS employees(badge TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT DEFAULT '', active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY, name TEXT NOT NULL, ip TEXT NOT NULL, port INTEGER NOT NULL DEFAULT 4370, udp INTEGER NOT NULL DEFAULT 0, UNIQUE(ip,port));
        CREATE TABLE IF NOT EXISTS punches(badge TEXT NOT NULL, stamp TEXT NOT NULL, kind TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, UNIQUE(badge,stamp));
        CREATE TABLE IF NOT EXISTS shifts(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL, grace INTEGER NOT NULL DEFAULT 0, break_mins INTEGER NOT NULL DEFAULT 0, days TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, badge TEXT NOT NULL REFERENCES employees(badge), shift_id INTEGER NOT NULL REFERENCES shifts(id), begin TEXT NOT NULL, finish TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, stamp TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS company_profile(id INTEGER PRIMARY KEY CHECK(id=1), company_name TEXT NOT NULL, branch TEXT NOT NULL, logo BLOB NOT NULL);
        ''')
        self.actor = None
        try:self._migrate_punches()
        except BaseException:
            self.db.close()
            raise

    def _migrate_punches(self):
        """Atomic, repeatable upgrade; retain first-seen row and archive duplicates.

        Badge+second is the physical punch identity. MDB CHECKTYPE values and
        numeric device states can differ for the same scan, so neither kind nor
        origin belongs in the unique key. Report math already uses this identity.
        """
        self.db.execute('BEGIN IMMEDIATE')
        try:
            indexes=self.db.execute('PRAGMA index_list(punches)').fetchall()
            unique=[tuple(r['name'] for r in self.db.execute('SELECT name FROM pragma_index_info(?) ORDER BY seqno',(i['name'],))) for i in indexes if i['unique']]
            if ('badge','stamp') not in unique:
                self.db.execute('CREATE TABLE IF NOT EXISTS punch_duplicate_archive(original_rowid INTEGER,badge TEXT,stamp TEXT,kind TEXT,source TEXT,migrated_at TEXT)')
                count=self.db.execute('SELECT COUNT(*) FROM punches').fetchone()[0]
                self.db.execute('INSERT INTO punch_duplicate_archive SELECT rowid,badge,stamp,kind,source,? FROM punches WHERE rowid NOT IN (SELECT MIN(rowid) FROM punches GROUP BY badge,stamp)',(datetime.now().isoformat(timespec='seconds'),))
                self.db.execute("CREATE TABLE punches_v2(badge TEXT NOT NULL,stamp TEXT NOT NULL,kind TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,UNIQUE(badge,stamp))")
                self.db.execute('INSERT INTO punches_v2 SELECT badge,stamp,kind,source FROM punches WHERE rowid IN (SELECT MIN(rowid) FROM punches GROUP BY badge,stamp) ORDER BY rowid')
                after=self.db.execute('SELECT COUNT(*) FROM punches_v2').fetchone()[0]
                self.db.execute('DROP TABLE punches');self.db.execute('ALTER TABLE punches_v2 RENAME TO punches')
                self.log(f'Punch identity migration v2: {count-after} duplicate rows archived; {after} punches retained')
            self.db.execute('CREATE INDEX IF NOT EXISTS idx_punches_stamp ON punches(stamp)')
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def require(self, *roles):
        if not self.actor or self.actor['role'] not in roles:
            raise PermissionError('Your account does not have permission for this action.')

    def log(self, action):
        self.db.execute('INSERT INTO audit(stamp,actor,action) VALUES(?,?,?)', (datetime.now().isoformat(timespec='seconds'), self.actor['username'] if self.actor else 'setup', action))

    def account(self, username, password, role, bootstrap=False):
        if not (bootstrap and not self.rows('SELECT username FROM accounts')):
            self.require('admin')
        username = username.strip()
        if not username or len(password) < 8 or role not in ROLES:
            raise ValueError('Use a username, a password of at least 8 characters, and a valid role.')
        if self.actor and username == self.actor['username'] and role != 'admin':
            raise ValueError('You cannot demote your own administrator account.')
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
        with self.db:
            self.db.execute('INSERT INTO accounts(username,salt,hash,role) VALUES(?,?,?,?) ON CONFLICT(username) DO UPDATE SET salt=excluded.salt,hash=excluded.hash,role=excluded.role,failures=0,locked_until=NULL', (username,salt,digest,role))
            self.log('Account saved: ' + username)

    def login(self, username, password):
        row = self.db.execute('SELECT * FROM accounts WHERE username=?', (username,)).fetchone()
        if row and row['locked_until'] and datetime.fromisoformat(row['locked_until']) > datetime.now():
            raise ValueError('Account temporarily locked. Try again in 5 minutes.')
        salt = bytes.fromhex(row['salt']) if row else bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000).hex()
        if not row or not hmac.compare_digest(digest,row['hash']):
            if row:
                with self.db:
                    n = row['failures'] + 1
                    self.db.execute('UPDATE accounts SET failures=?,locked_until=? WHERE username=?', (n, (datetime.now()+timedelta(minutes=5)).isoformat() if n >= 5 else None,username))
            raise ValueError('Invalid username or password.')
        self.actor = {'username':username,'role':row['role']}
        with self.db:
            self.db.execute('UPDATE accounts SET failures=0,locked_until=NULL WHERE username=?',(username,))
            self.log('Login')

    def employee(self,badge,name,department='',active=1):
        self.require('admin','manager')
        if not badge.strip() or not name.strip(): raise ValueError('Badge and name are required.')
        if int(active) not in (0,1): raise ValueError('Active must be 0 or 1.')
        with self.db:
            self.db.execute('INSERT INTO employees VALUES(?,?,?,?) ON CONFLICT(badge) DO UPDATE SET name=excluded.name,department=excluded.department,active=excluded.active',(badge.strip(),name.strip(),department,int(active)))
            self.log('Employee saved: '+badge)

    def device(self,name,ip,port,udp):
        self.require('admin')
        import ipaddress
        ipaddress.ip_address(ip)
        if not name.strip() or not 1 <= int(port) <= 65535 or int(udp) not in (0,1): raise ValueError('Invalid device name, port or UDP setting.')
        with self.db:
            self.db.execute('INSERT INTO devices(name,ip,port,udp) VALUES(?,?,?,?) ON CONFLICT(ip,port) DO UPDATE SET name=excluded.name,udp=excluded.udp',(name,ip,int(port),int(udp)))
            self.log('Device saved: '+ip)

    def shift(self,name,start,end,grace,break_mins,days):
        self.require('admin','manager')
        a=time.fromisoformat(start); b=time.fromisoformat(end)
        duration=((b.hour*60+b.minute)-(a.hour*60+a.minute)) % 1440
        ds=sorted(set(int(v.strip()) for v in days.split(',')))
        if not name.strip() or not ds or min(ds)<0 or max(ds)>6 or duration==0 or int(grace)<0 or not 0<=int(break_mins)<duration:
            raise ValueError('Check shift times, break, grace and weekdays (Monday=0 … Sunday=6).')
        with self.db:
            self.db.execute('INSERT INTO shifts(name,start,end,grace,break_mins,days) VALUES(?,?,?,?,?,?)',(name,a.strftime('%H:%M'),b.strftime('%H:%M'),int(grace),int(break_mins),','.join(map(str,ds))))
            self.log('Shift created: '+name)

    def assign(self,badge,shift_id,begin,finish):
        self.require('admin','manager')
        begin=date.fromisoformat(begin).isoformat(); finish=date.fromisoformat(finish).isoformat()
        if begin>finish: raise ValueError('End date must follow start date.')
        if self.rows('SELECT id FROM assignments WHERE badge=? AND begin<=? AND finish>=?',(badge,finish,begin)):
            raise ValueError('This employee already has an assignment overlapping these dates. Remove it first.')
        with self.db:
            self.db.execute('INSERT INTO assignments(badge,shift_id,begin,finish) VALUES(?,?,?,?)',(badge,int(shift_id),begin,finish))
            self.log('Shift assigned: '+badge)

    def remove_assignment(self, id):
        self.require('admin','manager')
        with self.db:
            self.db.execute('DELETE FROM assignments WHERE id=?',(int(id),)); self.log('Assignment removed: '+str(id))

    def remove_device(self, id):
        """Delete a device row. Punches already imported from it are kept: they
        record the source as text, not a foreign key, so history is not lost."""
        self.require('admin')
        row=self.db.execute('SELECT name,ip,port FROM devices WHERE id=?',(int(id),)).fetchone()
        if not row: raise ValueError('That device no longer exists. Refresh the list.')
        with self.db:
            self.db.execute('DELETE FROM devices WHERE id=?',(int(id),))
            self.log(f"Device removed: {row['name']} {row['ip']}:{row['port']}")

    def ingest(self, employees, punches, source):
        self.require('admin')
        punches=list(punches)
        identities={(str(p['badge']),datetime.fromisoformat(p['stamp']).replace(microsecond=0).isoformat(sep=' ')) for p in punches}
        added=0
        with self.db:
            repaired=0
            for p in punches:
                if not p.get('legacy_stamp'):continue
                badge=str(p['badge']);old=datetime.fromisoformat(p['legacy_stamp']).replace(microsecond=0).isoformat(sep=' ')
                stamp=datetime.fromisoformat(p['stamp']).replace(microsecond=0).isoformat(sep=' ')
                # Never move a timestamp that is also a real record in this download.
                if old==stamp or (badge,old) in identities:continue
                found=self.db.execute('SELECT kind FROM punches WHERE badge=? AND stamp=? AND source=?',(badge,old,source)).fetchone()
                if not found or found['kind']!=str(p.get('kind') or ''):continue
                self.db.execute('''CREATE TABLE IF NOT EXISTS punch_time_repair_archive(
                    badge TEXT, original_stamp TEXT, corrected_stamp TEXT, kind TEXT, source TEXT, repaired_at TEXT)''')
                self.db.execute('INSERT INTO punch_time_repair_archive VALUES(?,?,?,?,?,?)',
                    (badge,old,stamp,found['kind'],source,datetime.now().isoformat(timespec='seconds')))
                self.db.execute('DELETE FROM punches WHERE badge=? AND stamp=? AND source=?',(badge,old,source))
                repaired+=1
            before=self.db.total_changes
            for e in employees:
                self.db.execute('INSERT INTO employees(badge,name,department) VALUES(?,?,?) ON CONFLICT(badge) DO NOTHING',(str(e['badge']),str(e.get('name') or e['badge']),str(e.get('department') or '')))
            for p in punches:
                stamp=datetime.fromisoformat(p['stamp']).replace(microsecond=0).isoformat(sep=' ')
                self.db.execute('INSERT OR IGNORE INTO punches VALUES(?,?,?,?)',(str(p['badge']),stamp,str(p.get('kind') or ''),source))
            added=self.db.total_changes-before
            if repaired:self.log(f'Corrected {repaired} device punch dates from {source}; original rows archived')
            self.log(f'Imported {added} new rows from {source}')
        return added

    def read_clone(self):
        """A separate read-only connection for background queries.

        sqlite3 connections are bound to the thread that created them, so a
        worker thread cannot reuse self.db. This clone carries the same actor
        so require() still enforces the role, opens the file read-only so a
        background report can never write, and must be closed by the caller.
        """
        from pathlib import Path
        clone=object.__new__(Store)
        clone.path=self.path
        clone.db=sqlite3.connect(Path(self.path).as_uri()+'?mode=ro',uri=True,timeout=15)
        clone.db.row_factory=sqlite3.Row
        clone.actor=dict(self.actor) if self.actor else None
        return clone

    def close(self):
        self.db.close()

    def punch_bounds(self):
        """First and last punch dates, for bounding the date pickers.

        Returns (low, high) as date objects. Falls back to today when the
        punches table is empty, so the picker still opens on a fresh database.
        """
        row=self.db.execute('SELECT MIN(stamp) AS first, MAX(stamp) AS last FROM punches').fetchone()
        if not row or not row['first']:
            today=date.today(); return today,today
        return (datetime.fromisoformat(row['first']).date(), datetime.fromisoformat(row['last']).date())

    def report(self,begin,finish,badge='',max_days=366,row_cap=0):
        """Daily rows for the period.

        max_days guards the O(days x employees) walk below. The Attendance grid
        raises it for its Full range preset and passes a row_cap instead, so a
        multi-year file returns a truncated report rather than an exception.
        row_cap of 0 means no cap. When the cap trims the result the last row
        carries 'truncated': True so the caller can say so on screen.
        """
        self.require(*ROLES)
        begin=date.fromisoformat(begin); finish=date.fromisoformat(finish)
        max_days=int(max_days); row_cap=int(row_cap)
        if max_days<0 or row_cap<0: raise ValueError('Invalid report limits.')
        if begin>finish: raise ValueError('The From date must not be after the To date.')
        if (finish-begin).days>max_days: raise ValueError(f'Choose an ordered period up to {max_days+1} days.')
        people=self.rows('SELECT * FROM employees WHERE (?="" OR badge=?) ORDER BY badge',(badge,badge))
        ps=self.rows('SELECT badge,stamp FROM punches WHERE stamp>=? AND stamp<? ORDER BY stamp',((begin-timedelta(days=1)).isoformat(),(finish+timedelta(days=2)).isoformat()))
        stamps={}
        for p in ps: stamps.setdefault(p['badge'],set()).add(datetime.fromisoformat(p['stamp']))
        schedules=self.rows('SELECT a.*,s.name,s.start,s.end,s.grace,s.break_mins,s.days FROM assignments a JOIN shifts s ON a.shift_id=s.id')
        output=[]
        for e in people:
            occurrences=[]
            od=begin-timedelta(days=1)
            while od<=finish+timedelta(days=1):
                ss=next((v for v in schedules if v['badge']==e['badge'] and v['begin']<=od.isoformat()<=v['finish'] and str(od.weekday()) in v['days'].split(',')),None)
                if ss:
                    aa=datetime.combine(od,time.fromisoformat(ss['start']));bb=datetime.combine(od,time.fromisoformat(ss['end']))
                    if bb<=aa:bb+=timedelta(days=1)
                    gap=(timedelta(days=1)-(bb-aa))/2
                    occurrences.append((od,aa,bb,aa-gap,bb+gap))
                od+=timedelta(days=1)
            allocated={}
            for t in sorted(stamps.get(e['badge'],[])):
                candidates=[o for o in occurrences if o[3]<=t<o[4]]
                # Assign each punch exactly once, even when shift times change.
                chosen=min(candidates,key=lambda o:(max((o[1]-t).total_seconds(),(t-o[2]).total_seconds(),0),o[1])) if candidates else None
                allocated.setdefault(chosen[0] if chosen else t.date(),[]).append(t)
            d=begin
            while d<=finish:
                s=next((s for s in schedules if s['badge']==e['badge'] and s['begin']<=d.isoformat()<=s['finish']),None)
                scheduled=s and str(d.weekday()) in s['days'].split(',')
                if scheduled:
                    start=datetime.combine(d,time.fromisoformat(s['start'])); end=datetime.combine(d,time.fromisoformat(s['end']))
                    if end<=start: end+=timedelta(days=1)
                    # Windows split at midpoints between daily shifts; each punch belongs to one workday.
                    gap=timedelta(days=1)-(end-start)
                    lo=start-gap/2; hi=end+gap/2
                else: lo=datetime.combine(d,time()); hi=lo+timedelta(days=1)
                hits=allocated.get(d,[])
                first=hits[0] if hits else None; last=hits[-1] if len(hits)>1 else None
                worked=max(0,int((last-first).total_seconds()//60)-(s['break_mins'] if scheduled else 0)) if last else 0
                late=max(0,int((first-start).total_seconds()//60)-s['grace']) if first and scheduled else 0
                early=max(0,int((end-last).total_seconds()//60)) if last and scheduled else 0
                status=('Absent' if scheduled else 'Off / Unscheduled') if not hits else ('Missing punch' if not last else ('Late' if late else 'Present'))
                if scheduled and datetime.now()<end:
                    status='Pending' if datetime.now()<start else 'In progress'
                if hits or scheduled or e['active']:
                    output.append({'date':d.isoformat(),'badge':e['badge'],'name':e['name'],'department':e['department'],'shift':s['name'] if scheduled else '', 'first':str(first or ''),'last':str(last or ''),'punches':len(hits),'worked_minutes':worked,'late_minutes':late,'early_minutes':early,'status':status})
                d+=timedelta(days=1)
            if row_cap and len(output)>=row_cap:
                output=output[:row_cap]
                if output: output[-1]=dict(output[-1],truncated=True)
                return output
        return output

def monthly(rows):
    out={}
    for r in rows:
        k=r['badge']
        if k not in out: out[k]={'badge':k,'name':r['name'],'present_days':0,'absent_days':0,'missing_punch_days':0,'worked_minutes':0,'late_minutes':0,'early_minutes':0}
        t=out[k]; t['present_days']+=int(r['punches']>0); t['absent_days']+=int(r['status']=='Absent'); t['missing_punch_days']+=int(r['status']=='Missing punch')
        for field in ('worked_minutes','late_minutes','early_minutes'): t[field]+=r[field]
    return list(out.values())

def export_csv(path,rows,company=None):
    if not rows: raise ValueError('No rows to export.')
    def safe(v):
        return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        if company and (company.get('company_name') or company.get('branch')):
            metadata=csv.writer(f)
            metadata.writerow(['Company name',safe(company.get('company_name',''))])
            metadata.writerow(['Branch',safe(company.get('branch',''))])
            metadata.writerow([])
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows({k:safe(v) for k,v in r.items()} for r in rows)
