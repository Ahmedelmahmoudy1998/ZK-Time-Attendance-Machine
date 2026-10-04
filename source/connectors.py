import json, subprocess, tempfile, shutil, os
from pathlib import Path
from contextlib import contextmanager
import uuid

@contextmanager
def snapshot_folder():
    folder=Path(tempfile.gettempdir())/('zkdesk-import-'+uuid.uuid4().hex)
    folder.mkdir()
    try: yield folder
    finally:
        for p in folder.iterdir(): p.unlink()
        folder.rmdir()

def read_mdb(path):
    # ACE may create a lock file even for read access. Open a private snapshot.
    with snapshot_folder() as folder:
        snap=Path(folder)/'snapshot.mdb'; shutil.copy2(path,snap)
        script=r'''
$ErrorActionPreference='Stop'
$c=New-Object -ComObject ADODB.Connection
try {
 $c.Open('Provider=Microsoft.ACE.OLEDB.12.0;Data Source='+$env:ZK_MDB_SNAPSHOT+';Mode=Read;')
 function Read-Rows($sql) {
  $r=$c.Execute($sql)
  $rows=@()
  while(-not $r.EOF) {
   $o=[ordered]@{}
   foreach($f in $r.Fields) {
    $v=$f.Value
    if($v -is [DBNull]) {$v=''}
    if($v -is [datetime]) {$v=$v.ToString('yyyy-MM-dd HH:mm:ss')}
    $o[$f.Name]=$v
   }
   $rows+= [pscustomobject]$o
   $r.MoveNext()
  }
  $r.Close()
  return $rows
 }
 $e=@(Read-Rows 'SELECT u.Badgenumber AS badge,u.Name AS name,d.DEPTNAME AS department FROM USERINFO u LEFT JOIN DEPARTMENTS d ON u.DEFAULTDEPTID=d.DEPTID')
 $p=@(Read-Rows 'SELECT u.Badgenumber AS badge,c.CHECKTIME AS stamp,c.CHECKTYPE AS kind FROM CHECKINOUT c INNER JOIN USERINFO u ON c.USERID=u.USERID')
 $d=@(Read-Rows 'SELECT MachineAlias AS name,IP AS ip,Port AS port FROM Machines')
 $s=@(Read-Rows 'SELECT schName AS [name],StartTime AS [start],EndTime AS [end],LateMinutes AS grace FROM SchClass')
 @{employees=$e;punches=$p;devices=$d;shifts=$s}|ConvertTo-Json -Depth 5 -Compress|Set-Content -LiteralPath $env:ZK_MDB_JSON -Encoding UTF8
} finally {if($c.State -eq 1){$c.Close()}}
'''
        output=Path(folder)/'data.json'
        env=os.environ.copy(); env.update(ZK_MDB_SNAPSHOT=str(snap),ZK_MDB_JSON=str(output))
        executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        result=subprocess.run([str(executable),'-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=180)
        if result.returncode:
            raise RuntimeError('MDB import failed. Install the matching 64-bit Microsoft Access Database Engine, or close ZKTime and retry.\n'+result.stderr[-1800:])
        return json.loads(output.read_text(encoding='utf-8-sig'))

def download(device,password=0):
    from device_session import DeviceSession
    from device_time import previous_decoded_time
    from pyzatt.misc import encode_time
    import ipaddress
    if int(device.get('udp',0)):
        raise ValueError('The selected pyzatt connector supports TCP only. UDP download is not available.')
    key=int(password)
    if not 0<=key<=0xFFFFFFFF:
        raise ValueError('The communication key must be a number between 0 and 4294967295.')
    ip=ipaddress.IPv4Address(device['ip']);port=int(device['port'])
    if not 1<=port<=65535:raise ValueError('Invalid device port.')
    conn=DeviceSession()
    try:
        conn.connect(str(ip),port,timeout=20,comm_key=key)
        conn.read_all_user_id();conn.read_att_log()
        result=([{'badge':str(u.user_id),'name':u.user_name} for u in conn.users.values()],
                [{'badge':str(p.user_id),'stamp':p.att_time.isoformat(sep=' '),'kind':str(p.ver_state),
                  'legacy_stamp':old.isoformat(sep=' ') if (old:=previous_decoded_time(encode_time(p.att_time))) else None}
                 for p in conn.att_log])
    except BaseException:
        try:conn.close()
        except Exception:pass  # Preserve the original download/authentication failure.
        raise
    else:
        conn.close()
        return result
