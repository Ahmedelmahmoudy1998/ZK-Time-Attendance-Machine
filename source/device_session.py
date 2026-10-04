"""Bounded TCP transport for the pinned MIT pyzatt session.

Uses pyzatt's packet/dataset commands. Does not write SDKBuild,
disable terminals, clear logs, or read biometric templates.

Adds the communication key handshake, which pyzatt does not implement. When a
device has a comm key set it answers CMD_CONNECT with CMD_ACK_UNAUTH, and the
client must reply with CMD_AUTH carrying the key scrambled with the session id.
The transform below is written here from the published ZK protocol behaviour so
the app keeps its own licence; no GPL source is reused.
"""
import codecs, socket, struct
from pyzatt.pyzatt import ZKSS
from pyzatt.zkmodules import defs as DEFS
from device_time import decode_device_time

# pyzatt does not expose these two in every build, so fall back to the wire values.
CMD_AUTH = getattr(DEFS, 'CMD_AUTH', 1102)
CMD_ACK_UNAUTH = getattr(DEFS, 'CMD_ACK_UNAUTH', 1999)

MASK32 = 0xFFFFFFFF


def scramble_comm_key(key, session_id, ticks=50):
    """Return the 4 byte payload for CMD_AUTH.

    key is the device's communication key as an integer, session_id is the value
    the device returned on CMD_CONNECT. The device rejects the session when the
    result does not match, so an incorrect key looks exactly like no key at all.
    """
    key = int(key) & MASK32
    session_id = int(session_id) & MASK32
    ticks = int(ticks) & 0xFF

    # Reverse the 32 bits of the key, then fold the session id in.
    reversed_bits = 0
    for bit in range(32):
        reversed_bits = ((reversed_bits << 1) | ((key >> bit) & 1)) & MASK32
    value = (reversed_bits + session_id) & MASK32

    a, b, c, d = struct.unpack('<4B', struct.pack('<I', value))
    a, b, c, d = a ^ ord('Z'), b ^ ord('K'), c ^ ord('S'), d ^ ord('O')

    # Swap the two 16 bit halves.
    low, high = struct.unpack('<2H', struct.pack('<4B', a, b, c, d))
    a, b, c, d = struct.unpack('<4B', struct.pack('<2H', high, low))

    return bytearray(struct.pack('<4B', a ^ ticks, b ^ ticks, ticks, d ^ ticks))


class DeviceSession(ZKSS):
    def connect(self, ip, port, timeout=20, comm_key=0):
        self.soc_zk = socket.create_connection((ip, port), timeout=timeout)
        self.send_command(DEFS.CMD_CONNECT)
        self.recv_reply()
        self.session_id = self.last_session_code
        self.connected_flg = self.recvd_ack()

        if not self.connected_flg and self.last_reply_code == CMD_ACK_UNAUTH:
            # Some terminals require CMD_AUTH even when their configured key is 0.
            self.send_command(CMD_AUTH, scramble_comm_key(comm_key, self.session_id))
            self.recv_reply()
            self.connected_flg = self.recvd_ack()
            if not self.connected_flg:
                raise ConnectionError(
                    'The device rejected the communication key. Check the COMM Key '
                    'on the device under Comm. > Security and enter the same number.')

        if not self.connected_flg:
            raise ConnectionError(
                'Device refused the connection (reply code '
                f'{getattr(self, "last_reply_code", "unknown")}). Check that the '
                'device is reachable on this port and not already in use by ZKTime.')

    def send_packet(self, packet): self.soc_zk.sendall(packet)

    def _read_exact(self, count):
        result = bytearray()
        while len(result) < count:
            part = self.soc_zk.recv(count - len(result))
            if not part: raise ConnectionError('Device closed the connection during download.')
            result.extend(part)
        return result

    def recv_packet(self, buff_size=4096):
        header = self._read_exact(8)
        size = struct.unpack_from('<I', header, 4)[0]
        if header[:4] != DEFS.START_TAG or not 8 <= size <= 32 * 1024 * 1024:
            raise ValueError('Invalid pyzatt TCP packet header or size.')
        return header + self._read_exact(size)

    def parse_ans(self, packet):
        super().parse_ans(packet)
        if self.last_reply_code == -1: raise ValueError('Invalid device reply/checksum.')

    def recv_reply(self, buff_size=1024):
        self.parse_ans(self.recv_packet(buff_size)); self.reply_number += 1

    def recv_long_reply(self, buff_size=4096):
        data = super().recv_long_reply(buff_size)
        if len(data) < 4: raise ValueError('Device returned no valid record dataset.')
        if struct.unpack_from('<I', data)[0] != len(data) - 4:
            raise ValueError('Device dataset length mismatch; download was not imported.')
        self.last_payload_data = data
        return data

    def read_all_user_id(self):
        self.send_command(DEFS.CMD_DATA_WRRQ, bytearray.fromhex('0109000500000000000000'))
        data = self.recv_long_reply()
        if (len(data) - 4) % 72:
            raise ValueError('Unsupported user record format; download was not imported.')
        users = []
        for pos in range(4, len(data), 72):
            serial = struct.unpack_from('<H', data, pos)[0]
            # Identity remains strict. Never repair or guess a badge number.
            badge = data[pos + 48:pos + 57].split(b'\x00', 1)[0].decode('ascii')
            if not badge:
                raise ValueError('Device returned an empty user badge; download was not imported.')
            raw_name = bytes(data[pos + 11:pos + 35]).split(b'\x00', 1)[0]
            # U160-C can leave garbage after NUL or cut a UTF-8 character at
            # the 24-byte name boundary. Ignore padding and retain the complete
            # prefix; replace any malformed interior display-name bytes only.
            name = codecs.getincrementaldecoder('utf-8')(errors='replace').decode(raw_name, final=False)
            users.append((serial, badge, name))
        self.users = {}
        for serial, badge, name in users:
            self.add_user(serial)
            # Download needs identity/name only, not device passwords or cards.
            self.users[serial].set_user_info(user_sn=serial, user_id=badge, name=name)

    def read_att_log(self):
        # pyzatt 2.0 reads a 16-bit size and loses the assembled long dataset.
        # Parse its documented 40-byte records using the complete 32-bit size.
        self.send_command(DEFS.CMD_DATA_WRRQ, bytearray.fromhex('010d000000000000000000'))
        data = self.recv_long_reply()
        if (len(data) - 4) % 40: raise ValueError('Unsupported attendance record format.')
        self.att_log = []
        for pos in range(4, len(data), 40):
            self.append_att_entry(struct.unpack_from('<H', data, pos)[0],
                data[pos + 2:pos + 11].decode('ascii').rstrip('\x00'), data[pos + 26],
                decode_device_time(data[pos + 27:pos + 31]), data[pos + 31])

    def close(self):
        sock = getattr(self, 'soc_zk', None)
        try:
            if self.connected_flg: self.disconnect()
        finally:
            if sock: sock.close()
            self.connected_flg = False
