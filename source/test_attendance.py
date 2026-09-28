"""Attendance date range, bounds, read clone and pairing display."""
import sys, types, tempfile, unittest, uuid, shutil
from datetime import date
from pathlib import Path

# datepicker imports tkinter for its widgets; the pure date maths is tested
# without a display by stubbing the module.
if 'tkinter' not in sys.modules:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        stub = types.ModuleType('tkinter')
        stub.Toplevel = stub.StringVar = stub.BooleanVar = object
        ttk = types.ModuleType('tkinter.ttk')
        ttk.Frame = ttk.Label = ttk.Button = object
        stub.ttk = ttk
        sys.modules['tkinter'] = stub
        sys.modules['tkinter.ttk'] = ttk

from core import Store
from datepicker import PRESETS, preset_range


class Attendance(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.gettempdir()) / ('oasis-attendance-test-' + uuid.uuid4().hex)
        self.folder.mkdir()
        self.store = Store(Path(self.folder) / 'test.sqlite')
        self.store.account('admin', 'passwordpass', 'admin', bootstrap=True)
        self.store.login('admin', 'passwordpass')
        self.store.employee('201', 'Test Employee', 'IT')
        self.store.shift('Day', '08:00', '17:00', 5, 60, '0,1,2,3,6')
        self.store.assign('201', 1, '2026-09-01', '2026-12-31')
        punches = []
        for day in range(1, 6):
            punches.append({'badge': '201', 'stamp': f'2026-09-0{day} 08:03:00'})
            if day != 3:                      # day 3 keeps a single punch
                punches.append({'badge': '201', 'stamp': f'2026-09-0{day} 17:11:00'})
        self.store.ingest([], punches, 'test')

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.folder)

    def test_bounds_come_from_the_data(self):
        self.assertEqual(self.store.punch_bounds(), (date(2026, 9, 1), date(2026, 9, 5)))

    def test_bounds_fall_back_to_today_when_empty(self):
        empty = Store(Path(self.folder) / 'empty.sqlite')
        try:
            low, high = empty.punch_bounds()
            self.assertEqual(low, date.today())
            self.assertEqual(low, high)
        finally:
            empty.close()

    def test_single_punch_day_has_no_out_time(self):
        rows = {r['date']: r for r in self.store.report('2026-09-01', '2026-09-05', '201')}
        day = rows['2026-09-03']
        self.assertEqual(day['punches'], 1)
        self.assertFalse(day['last'])
        self.assertEqual(day['status'], 'Missing punch')

    def test_row_cap_marks_the_last_row(self):
        rows = self.store.report('2026-09-01', '2026-09-05', '', row_cap=3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[-1].get('truncated'))

    def test_default_day_cap_still_applies(self):
        with self.assertRaises(ValueError):
            self.store.report('2020-01-01', '2026-09-05', '')

    def test_raised_cap_allows_a_multi_year_range(self):
        rows = self.store.report('2020-01-01', '2026-09-05', '201', max_days=3660, row_cap=10)
        self.assertEqual(len(rows), 10)

    def test_read_clone_cannot_write(self):
        clone = self.store.read_clone()
        try:
            self.assertEqual(len(clone.report('2026-09-01', '2026-09-05', '201')), 5)
            with self.assertRaises(Exception):
                clone.db.execute("INSERT INTO punches VALUES('x','2026-01-01 00:00:00','','t')")
        finally:
            clone.close()

    def test_presets_are_ordered(self):
        low, high = date(2026, 9, 1), date(2026, 9, 5)
        for name in PRESETS:
            begin, finish = preset_range(name, low, high, today=date(2026, 9, 7))
            self.assertLessEqual(begin, finish)

    def test_range_is_open_and_not_clamped_to_the_data(self):
        """Presets outside the data bounds must survive. The picker is an open
        range: bounds only position the calendar and resolve Full range."""
        low, high = date(2026, 9, 1), date(2026, 9, 5)
        begin, finish = preset_range('Today', low, high, today=date(2026, 9, 7))
        self.assertEqual((begin, finish), (date(2026, 9, 7), date(2026, 9, 7)))

    def test_report_accepts_a_period_outside_the_data(self):
        """An open range must not raise. Active employees still get a row per
        day, with no punches, which is what an absence looks like."""
        rows = self.store.report('2019-01-01', '2019-01-31', '201', max_days=36600)
        self.assertEqual(len(rows), 31)
        self.assertTrue(all(r['punches'] == 0 and not r['first'] for r in rows))

    def test_full_range_is_the_whole_file(self):
        low, high = date(2024, 1, 1), date(2026, 9, 5)
        self.assertEqual(preset_range('Full range', low, high), (low, high))

    def test_last_month_crosses_the_year_boundary(self):
        low, high = date(2024, 1, 1), date(2026, 12, 31)
        self.assertEqual(preset_range('Last month', low, high, today=date(2026, 1, 15)),
                         (date(2025, 12, 1), date(2025, 12, 31)))


if __name__ == '__main__':
    unittest.main()
