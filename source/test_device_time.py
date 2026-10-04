from datetime import datetime
from pathlib import Path
import shutil, sqlite3, struct, tempfile, unittest, uuid
from core import Store
from device_time import decode_device_time, previous_decoded_time


def packed(t):
    return struct.pack('<I', (((t.year-2000)*12*31+(t.month-1)*31+t.day-1)*24+t.hour)*3600+t.minute*60+t.second)


class DeviceTimeTests(unittest.TestCase):
    def test_protocol_dates(self):
        for value in ('2000-01-01 00:00:00','2026-10-04 13:51:21','2026-12-31 23:59:59',
                      '2027-01-01 00:00:00','2024-02-29 08:00:00','2099-12-31 23:59:59'):
            t=datetime.fromisoformat(value)
            self.assertEqual(decode_device_time(packed(t)),t)

    def test_reported_year_error(self):
        data=packed(datetime(2026,10,4,13,51,21))
        self.assertEqual(previous_decoded_time(data),datetime(2027,10,4,13,51,21))
        self.assertEqual(decode_device_time(data),datetime(2026,10,4,13,51,21))

    def test_invalid_dates_rejected(self):
        with self.assertRaises(ValueError):decode_device_time(struct.pack('<I',(26*372+31+30)*86400))
        with self.assertRaises(struct.error):decode_device_time(b'bad')


class DeviceRepairTests(unittest.TestCase):
    def setUp(self):
        self.folder=Path(tempfile.gettempdir())/('oasis-time-test-'+uuid.uuid4().hex);self.folder.mkdir()
        self.store=Store(self.folder/'test.sqlite')
        self.store.account('admin','password','admin',True);self.store.login('admin','password')
        self.old='2027-10-04 13:51:21';self.new='2026-10-04 13:51:21'
        self.row={'badge':'201','stamp':self.new,'kind':'0','legacy_stamp':self.old}
        self.store.ingest([{'badge':'201','name':'Example'}],[dict(self.row,stamp=self.old,legacy_stamp=None)],'device')

    def tearDown(self):
        self.store.close();shutil.rmtree(self.folder)

    def test_corrects_archives_and_reports_idempotently(self):
        for _ in range(2):self.store.ingest([], [self.row], 'device')
        self.assertEqual(self.store.rows('SELECT stamp FROM punches'),[{'stamp':self.new}])
        self.assertEqual(self.store.rows('SELECT original_stamp FROM punch_time_repair_archive'),[{'original_stamp':self.old}])
        report=self.store.report('2026-10-04','2026-10-04','201')
        self.assertEqual(report[0]['punches'],1);self.assertEqual(report[0]['first'],self.new)

    def test_different_source_is_not_moved(self):
        self.store.ingest([], [self.row], 'other device')
        self.assertEqual(len(self.store.rows('SELECT stamp FROM punches')),2)

    def test_genuine_future_record_is_not_moved(self):
        self.store.ingest([], [self.row,dict(self.row,stamp=self.old,legacy_stamp=None)], 'device')
        self.assertEqual(len(self.store.rows('SELECT stamp FROM punches')),2)

    def test_existing_correct_record_is_not_duplicated(self):
        self.store.ingest([], [dict(self.row,legacy_stamp=None)], 'MDB')
        self.store.ingest([], [self.row], 'device')
        self.assertEqual(self.store.rows('SELECT stamp,source FROM punches'),[{'stamp':self.new,'source':'MDB'}])

    def test_failure_rolls_back_date_repair(self):
        self.store.db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):self.store.ingest([], [self.row], 'device')
        self.assertEqual(self.store.rows('SELECT stamp FROM punches'),[{'stamp':self.old}])


if __name__=='__main__':unittest.main()
