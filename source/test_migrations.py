import unittest,sqlite3,json,uuid
from pathlib import Path
from core import Store
from settings import migrate_settings

class MigrationTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.root=Path(tempfile.gettempdir())/('oasis-test-'+uuid.uuid4().hex);self.root.mkdir()
    def tearDown(self):
        import shutil
        shutil.rmtree(self.root)
    def legacy(self):
        path=self.root/'test.sqlite';db=sqlite3.connect(path)
        db.execute("CREATE TABLE punches(badge TEXT NOT NULL,stamp TEXT NOT NULL,kind TEXT NOT NULL,source TEXT NOT NULL,UNIQUE(badge,stamp,kind,source))")
        db.executemany('INSERT INTO punches VALUES(?,?,?,?)',[
            ('001','2020-09-07 08:00:00','I','MDB'),
            ('001','2020-09-07 08:00:00','0','device'),
            ('001','2020-09-07 17:00:00','O','MDB'),
            ('002','2020-09-07 08:00:00','I','MDB')])
        db.commit();db.close();return path
    def test_migrate_and_reimport(self):
        path=self.legacy();s=Store(path)
        self.assertEqual(len(s.rows('SELECT * FROM punches')),3)
        self.assertEqual(s.rows('SELECT * FROM punches WHERE badge=? AND stamp=?',('001','2020-09-07 08:00:00'))[0]['source'],'MDB')
        self.assertEqual(len(s.rows('SELECT * FROM punch_duplicate_archive')),1)
        s.account('owner','strong-pass-123','admin',True);s.login('owner','strong-pass-123')
        self.assertEqual(s.ingest([],[{'badge':'001','stamp':'2020-09-07 08:00:00','kind':'0'}],'other device'),0)
        s.db.close();s=Store(path)
        self.assertEqual(len(s.rows('SELECT * FROM punch_duplicate_archive')),1)
        self.assertEqual(len(s.rows("SELECT * FROM audit WHERE action LIKE 'Punch identity migration%'")),1);s.db.close()
    def test_atomic_rollback(self):
        path=self.legacy();db=sqlite3.connect(path)
        db.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,stamp TEXT,actor TEXT,action TEXT)')
        db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        db.commit();db.close()
        with self.assertRaises(sqlite3.IntegrityError):Store(path)
        db=sqlite3.connect(path);self.assertEqual(db.execute('SELECT COUNT(*) FROM punches').fetchone()[0],4)
        self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='punches_v2'").fetchone());db.close()
    def test_settings_migration_preserves_old_and_new(self):
        old=self.root/'ZKDesk';old.mkdir();data={'database':'D:/attendance.sqlite','language':'ar'}
        (old/'settings.json').write_text(json.dumps(data))
        new=migrate_settings(self.root);self.assertEqual(json.loads(new.read_text()),data)
        self.assertTrue((old/'settings.json').exists())
        new.write_text('{"language":"en"}');migrate_settings(self.root)
        self.assertEqual(json.loads(new.read_text()),{'language':'en'})

if __name__=='__main__':unittest.main()
