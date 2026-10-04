import unittest,struct
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
from connectors import download
from device_session import DeviceSession
from pyzatt import misc

class ConnectorTests(unittest.TestCase):
    def test_mapping_and_cleanup(self):
        fake=MagicMock();fake.users={9:SimpleNamespace(user_id='001',user_name='Example')}
        fake.att_log=[SimpleNamespace(user_id='001',att_time=datetime(2020,1,1,8),ver_state=0)]
        with patch('device_session.DeviceSession',return_value=fake):
            users,punches=download({'ip':'127.0.0.1','port':4370,'udp':0})
        self.assertEqual(users,[{'badge':'001','name':'Example'}]);self.assertEqual(punches[0]['kind'],'0')
        fake.connect.assert_called_once_with('127.0.0.1',4370,timeout=20,comm_key=0);fake.close.assert_called_once()
    def test_failed_download_closes_and_preserves_error(self):
        fake=MagicMock();fake.read_att_log.side_effect=TimeoutError('original failure');fake.close.side_effect=OSError('cleanup')
        with patch('device_session.DeviceSession',return_value=fake):
            with self.assertRaisesRegex(TimeoutError,'original failure'):download({'ip':'127.0.0.1','port':4370,'udp':0})
        fake.close.assert_called_once()
    def test_unsupported_modes_fail_before_network(self):
        with patch('device_session.DeviceSession') as factory:
            with self.assertRaisesRegex(ValueError,'TCP only'):download({'ip':'127.0.0.1','port':4370,'udp':1})
            with self.assertRaisesRegex(ValueError,'communication key'):download({'ip':'127.0.0.1','port':4370,'udp':0},-1)
            factory.assert_not_called()
    def test_large_attendance_dataset(self):
        session=DeviceSession();record=bytearray(40);struct.pack_into('<H',record,0,9)
        record[2:5]=b'001';record[27:31]=misc.encode_time(datetime(2026,10,4,13,51,21))
        data=struct.pack('<I',40*2000)+record*2000
        with patch.object(session,'send_command'),patch.object(session,'recv_long_reply',return_value=data):session.read_att_log()
        self.assertEqual(len(session.att_log),2000);self.assertEqual(session.att_log[0].user_id,'001')
        self.assertEqual(session.att_log[0].att_time,datetime(2026,10,4,13,51,21))
    def test_fragmented_tcp_and_eof(self):
        from pyzatt.zkmodules import defs
        session=DeviceSession();packet=session.create_packet(defs.CMD_ACK_OK)
        chunks=[bytes([b]) for b in packet]
        session.soc_zk=MagicMock();session.soc_zk.recv.side_effect=chunks
        session.recv_reply();self.assertTrue(session.recvd_ack())
        session.soc_zk.recv.side_effect=[b'']
        with self.assertRaises(ConnectionError):session.recv_packet()

    def test_real_pyzatt_against_simulated_tcp_device(self):
        import socket,threading
        from pyzatt.zkmodules import defs
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(5)
        failures=[]
        def serve():
            try:
                peer,_=server.accept();peer.settimeout(5)
                with peer:
                    wire=DeviceSession();wire.soc_zk=peer
                    for expected in (defs.CMD_CONNECT,defs.CMD_DATA_WRRQ,defs.CMD_DATA_WRRQ,defs.CMD_EXIT):
                        wire.parse_ans(wire.recv_packet());self.assertEqual(wire.last_reply_code,expected)
                        payload=None;reply=defs.CMD_ACK_OK
                        if expected==defs.CMD_DATA_WRRQ:
                            if wire.last_payload_data[1]==9:
                                record=bytearray(72);struct.pack_into('<H',record,0,9)
                                record[11:18]=b'Example';record[48:51]=b'001'
                            else:
                                record=bytearray(40);struct.pack_into('<H',record,0,9)
                                record[2:5]=b'001';record[27:31]=misc.encode_time(datetime(2026,10,4,13,51,21))
                            payload=struct.pack('<I',len(record))+record;reply=defs.CMD_DATA
                        peer.sendall(wire.create_packet(reply,payload,session_id=123))
            except BaseException as e:failures.append(e)
            finally:server.close()
        port=server.getsockname()[1];thread=threading.Thread(target=serve,daemon=True);thread.start()
        users,punches=download({'ip':'127.0.0.1','port':port,'udp':0})
        thread.join(6)
        self.assertFalse(thread.is_alive());self.assertFalse(failures)
        self.assertEqual(users,[{'badge':'001','name':'Example'}]);self.assertEqual(punches[0]['stamp'],'2026-10-04 13:51:21')
        self.assertEqual(punches[0]['legacy_stamp'],'2027-10-04 13:51:21')

if __name__=='__main__':unittest.main()
