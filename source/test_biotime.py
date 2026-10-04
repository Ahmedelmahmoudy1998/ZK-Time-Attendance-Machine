import json
import sqlite3
import tempfile
import shutil
import uuid
import threading
import unittest
from contextlib import contextmanager, closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from biotime import BioTimeClient, BioTimeError, server_url
from biotime_ui import import_records
from core import Store


@contextmanager
def test_folder():
    root = Path(tempfile.gettempdir()).resolve()
    folder = root / ('oasis-biotime-test-' + uuid.uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        assert folder.resolve().parent == root and folder.name.startswith('oasis-biotime-test-')
        shutil.rmtree(folder)


def punch(id=1, **changes):
    row = dict(id=id, emp_code='00201', first_name='محمد', last_name='أحمد',
               department='Office', terminal_sn='TEST123', punch_time='2026-10-04 08:00:00', punch_state='0')
    row.update(changes)
    return row


@contextmanager
def fake_biotime(mode='ok'):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, data):
            content = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self):
            requests.append(('POST', self.path))
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path != '/jwt-api-token-auth/' or body != {'username': 'tester', 'password': 'test-only'}:
                return self.reply(401, {'detail': 'invalid credentials'})
            self.reply(200, {'token': 'test-token'})

        def do_GET(self):
            requests.append(('GET', self.path))
            if mode == 'redirect':
                self.send_response(302)
                self.send_header('Location', 'http://127.0.0.1:1/steal')
                self.end_headers()
                return
            if self.headers.get('Authorization') != 'JWT test-token' or mode == 'denied':
                return self.reply(403, {'detail': 'not permitted'})
            query = parse_qs(urlsplit(self.path).query)
            if query.get('terminal_sn') != ['TEST123']:
                return self.reply(400, {})
            page = query.get('page', ['1'])[0]
            next_page = self.path.replace('page=1', 'page=2') if page == '1' else None
            rows = [punch()] if page == '1' else [punch(2, punch_time='2026-10-04 17:00:00')]
            if mode == 'external':
                next_page = 'http://127.0.0.1:1/steal'
            if mode == 'mismatch':
                rows[0]['terminal_sn'] = 'OTHER'
            if mode == 'incomplete':
                next_page = None
            if mode == 'invalid-date':
                rows[0]['punch_time'] = 'bad-date'
            if mode == 'timezone':
                rows[0]['punch_time'] += '+03:00'
            if mode == 'outside':
                rows[0]['punch_time'] = '2026-10-05 08:00:00'
            if mode == 'duplicate-page' and page == '2':
                rows = [punch()]
            if mode == 'duplicate-punch' and page == '2':
                rows = [punch(2)]
            self.reply(200, {'code': 0, 'count': 2, 'data': rows, 'next': next_page})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', requests
    finally:
        server.shutdown(); server.server_close(); thread.join(3)


class BioTimeTests(unittest.TestCase):
    def download(self, client, password='test-only'):
        return client.download('tester', password, 'TEST123', '2026-10-04', '2026-10-04')

    def test_paginated_download_backup_and_idempotent_import(self):
        with fake_biotime() as (url, requests), test_folder() as folder:
            client = BioTimeClient(url)
            employees, punches = self.download(client)
            self.assertIsNone(client.token)
            self.assertEqual(employees, [{'badge': '00201', 'name': 'محمد أحمد', 'department': 'Office'}])
            self.assertEqual([p['stamp'] for p in punches], ['2026-10-04 08:00:00', '2026-10-04 17:00:00'])
            self.assertEqual([r[0] for r in requests], ['POST', 'GET', 'GET'])
            self.assertTrue(all(r[1].startswith('/iclock/api/transactions/') for r in requests[1:]))
            store = Store(Path(folder) / 'app.sqlite')
            try:
                store.account('owner', 'test-only-password', 'admin', True)
                store.login('owner', 'test-only-password')
                counts = import_records(store, (employees, punches), 'BioTime test', Path(folder) / 'backups')
                self.assertEqual(counts[:2], (1, 2))
                with closing(sqlite3.connect(counts[2])) as backup:
                    self.assertEqual(backup.execute('SELECT COUNT(*) FROM punches').fetchone()[0], 0)
                store.employee('00201', 'Existing local name', 'Local department')
                repeated = import_records(store, (employees, punches), 'BioTime test', Path(folder) / 'backups')
                self.assertEqual(repeated[:2], (0, 0))
                self.assertEqual(store.rows('SELECT name FROM employees')[0]['name'], 'Existing local name')
            finally:
                store.db.close()

    def test_authentication_failure_does_not_request_attendance(self):
        with fake_biotime() as (url, requests):
            client = BioTimeClient(url)
            with self.assertRaisesRegex(BioTimeError, 'login failed'):
                self.download(client, 'wrong')
            self.assertEqual(len(requests), 1)
            self.assertIsNone(client.token)

    def test_errors_reject_entire_download_and_clear_token(self):
        for mode in ('denied', 'redirect', 'external', 'mismatch', 'incomplete', 'invalid-date', 'timezone', 'outside', 'duplicate-page'):
            with self.subTest(mode=mode), fake_biotime(mode) as (url, requests):
                client = BioTimeClient(url)
                with self.assertRaises(BioTimeError):
                    self.download(client)
                self.assertIsNone(client.token)

    def test_duplicate_punches_from_different_api_ids_are_consolidated(self):
        with fake_biotime('duplicate-punch') as (url, requests):
            self.assertEqual(len(self.download(BioTimeClient(url))[1]), 1)

    def test_server_validation_and_no_network_on_invalid_inputs(self):
        for value in ('ftp://localhost', 'http://user:secret@localhost', 'http://192.168.0.11',
                      'https://example.com/path', 'https://example.com?secret=1', 'http://localhost:99999'):
            with self.subTest(url=value), self.assertRaises(BioTimeError):
                server_url(value)
        self.assertEqual(server_url(' http://127.0.0.1/ '), 'http://127.0.0.1')
        self.assertEqual(server_url('https://biotime.example.com'), 'https://biotime.example.com')
        client = BioTimeClient('http://127.0.0.1')
        with patch.object(client, '_request') as request:
            for serial, begin, finish in (('', '2026-10-04', '2026-10-04'), ('TEST123', 'bad', '2026-10-04'),
                                           ('TEST123', '2026-10-05', '2026-10-04')):
                with self.assertRaises(BioTimeError):
                    client.download('tester', 'password', serial, begin, finish)
            request.assert_not_called()

    def test_failed_import_rolls_back_and_keeps_backup(self):
        with test_folder() as folder:
            store = Store(Path(folder) / 'app.sqlite')
            try:
                store.account('owner', 'test-only-password', 'admin', True)
                store.login('owner', 'test-only-password')
                data = ([{'badge': '1', 'name': 'One'}, {}], [])
                with self.assertRaises(KeyError):
                    import_records(store, data, 'BioTime test', Path(folder) / 'backups')
                self.assertEqual(store.rows('SELECT * FROM employees'), [])
                self.assertEqual(len(list((Path(folder) / 'backups').glob('*.sqlite'))), 1)
                store.actor = {'username': 'reader', 'role': 'reports'}
                with self.assertRaises(PermissionError):
                    import_records(store, ([], []), 'BioTime test', Path(folder) / 'other')
                self.assertFalse((Path(folder) / 'other').exists())
            finally:
                store.db.close()


if __name__ == '__main__':
    unittest.main()
