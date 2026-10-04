import unittest, tempfile, uuid, shutil
from pathlib import Path
from core import Store, monthly, export_csv

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.gettempdir())/('zk-test-'+uuid.uuid4().hex); self.tmp.mkdir(); self.s=Store(self.tmp/'db.sqlite')
        self.s.account('owner','strong-pass-123','admin',True); self.s.login('owner','strong-pass-123')
        self.s.employee('1','Example','Office')
    def tearDown(self):
        self.s.db.close()
        for p in self.tmp.iterdir():p.unlink()
        self.tmp.rmdir()
    def test_device_key_persists_and_edit_keeps_identity(self):
        self.s.device('Terminal','127.0.0.1',4370,0,123)
        device=self.s.rows('SELECT * FROM devices')[0]
        self.s.device('Imported','127.0.0.1',4370,0)
        self.assertEqual(self.s.rows('SELECT comm_key FROM devices')[0]['comm_key'],123)
        self.s.device('Moved','127.0.0.2',4370,0,0,device['id'])
        self.s.close();self.s=Store(self.tmp/'db.sqlite')
        rows=self.s.rows('SELECT id,ip,comm_key FROM devices')
        self.assertEqual(rows,[{'id':device['id'],'ip':'127.0.0.2','comm_key':0}])

    def test_invalid_device_key_leaves_saved_value(self):
        self.s.device('Terminal','127.0.0.1',4370,0,123)
        for value in (-1,4294967296,'bad'):
            with self.assertRaises(ValueError):self.s.device('Terminal','127.0.0.1',4370,0,value)
        self.assertEqual(self.s.rows('SELECT comm_key FROM devices')[0]['comm_key'],123)

    def test_roles(self):
        self.s.account('viewer','strong-pass-123','reports'); self.s.login('viewer','strong-pass-123')
        for f in [lambda:self.s.employee('2','Other'),lambda:self.s.device('a','127.0.0.1',4370,0),lambda:self.s.shift('x','08:00','17:00',0,0,'0'),lambda:self.s.ingest([],[],'x'),lambda:self.s.account('x','strong-pass-123','admin',True)]:
            with self.assertRaises(PermissionError):f()
        self.assertTrue(self.s.report('2026-09-07','2026-09-07'))
    def test_duplicate_import(self):
        p=[{'badge':'1','stamp':'2026-09-07 08:00:00','kind':'0'}]
        self.assertEqual(self.s.ingest([],p,'dev'),1); self.assertEqual(self.s.ingest([],p,'dev'),0)
    def test_overnight(self):
        self.s.shift('Night','22:00','06:00',5,30,'0')
        self.s.assign('1',1,'2026-09-01','2026-09-30')
        self.s.ingest([],[{'badge':'1','stamp':t} for t in ['2026-09-07 22:12:00','2026-09-08 05:50:00']],'dev')
        a,b=self.s.report('2026-09-07','2026-09-08')
        self.assertEqual(a['worked_minutes'],428); self.assertEqual(a['late_minutes'],7); self.assertEqual(a['early_minutes'],10); self.assertEqual(b['punches'],0)
    def test_absence_missing_and_month(self):
        self.s.shift('Day','08:00','17:00',5,60,'0,1,2,3,4'); self.s.assign('1',1,'2020-09-01','2020-09-30')
        self.s.ingest([],[{'badge':'1','stamp':'2020-09-07 08:00:00'}],'dev')
        rows=self.s.report('2020-09-07','2020-09-08')
        self.assertEqual(rows[0]['status'],'Missing punch'); self.assertEqual(rows[1]['status'],'Absent'); self.assertEqual(rows[0]['worked_minutes'],0)
        self.assertEqual(monthly(rows)[0]['absent_days'],1)
    def test_assignment_overlap(self):
        self.s.shift('Day','08:00','17:00',0,0,'0'); self.s.assign('1',1,'2026-09-01','2026-09-30')
        with self.assertRaises(ValueError):self.s.assign('1',1,'2026-09-30','2026-10-02')
    def test_atomic_import(self):
        with self.assertRaises(ValueError): self.s.ingest([{'badge':'9','name':'Rollback'}],[{'badge':'9','stamp':'invalid'}],'dev')
        self.assertFalse(self.s.rows('SELECT * FROM employees WHERE badge="9"'))
    def test_password_and_lockout(self):
        self.s.actor=None
        for _ in range(5):
            with self.assertRaises(ValueError):self.s.login('owner','wrong')
        with self.assertRaisesRegex(ValueError,'locked'):self.s.login('owner','strong-pass-123')
    def test_eight_character_password_without_complexity(self):
        self.s.account('simple','abcdefgh','reports')
        self.s.login('simple','abcdefgh')
        self.assertEqual(self.s.actor['username'],'simple')
        self.s.login('owner','strong-pass-123')
        self.s.account('simple','12345678','reports')
        self.s.login('simple','12345678')
        self.s.login('owner','strong-pass-123')
        with self.assertRaisesRegex(ValueError,'at least 8 characters'):
            self.s.account('simple','1234567','reports')
        self.s.login('simple','12345678')
    def test_csv_formula(self):
        path=self.tmp/'out.csv'; export_csv(path,[{'name':'=SUM(A1:A2)'}]); self.assertIn("'=SUM",path.read_text('utf-8-sig'))

if __name__=='__main__':unittest.main()
