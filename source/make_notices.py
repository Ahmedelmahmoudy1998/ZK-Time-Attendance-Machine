"""Regenerate notices from the build environment; never append old licenses."""
from pathlib import Path
import sys,importlib.metadata as metadata,shutil

def main():
    root=Path(__file__).resolve().parent.parent
    sections=['OASIS ATTEND — THIRD-PARTY NOTICES\nOasis Digital Solutions\n\nThe ODS EULA applies to the application. Components below retain their own licenses.\n']
    sections.append('=== pyzatt 2.0.0 (MIT) ===\nUpstream commit dc30714ed641388f53537319f6c0e7bd8dba544a\nhttps://github.com/adrobinoga/pyzatt\n'+(root/'third-party-sources/pyzatt-LICENSE.txt').read_text('utf-8'))
    packages=['reportlab','openpyxl','xlwt','arabic-reshaper','python-bidi','Pillow','charset-normalizer','et-xmlfile','prettytable','wcwidth','colorama','lxml','pyinstaller']
    for name in packages:
        dist=metadata.distribution(name)
        files=[f for f in dist.files or [] if Path(str(f)).name.lower().startswith(('licen','copying','copyright','authors','notice')) and ('.dist-info/' in str(f).replace('\\','/') or name=='xlwt')]
        sections.append(f'\n=== {name} {dist.version} ===\n')
        if not files:
            fallback=root/'third-party-sources'/(name+'-LICENSE.txt')
            if not fallback.is_file():raise RuntimeError('No published license text found for '+name)
            sections.append(fallback.read_text('utf-8'))
        for f in files:
            p=Path(dist.locate_file(f))
            if p.is_file():sections.append(str(f)+'\n'+p.read_text('utf-8',errors='replace'))
    python=Path(sys.base_prefix)
    sections.append('\n=== Python '+sys.version.split()[0]+' ===\n'+(python/'LICENSE.txt').read_text('utf-8'))
    for p in python.glob('tcl/**/license.terms'):sections.append('\n=== '+str(p.relative_to(python))+' ===\n'+p.read_text('utf-8',errors='replace'))
    sections.append('\nSQLite is in the public domain: https://sqlite.org/copyright.html\n')
    sections.append('\nBuild tool: PyInstaller license above includes its bootloader exception. No pyzk component is included.\n')
    (root/'THIRD-PARTY-NOTICES.txt').write_text('\n'.join(sections),encoding='utf-8')
    portable=root/'portable/Oasis Attend'
    if portable.is_dir():
        for name in ('LICENSE.txt','THIRD-PARTY-NOTICES.txt','README.md','REPLACING-BIDI.md','VALIDATION.md','PASSWORD-UPDATE.md','COMPANY-SETTINGS.md','BIOTIME.md','ADMS.md'):
            shutil.copy2(root/name,portable/name)
        shutil.copytree(root/'third-party-sources',portable/'third-party-sources',dirs_exist_ok=True)

if __name__=='__main__':main()
