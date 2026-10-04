import unittest,struct
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
from connectors import download
from device_session import DeviceSession
from pyzatt import misc

class ConnectorTests(unittest.TestCase):
    def test_reply_6001_is_rejected_and_preserved_for_ui(self):
        from device_session import DirectConnectionRejected
        session=DeviceSession()
        def reply():session.last_reply_code=6001;session.last_session_code=123
        with patch('device_session.socket.create_connection'),patch.object(session,'send_command') as send,patch.object(session,'recv_reply',side_effect=reply):
            with self.assertRaises(DirectConnectionRejected) as failure:
                session.connect('127.0.0.1',4370)
            self.assertEqual(failure.exception.reply_code,6001)
            self.assertFalse(session.connected_flg)
            self.assertEqual(send.call_count,1)

    def test_reply_6001_offers_biotime_without_claiming_success(self):
        from app import App
        from device_session import DirectConnectionRejected
        app=SimpleNamespace(tr=lambda value:value)
        for accept in (False,True):
            with patch('app.messagebox.askyesno',return_value=accept),patch('app.open_biotime') as open_form,patch('app.messagebox.showerror') as error:
                App.operation_error(app,DirectConnectionRejected(6001))
                self.assertEqual(open_form.call_count,int(accept))
                error.assert_not_called()
        with patch('app.messagebox.askyesno') as prompt,patch('app.open_biotime') as open_form,patch('app.messagebox.showerror') as error:
            App.operation_error(app,ConnectionError('A different error'))
            error.assert_called_once();prompt.assert_not_called();open_form.assert_not_called()

    def test_u160_names_do_not_interrupt_download(self):
        cases=[('محمد'.encode('utf-8')+b'\0\xff', 'محمد'),
               (b'A'+('م'*12).encode('utf-8')[:23], 'A'+'م'*11),
               ('علي'.encode('utf-8'), 'علي'),
               (b'Bad\xffName', 'Bad\ufffdName'), (b'', '')]
        records=[]
        for serial,(raw,expected) in enumerate(cases,1):
            record=bytearray(72);struct.pack_into('<H',record,0,serial)
            record[11:11+len(raw)]=raw;record[48:51]=f'{serial:03}'.encode('ascii')
            records.append(record)
        session=DeviceSession();data=struct.pack('<I',72*len(records))+b''.join(records)
        with patch.object(session,'send_command'),patch.object(session,'recv_long_reply',return_value=data):
            session.read_all_user_id()
        self.assertEqual([u.user_name for u in session.users.values()],[x[1] for x in cases])
        self.assertEqual([u.user_id for u in session.users.values()],['001','002','003','004','005'])

    def test_user_identity_and_record_lengths_remain_strict(self):
        for payload in (bytearray(71),bytearray(72),bytearray(72)):
            if len(payload)==72:payload[48]=255
            session=DeviceSession();data=struct.pack('<I',len(payload))+payload
            with patch.object(session,'send_command'),patch.object(session,'recv_long_reply',return_value=data):
                with self.assertRaises(ValueError):session.read_all_user_id()
        session=DeviceSession();data=struct.pack('<I',72)+bytearray(72)
        with patch.object(session,'send_command'),patch.object(session,'recv_long_reply',return_value=data):
            with self.assertRaisesRegex(ValueError,'empty user badge'):session.read_all_user_id()

    def test_saved_key_is_used_and_can_be_overridden_with_zero(self):
        for override,expected in ((None,123),(0,0)):
            fake=MagicMock();fake.users={};fake.att_log=[]
            with patch('device_session.DeviceSession',return_value=fake):
                download({'ip':'127.0.0.1','port':4370,'udp':0,'comm_key':123},override)
            fake.connect.assert_called_once_with('127.0.0.1',4370,timeout=20,comm_key=expected)

    def test_zero_key_authentication_challenge(self):
        from device_session import CMD_AUTH,CMD_ACK_UNAUTH,scramble_comm_key
        from pyzatt.zkmodules import defs
        session=DeviceSession()
        replies=iter((CMD_ACK_UNAUTH,defs.CMD_ACK_OK))
        def reply():session.last_reply_code=next(replies);session.last_session_code=123
        with patch('device_session.socket.create_connection'),patch.object(session,'send_command') as send,patch.object(session,'recv_reply',side_effect=reply):
            session.connect('127.0.0.1',4370,comm_key=0)
            self.assertTrue(session.connected_flg)
            self.assertEqual(send.call_args_list[1].args,(CMD_AUTH,scramble_comm_key(0,123)))

    def test_rejected_zero_key_still_fails(self):
        from device_session import CMD_ACK_UNAUTH
        session=DeviceSession()
        def reply():session.last_reply_code=CMD_ACK_UNAUTH;session.last_session_code=123
        with patch('device_session.socket.create_connection'),patch.object(session,'send_command'),patch.object(session,'recv_reply',side_effect=reply):
            with self.assertRaisesRegex(ConnectionError,'rejected'):session.connect('127.0.0.1',4370,comm_key=0)

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
