"""Small attendance-only ZKTeco PUSH receiver. No BioTime service is required.

Only the configured terminal IP and serial are accepted. Transactions commit
before acknowledgement, including the terminal's opaque upload checkpoint.
No biometric data, passwords, or raw request bodies are retained.
"""
import ipaddress
import re
import socket
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from datetime import datetime, date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

MAX_BODY = 4 * 1024 * 1024


def configuration(host, port, peer, serial):
    host, peer = str(ipaddress.IPv4Address(host)), str(ipaddress.IPv4Address(peer))
    if any(ipaddress.ip_address(value).is_unspecified or ipaddress.ip_address(value).is_multicast
           for value in (host, peer)):
        raise ValueError('Choose a specific PC IP and device IP.')
    port = int(port)
    serial = serial.strip()
    if not 1024 <= port <= 65535 or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', serial):
        raise ValueError('Enter a port from 1024 to 65535 and a valid device serial number.')
    return dict(host=host, port=port, peer=peer, serial=serial)


def local_addresses():
    try:
        return sorted({v[4][0] for v in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                       if not v[4][0].startswith('127.')})
    except OSError:
        return []


def server_timezone():
    minutes = int(datetime.now().astimezone().utcoffset().total_seconds() / 60)
    return minutes // 60 if minutes % 60 == 0 and -720 < minutes < 720 else minutes


