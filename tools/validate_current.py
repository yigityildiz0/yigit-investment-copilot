#!/usr/bin/env python3
"""Check the declared current edition. Historical sources are not declared tested."""
from pathlib import Path,PurePosixPath
from io import BytesIO
import ast,hashlib,json,re,zipfile
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
def main():
    reg=json.loads((ROOT/'library-registry.json').read_text('utf-8'));cur=json.loads((ROOT/'current-release.json').read_text('utf-8'))
    names=cur['skills'];assert len(names)==len(set(names));assert 'gemini-deep-research' not in names
    assert set(names)<={s['id'] for s in reg['skills']}
    checked=0
    for rel,digest in cur['artifact_sha256'].items():
        p=ROOT/rel;data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest,rel
        with zipfile.ZipFile(BytesIO(data)) as z:
            assert z.testzip() is None,rel
            for n in z.namelist():
                path=PurePosixPath(n);assert not path.is_absolute() and '..' not in path.parts,(rel,n)
                assert 'gemini-deep-research' not in path.parts,(rel,n)
            if rel.startswith('packages/claude/'):
                assert len(z.namelist())<=200,rel
                roots={n.split('/')[0] for n in z.namelist()};assert len(roots)==1,rel
                assert next(iter(roots))+'/SKILL.md' in z.namelist(),rel
        checked+=1
    docs=[ROOT/'README.md',ROOT/'README.tr.md',ROOT/'DOWNLOADS.md',ROOT/'COLLECTIONS.md',ROOT/'MAINTAINING.md',ROOT/'LEGACY.md',ROOT/'docs/INSTALL.md',ROOT/'docs/LICENSE-SCOPE.md']
    for name in names:
        assert (ROOT/'skills/common'/name/'SKILL.md').is_file(),name
        for lang in ('en','tr'):
            page=ROOT/f'docs/skills/{name}.{lang}.md';assert page.is_file();docs.append(page)
    link_count=0
    for p in docs:
        text=p.read_text('utf-8')
        for raw in re.findall(r'\]\(([^\n)]+)\)',text):
            url=raw.strip('<> ').split(' "')[0]
            if re.match(r'^[a-z]+:',url) or url.startswith('#'):continue
            target=(p.parent/url.split('#')[0]).resolve();assert target.is_file() or target.is_dir(),(p.relative_to(ROOT),url)
            link_count+=1
    for p in (ROOT/'assets').glob('hero-*.svg'):ElementTree.fromstring(p.read_bytes())
    for name in names:
        for p in (ROOT/'skills/common'/name).rglob('*.py'):ast.parse(p.read_text('utf-8-sig'),filename=str(p))
    print(json.dumps({'ok':True,'skills':len(names),'artifacts':checked,'local_document_links':link_count,'scope':'current edition only; not runtime/account/efficacy certification'}))
if __name__=='__main__':main()
