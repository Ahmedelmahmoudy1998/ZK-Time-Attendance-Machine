"""Read attendance using BioTime's documented JWT/transactions API.

Only authentication POST and attendance GET are supported. No terminal commands,
database access, employee passwords or biometric endpoints are used.
"""
import ipaddress
import json
import socket
import time
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class BioTimeError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials or tokens to a redirected login/server.
        return None


def server_url(value):
    value = value.strip().rstrip('/')
    try:
        p = urlsplit(value)
        port = p.port
        if (p.scheme not in ('http', 'https') or not p.hostname or
                p.username is not None or p.password is not None or
                p.query or p.fragment or p.path not in ('', '/')):
            raise ValueError()
        if port is not None and not 1 <= port <= 65535:
            raise ValueError()
        local = p.hostname.lower() == 'localhost'
        try:
            local = local or ipaddress.ip_address(p.hostname).is_loopback
        except ValueError:
            pass
        if p.scheme == 'http' and not local:
            raise BioTimeError('Use HTTPS for a remote BioTime server, or http://127.0.0.1 for BioTime on this PC.')
        return urlunsplit((p.scheme, p.netloc.lower(), '', '', ''))
    except BioTimeError:
        raise
    except ValueError:
        raise BioTimeError('Enter the BioTime server URL, for example http://127.0.0.1.') from None


class BioTimeClient:
    def __init__(self, url):
        self.url = server_url(url)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.token = None

    def _request(self, url, body=None):
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'JWT ' + self.token
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(url, data=json.dumps(body).encode('utf-8') if body is not None else None,
                      headers=headers, method='POST' if body is not None else 'GET')
        try:
            with self.opener.open(req, timeout=20) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise BioTimeError('BioTime returned too much data. Choose a shorter date range.')
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError()
                return result
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if code in (400, 401) and body is not None:
                message = 'BioTime login failed. Check your BioTime username and password.'
            elif code in (401, 403):
                message = 'BioTime denied API access. Check account permissions and API availability in BioTime.'
            elif code in (301, 302, 303, 307, 308):
                message = 'BioTime redirected the request. Enter its direct server URL.'
            else:
                message = f'BioTime API returned HTTP {code}. Check API availability and server settings.'
            raise BioTimeError(message) from None
        except (URLError, socket.timeout, OSError):
            raise BioTimeError('Cannot reach BioTime securely. Check the server address, service and HTTPS certificate.') from None
        except (ValueError, UnicodeError) as exc:
            if isinstance(exc, BioTimeError):
                raise
            raise BioTimeError('BioTime returned an unexpected response. Check its API availability.') from None

    def download(self, username, password, serial, begin, finish):
        serial = serial.strip()
        if not username.strip() or not password:
            raise BioTimeError('Enter your BioTime username and password.')
        if not serial or len(serial) > 100 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in serial):
            raise BioTimeError('Enter the device serial number shown in BioTime.')
        try:
            start, end = date.fromisoformat(begin), date.fromisoformat(finish)
        except (TypeError, ValueError):
            raise BioTimeError('Choose valid start and end dates.') from None
        if start > end or (end - start).days > 366:
            raise BioTimeError('Choose a date range of no more than 367 days, with start before end.')
        try:
            auth = self._request(self.url + '/jwt-api-token-auth/',
                                 {'username': username.strip(), 'password': password})
            token = auth.get('token')
            if not isinstance(token, str) or not token or any(c.isspace() for c in token):
                raise BioTimeError('BioTime did not return an API token. Check API availability for your account.')
            self.token = token
            endpoint = self.url + '/iclock/api/transactions/'
            params = {'terminal_sn': serial, 'start_time': begin + ' 00:00:00',
                      'end_time': finish + ' 23:59:59', 'page_size': 500, 'page': 1}
            current = endpoint + '?' + urlencode(params)
            seen_pages, seen_ids = set(), set()
            employees, punches = {}, {}
            expected = None
            deadline = time.monotonic() + 300
            while current:
                if current in seen_pages or len(seen_pages) >= 1000 or time.monotonic() > deadline:
                    raise BioTimeError('BioTime download did not finish. Choose a shorter date range and retry.')
                seen_pages.add(current)
                result = self._request(current)
                rows, count = result.get('data'), result.get('count')
                if (result.get('code', 0) not in (0, '0') or not isinstance(rows, list) or
                        type(count) is not int or count < 0 or count > 500000):
                    raise BioTimeError('BioTime returned an invalid attendance page. Nothing was imported.')
                if expected is None:
                    expected = count
                elif expected != count:
                    raise BioTimeError('BioTime attendance changed during download. Retry to obtain a complete import.')
                for row in rows:
                    if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] in seen_ids:
                        raise BioTimeError('BioTime returned duplicate or invalid page records. Nothing was imported.')
                    seen_ids.add(row['id'])
                    badge = row.get('emp_code')
                    try:
                        stamp = datetime.fromisoformat(row['punch_time'])
                    except (KeyError, TypeError, ValueError):
                        raise BioTimeError('BioTime returned an invalid punch date. Nothing was imported.') from None
                    if (not isinstance(badge, str) or not badge.strip() or badge != badge.strip() or
                            len(badge) > 100 or stamp.tzinfo is not None or
                            row.get('terminal_sn') != serial or not start <= stamp.date() <= end):
                        raise BioTimeError('BioTime returned a record outside the selected device/date range or an invalid badge/time. Nothing was imported.')
                    # BioTime documents device-local wall time, without a zone.
                    # Reject unexpected zoned values instead of silently shifting reports.
                    stamp = stamp.replace(microsecond=0).isoformat(sep=' ')
                    name = ' '.join(str(row.get(k) or '').strip() for k in ('first_name', 'last_name')).strip()
                    department = row.get('department') or ''
                    if not isinstance(department, str):
                        raise BioTimeError('BioTime returned an invalid department. Nothing was imported.')
                    employees[badge] = {'badge': badge, 'name': name or badge, 'department': department}
                    punches.setdefault((badge, stamp), {'badge': badge, 'stamp': stamp,
                                                        'kind': str(row.get('punch_state') or '0')})
                next_page = result.get('next')
                if next_page is not None:
                    if not isinstance(next_page, str) or not next_page or not rows:
                        raise BioTimeError('BioTime returned invalid pagination. Nothing was imported.')
                    candidate = urljoin(current, next_page)
                    p, base = urlsplit(candidate), urlsplit(endpoint)
                    if (p.scheme, p.netloc, p.path) != (base.scheme, base.netloc, base.path) or p.fragment:
                        raise BioTimeError('BioTime returned an unsafe pagination address. Nothing was imported.')
                    current = candidate
                else:
                    current = None
            if len(seen_ids) != expected:
                raise BioTimeError('BioTime returned an incomplete download. Nothing was imported.')
            return list(employees.values()), list(punches.values())
        finally:
            self.token = None