def badge(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', value):
        raise ValueError('Invalid badge in device upload.')
    return value


def attendance(body):
    result = []
    for line in body.splitlines():
        if not line.strip():
            continue
        fields = line.split('\t')
        if len(fields) < 4 or len(fields) > 32:
            raise ValueError('Invalid attendance format; batch was not saved.')
        pin = badge(fields[0])
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', fields[1]):
            raise ValueError('Invalid attendance time; batch was not saved.')
        stamp = datetime.strptime(fields[1], '%Y-%m-%d %H:%M:%S').isoformat(sep=' ', timespec='seconds')
        if not re.fullmatch(r'\d{1,3}', fields[2]):
            raise ValueError('Invalid attendance state; batch was not saved.')
        result.append((pin, stamp, fields[2]))
    return result


def users(body):
    result = []
    lines = [line for line in body.splitlines() if line.strip()]
    for line in lines:
        if not line.startswith('USER '):
            # OPERLOG may contain operation events or unsolicited templates.
            # They are deliberately not stored or requested by this receiver.
            continue
        fields = dict(re.findall(r'(?:^|[\t ])([A-Za-z]+)=(.*?)(?=\t| [A-Za-z]+=|$)', line[5:]))
        pin = badge(fields.get('PIN', ''))
        name = fields.get('Name', '').strip() or pin
        if len(name) > 160 or any(ord(c) < 32 for c in name):
            raise ValueError('Invalid employee name; batch was not saved.')
        result.append((pin, name))
    return result, len(lines)


class LimitedServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = False

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(8)
        self.active = set()
        self.active_lock = threading.Lock()
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            with self.active_lock:
                self.active.add(request)
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            with self.active_lock:
                self.active.discard(request)
            self.slots.release()

    def close_connections(self):
        with self.active_lock:
            for connection in self.active:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


class Receiver:
    def __init__(self, database, config):
        self.database = str(Path(database).resolve())
        self.config = configuration(**config)
        self.lock = threading.Lock()
        self.state = dict(last_seen='', last_upload='', uploads=0, received_punches=0, new_punches=0, error='', command='')
        self.server = None
        self.thread = None

    def connect(self):
        # mode=rw prevents accidentally creating a different empty database.
        return sqlite3.connect(Path(self.database).as_uri() + '?mode=rw', uri=True, timeout=2)

    def status(self):
        with self.lock:
            return dict(self.state)

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def start(self):
        if self.server:
            raise ValueError('The receiver is already running.')
        with closing(self.connect()) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS adms_checkpoints(serial TEXT,kind TEXT,stamp TEXT NOT NULL,PRIMARY KEY(serial,kind));
                CREATE TABLE IF NOT EXISTS adms_placeholders(badge TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS adms_commands(id INTEGER PRIMARY KEY AUTOINCREMENT,serial TEXT,command TEXT,created TEXT,sent REAL DEFAULT 0,result TEXT);
            ''')
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'OasisAttend'
            sys_version = ''

            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *args):
                pass

            def do_GET(self):
                self.dispatch()

            def do_POST(self):
                self.dispatch()

            def dispatch(self):
                try:
                    parsed = urlsplit(self.path)
                    query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=64)
                    if (self.client_address[0] != receiver.config['peer'] or
                            query.get('SN') != [receiver.config['serial']]):
                        self.respond(403, 'Unregistered terminal')
                        return
                    receiver.update(last_seen=datetime.now().isoformat(timespec='seconds'))
                    body = ''
                    if self.command == 'POST':
                        lengths = self.headers.get_all('Content-Length', [])
                        if self.headers.get('Transfer-Encoding') or len(lengths) != 1:
                            self.respond(411, 'Content-Length required')
                            return
                        length = int(lengths[0])
                        if not 0 <= length <= MAX_BODY:
                            self.respond(413, 'Upload too large')
                            return
                        raw = self.rfile.read(length)
                        if len(raw) != length:
                            raise ValueError('Incomplete device upload; batch was not saved.')
                        body = raw.decode('utf-8-sig')
                    path = parsed.path.removesuffix('.aspx').rstrip('/')
                    code, answer = receiver.request(self.command, path, query, body)
                    self.respond(code, answer)
                except (ValueError, UnicodeError):
                    receiver.update(error='Invalid device upload; batch was not saved. Check device text encoding and retry.')
                    self.respond(400, 'Invalid upload; not saved')
                except sqlite3.Error:
                    receiver.update(error='Database busy or unavailable; upload was not acknowledged. The device can retry.')
                    self.respond(503, 'Database unavailable; retry')
                except (OSError, TimeoutError):
                    receiver.update(error='Device connection interrupted; check the latest upload status.')

            def respond(self, code, text):
                payload = (text + '\n').encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(payload)

        self.server = LimitedServer((self.config['host'], self.config['port']), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': 0.1}, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.close_connections()
            self.server.server_close()  # Finish bounded in-flight transactions before switching databases.
            self.thread.join()
            self.server = None

    def request(self, method, path, query, body):
        serial = self.config['serial']
        if method == 'GET' and path == '/iclock/cdata':
            with closing(self.connect()) as db:
                stamps = dict(db.execute('SELECT kind,stamp FROM adms_checkpoints WHERE serial=?', (serial,)))
            return 200, '\n'.join((f'GET OPTION FROM: {serial}',
                'ATTLOGStamp=' + stamps.get('ATTLOG', '0'),
                'OPERLOGStamp=' + stamps.get('OPERLOG', '0'),
                'ErrorDelay=30', 'Delay=10', 'TransTimes=00:00;14:05', 'TransInterval=1',
                'TransFlag=TransData AttLog\tOpLog\tEnrollUser\tChgUser',
                f'TimeZone={server_timezone()}', 'Realtime=1', 'Encrypt=None',
                'ServerVer=2.4.1', 'PushProtVer=2.4.1', 'PushOptionsFlag=0'))
        if method == 'GET' and path == '/iclock/ping':
            return 200, 'OK'
        if method == 'GET' and path == '/iclock/getrequest':
            with closing(self.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT id,command,sent FROM adms_commands WHERE serial=? AND result IS NULL ORDER BY id LIMIT 1', (serial,)).fetchone()
                if row and time.time() - row[2] >= 60:
                    db.execute('UPDATE adms_commands SET sent=? WHERE id=?', (time.time(), row[0]))
                    self.update(command='History request sent; waiting for uploads.')
                    return 200, f'C:{row[0]}:{row[1]}'
            return 200, 'OK'
        if method in ('GET', 'POST') and path == '/iclock/devicecmd':
            replies = [query] if method == 'GET' else [parse_qs(line, max_num_fields=16) for line in body.splitlines() if line]
            matched = []
            with closing(self.connect()) as db, db:
                for values in replies:
                    command_id = values.get('ID', values.get('CmdID', ['']))[0]
                    result = values.get('Return', [''])[0]
                    if not re.fullmatch(r'-?\d{1,10}', result):
                        raise ValueError('Invalid command reply')
                    if not re.fullmatch(r'\d{1,16}', command_id):
                        continue  # Replies to a previous server's unrelated commands.
                    cursor = db.execute('UPDATE adms_commands SET result=? WHERE id=? AND serial=? AND result IS NULL', (result, int(command_id), serial))
                    if cursor.rowcount:
                        matched.append(result)
            if matched:
                self.update(command=f'Device command result: {matched[-1]}. Check received punches; this does not confirm a complete download.')
            return 200, 'OK'
        if method == 'POST' and path == '/iclock/cdata':
            kind = query.get('table', [''])[0].upper()
            if kind == 'OPTIONS':
                return 200, 'OK'
            if kind not in ('ATTLOG', 'OPERLOG'):
                return 400, 'Unsupported table'
            stamp = query.get('Stamp', [''])[0]
            if len(stamp) > 100 or any(ord(c) < 32 for c in stamp):
                raise ValueError('Invalid checkpoint')
            punches = attendance(body) if kind == 'ATTLOG' else []
            employees, count = users(body) if kind == 'OPERLOG' else ([], len(punches))
            added = 0
            with closing(self.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                for pin, name in employees:
                    db.execute('INSERT INTO employees(badge,name) VALUES(?,?) ON CONFLICT(badge) DO NOTHING', (pin, name))
                    db.execute('UPDATE employees SET name=? WHERE badge=? AND name=badge AND badge IN (SELECT badge FROM adms_placeholders)', (name, pin))
                    db.execute('DELETE FROM adms_placeholders WHERE badge=?', (pin,))
                for pin, timestamp, state in punches:
                    cursor = db.execute('INSERT INTO employees(badge,name) VALUES(?,?) ON CONFLICT(badge) DO NOTHING', (pin, pin))
                    if cursor.rowcount:
                        db.execute('INSERT OR IGNORE INTO adms_placeholders VALUES(?)', (pin,))
                    added += db.execute('INSERT INTO punches(badge,stamp,kind,source) VALUES(?,?,?,?) ON CONFLICT(badge,stamp) DO NOTHING',
                                        (pin, timestamp, state, 'ADMS ' + serial)).rowcount
                if stamp:
                    db.execute('INSERT INTO adms_checkpoints VALUES(?,?,?) ON CONFLICT(serial,kind) DO UPDATE SET stamp=excluded.stamp', (serial, kind, stamp))
                db.execute('INSERT INTO audit(stamp,actor,action) VALUES(?,?,?)',
                           (datetime.now().isoformat(timespec='seconds'), 'ADMS ' + serial,
                            f'{kind}: {count} received, {added} new punches'))
            with self.lock:
                self.state['uploads'] += 1
                self.state['last_upload'] = datetime.now().isoformat(timespec='seconds')
                self.state['received_punches'] += len(punches)
                self.state['new_punches'] += added
                self.state['error'] = ''
            return 200, f'OK: {count}'
        return 404, 'Unsupported request'

    def request_history(self, begin, finish):
        begin, finish = date.fromisoformat(begin), date.fromisoformat(finish)
        if begin > finish or (finish - begin).days > 366:
            raise ValueError('Choose a date range of no more than 367 days, with start before end.')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM adms_commands WHERE serial=? AND result IS NULL', (self.config['serial'],)).fetchone():
                raise ValueError('A history request is pending. Wait for the device or cancel the pending request.')
            db.execute('INSERT INTO adms_commands(serial,command,created) VALUES(?,?,?)',
                       (self.config['serial'], f'DATA QUERY ATTLOG StartTime={begin} 00:00:00\tEndTime={finish} 23:59:59', datetime.now().isoformat()))
        self.update(command='History request queued; waiting for device.')

    def cancel_history(self):
        with closing(self.connect()) as db, db:
            db.execute("UPDATE adms_commands SET result='cancelled' WHERE serial=? AND result IS NULL", (self.config['serial'],))
        self.update(command='Pending request cancelled. Already sent requests may still upload records.')


def start_receiver(store, config, backup_dir):
    store.require('admin')
    receiver = Receiver(store.path, config)
    folder = Path(backup_dir)
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('before-adms-' + uuid.uuid4().hex + '.sqlite')
    with closing(sqlite3.connect(backup)) as target:
        store.db.backup(target)
    receiver.start()
    return receiver, backup
