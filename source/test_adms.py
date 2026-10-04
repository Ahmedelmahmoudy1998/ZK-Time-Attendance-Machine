import http.client
import socket
import sqlite3
import unittest
from contextlib import closing
from urllib.parse import urlencode
from adms import Receiver, configuration, start_receiver
from core import Store
from test_biotime import test_folder


class AdmsTests(unittest.TestCase):
    def setUp(self):
        self.folder_context = test_folder()
        self.folder = self.folder_context.__enter__()
        self.store = Store(self.folder / 'test.sqlite')
        self.store.actor = {'username': 'test-admin', 'role': 'admin'}
        with closing(socket.socket()) as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.config = dict(host='127.0.0.1', port=self.port, peer='127.0.0.1', serial='TEST123')
        self.receiver, self.backup = start_receiver(self.store, self.config, self.folder / 'backups')

    def tearDown(self):
        self.receiver.stop()
        self.store.db.close()
        self.folder_context.__exit__(None, None, None)

    def request(self, method='GET', path='/iclock/cdata', body=None, **query):
        query.setdefault('SN', 'TEST123')
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=8)
        try:
            conn.request(method, path + '?' + urlencode(query), body.encode('utf-8') if isinstance(body, str) else body)
            response = conn.getresponse()
            return response.status, response.read().decode('utf-8').strip()
        finally:
            conn.close()

    def upload(self, body='00201\t2026-10-04 08:00:00\t0\t15\t0\t0\t0', **query):
        return self.request('POST', body=body, table='ATTLOG', Stamp='12345', **query)

    def test_handshake_heartbeat_allowlist(self):
        code, body = self.request(options='all')
        self.assertEqual(code, 200)
        self.assertIn('ATTLOGStamp=0', body)
        self.assertIn('EnrollUser', body)
        self.assertNotIn('EnrollFP', body)
        self.assertEqual(self.request(path='/iclock/getrequest'), (200, 'OK'))
        self.assertEqual(self.request(path='/iclock/ping.aspx'), (200, 'OK'))
        self.assertEqual(self.upload(SN='UNKNOWN')[0], 403)
        self.receiver.config['peer'] = '127.0.0.2'
        self.assertEqual(self.upload()[0], 403)
        self.assertEqual(self.store.rows('SELECT * FROM punches'), [])

    def test_backup_commit_checkpoint_and_duplicate_restart(self):
        with closing(sqlite3.connect(self.backup)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM punches').fetchone()[0], 0)
        self.assertEqual(self.upload(), (200, 'OK: 1'))
        self.assertEqual(self.upload(), (200, 'OK: 1'))
        rows = self.store.rows('SELECT * FROM punches')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['badge'], '00201')
        self.assertEqual(rows[0]['stamp'], '2026-10-04T08:00:00')
        self.receiver.stop()
        self.receiver = Receiver(self.store.path, self.config)
        self.receiver.start()
        self.assertIn('ATTLOGStamp=12345', self.request()[1])
        self.assertEqual(self.upload(), (200, 'OK: 1'))
        self.assertEqual(self.receiver.status()['new_punches'], 0)

    def test_users_preserve_custom_names_and_no_secrets(self):
        self.store.employee('10', 'Existing custom name', 'Office')
        self.upload()
        body = ('USER PIN=00201\tName=محمد أحمد\tPri=0\tPasswd=SECRET\tCard=123\n'
                'USER PIN=10\tName=Device name\tPasswd=SECRET\n'
                'FP PIN=00201\tTMP=PRIVATE_TEMPLATE')
        self.assertEqual(self.request('POST', table='OPERLOG', Stamp='88', body=body), (200, 'OK: 3'))
        employees = {r['badge']: r for r in self.store.rows('SELECT * FROM employees')}
        self.assertEqual(employees['00201']['name'], 'محمد أحمد')
        self.assertEqual(employees['10']['name'], 'Existing custom name')
        dump = '\n'.join(self.store.db.iterdump())
        self.assertNotIn('SECRET', dump)
        self.assertNotIn('PRIVATE_TEMPLATE', dump)

    def test_invalid_batch_atomic_no_checkpoint(self):
        for bad in ('broken', '201\t2026-02-30 10:00:00\t0\t1', '201\t2026-10-04 10:00:00\tx\t1'):
            self.assertEqual(self.upload('201\t2026-10-04 08:00:00\t0\t15\n' + bad)[0], 400)
        self.assertEqual(self.store.rows('SELECT * FROM punches'), [])
        self.assertEqual(self.store.rows('SELECT * FROM employees'), [])
        self.assertIn('ATTLOGStamp=0', self.request()[1])

    def test_database_busy_retries_without_acknowledging(self):
        self.store.db.execute('BEGIN IMMEDIATE')
        try:
            self.assertEqual(self.upload()[0], 503)
        finally:
            self.store.db.rollback()
        self.assertEqual(self.upload(), (200, 'OK: 1'))
        self.assertEqual(self.receiver.status()['new_punches'], 1)

    def test_commit_failure_rolls_back_punch_employee_and_checkpoint(self):
        self.store.db.execute("CREATE TRIGGER fail_checkpoint BEFORE INSERT ON adms_checkpoints BEGIN SELECT RAISE(ABORT,'test failure'); END")
        self.store.db.commit()
        self.assertEqual(self.upload()[0], 503)
        self.assertEqual(self.store.rows('SELECT * FROM punches'), [])
        self.assertEqual(self.store.rows('SELECT * FROM employees'), [])
        self.assertEqual(self.store.rows('SELECT * FROM adms_checkpoints'), [])
        self.store.db.execute('DROP TRIGGER fail_checkpoint')
        self.store.db.commit()
        self.assertEqual(self.upload(), (200, 'OK: 1'))

    def test_history_only_read_command_and_ack_not_completion(self):
        self.receiver.request_history('2026-10-01', '2026-10-04')
        with self.assertRaises(ValueError):
            self.receiver.request_history('2026-10-01', '2026-10-04')
        code, command = self.request(path='/iclock/getrequest')
        self.assertEqual(code, 200)
        self.assertIn('DATA QUERY ATTLOG StartTime=2026-10-01 00:00:00\tEndTime=2026-10-04 23:59:59', command)
        self.assertEqual(self.request(path='/iclock/getrequest'), (200, 'OK'))
        command_id = command.split(':')[1]
        self.assertEqual(self.request('POST', '/iclock/devicecmd', f'ID={command_id}&Return=0&CMD=DATA'), (200, 'OK'))
        self.assertIn('does not confirm', self.receiver.status()['command'])
        self.receiver.request_history('2026-10-01', '2026-10-04')
        self.receiver.cancel_history()
        self.assertEqual(self.request(path='/iclock/getrequest'), (200, 'OK'))

    def test_no_replacement_of_biotime_punch(self):
        with self.store.db:
            self.store.db.execute("INSERT INTO punches VALUES('00201','2026-10-04T08:00:00','I','BioTime')")
        self.assertEqual(self.upload(), (200, 'OK: 1'))
        self.assertEqual(self.store.rows('SELECT * FROM punches')[0]['source'], 'BioTime')
        self.assertEqual(self.receiver.status()['new_punches'], 0)

    def test_configuration_role_and_input_limits(self):
        with self.assertRaises(ValueError):
            configuration('0.0.0.0', 8081, '127.0.0.1', 'ABC')
        self.store.actor = {'username': 'reader', 'role': 'reports'}
        with self.assertRaises(PermissionError):
            start_receiver(self.store, self.config, self.folder)
        self.assertEqual(self.request('POST', table='ATTLOG', body=b'\xff')[0], 400)
        self.assertEqual(self.request('POST', table='BIODATA', body='ignored')[0], 400)
        self.assertEqual(self.request('POST', table='ATTLOG', Stamp='bad\nvalue', body='')[0], 400)
        self.assertEqual(self.request(path='/unknown')[0], 404)


if __name__ == '__main__':
    unittest.main()
