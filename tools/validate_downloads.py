"""Validate current downloadable bundles; no network, execution or account mutation."""
from pathlib import Path, PurePosixPath
import hashlib,io,json,re,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def inspect(data):
    z=zipfile.ZipFile(io.BytesIO(data))
    assert z.testzip() is None, 'ZIP integrity failure'
    assert len(z.namelist())==len(set(z.namelist())), 'Duplicate ZIP members'
    for n in z.namelist():
        p=PurePosixPath(n.replace('\\','/'))
        assert not p.is_absolute() and '..' not in p.parts, n
        assert '.git' not in p.parts and '__pycache__' not in p.parts and not n.endswith('.pyc'), n
        if n.endswith(('.md','.txt','.py','.json','.yaml','.yml','.sh','.ps1')):
            data=z.read(n).decode('utf-8-sig',errors='replace')
            assert 'Private personal context' not in data and 'never publish this version' not in data, (n,'private source in public package')
            assert not re.search(r'(?<![\w-])(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{35,}|AKIA[0-9A-Z]{16})',data),(n,'credential-like literal')
    return z

def main():
    manifest=json.loads((ROOT/'downloads/manifest.json').read_text(encoding='utf-8'))
    names=manifest['skills']
    for rel,digest in manifest['files'].items():
        p=ROOT/rel
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest, rel
        inspect(p.read_bytes())
    with inspect((ROOT/'downloads/ChatGPT.zip').read_bytes()) as g,inspect((ROOT/'downloads/Claude.zip').read_bytes()) as c:
        assert sorted(n[:-4] for n in c.namelist())==names, 'Claude skill list'
        gn=sorted({n.split('/')[2] for n in g.namelist() if '/skills/' in n})
        assert gn==names, 'GPT and Claude skill sets differ'
        plugin=[n for n in g.namelist() if n.endswith('/plugin.json') and n.count('/')==1]
        assert len(plugin)==1
        json.loads(g.read(plugin[0]))
        for name in names:
            with inspect(c.read(name+'.zip')) as inner:
                assert len(inner.namelist())<=200,(name,'Claude file limit')
                text=inner.read(name+'/SKILL.md').decode('utf-8-sig')
                fm=text.split('---',2)[1]
                assert re.search(r'^name:\s*["\']?'+re.escape(name)+r'["\']?\s*$',fm,re.M),name
                desc=re.search(r'^description:\s*(.+)$',fm,re.M)[1]
                if desc.startswith('"'):desc=json.loads(desc)
                assert 0<len(desc)<=200,(name,'Claude description')
                for rel in inner.namelist():
                    p=ROOT/'skills/claude'/name/PurePosixPath(rel).relative_to(name)
                    assert p.exists(),(name,rel,'missing Claude source')
                    source=p.read_bytes();payload=inner.read(rel)
                    # Preserve pre-existing copyright line endings in a source checkout.
                    if p.name.upper().startswith(('LICENSE','COPYING','NOTICE')):
                        assert source.replace(b'\r\n',b'\n')==payload.replace(b'\r\n',b'\n'),(name,rel,'license mismatch')
                    else:assert source==payload,(name,rel,'source/package mismatch')
            with inspect((ROOT/'packages/chatgpt'/f'{name}.zip').read_bytes()) as single:
                assert name+'/plugin.json' in single.namelist()
                assert name+'/skills/'+name+'/SKILL.md' in single.namelist()
    for p in (ROOT/'assets').glob('*.svg'):ET.fromstring(p.read_text(encoding='utf-8'))
    # Check repository-relative file links in the newly maintained documentation block.
    for filename in ['README.md','README.tr.md']:
        text=(ROOT/filename).read_text(encoding='utf-8')
        match=re.search(r'<!-- CURRENT-SKILL-PUBLICATION -->(.*?)<!-- END-CURRENT-SKILL-PUBLICATION -->',text,re.S)
        if not match:continue
        for rel in re.findall(r'\]\(([^)]+)\)',match[1]):
            if rel.startswith(('http:','https:','#')):continue
            assert (ROOT/rel.split('#')[0]).is_file(),(filename,rel,'broken relative link')
    print(f'PASS: {len(names)} skills, equal provider sets, source/package parity, ZIP paths, hashes, descriptions and documentation links')

if __name__=='__main__':main()
