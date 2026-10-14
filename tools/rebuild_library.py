#!/usr/bin/env python3
"""Rebuild a maintained collection locally. No network, install, commit or push."""
from pathlib import Path
from io import BytesIO
import argparse
import hashlib
import json
import re
import zipfile
import library_views as views
from library_site import site
from publication_docs import INSTALL, MAINTAINING, LEGACY, LICENSE_SCOPE
import build_host_variants as host
from compact_desktop_packages import plugin_files, gemini_web_payload, fit_claude_upload

def put(root,path,text):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def jput(root,path,value):put(root,path,json.dumps(value,ensure_ascii=False,indent=2))
def pack(mapping):
    out=BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(mapping.items()):
            p=Path(name)
            if p.is_absolute() or '..' in p.parts:raise ValueError(name)
            info=zipfile.ZipInfo(name.replace(chr(92),'/'),(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
    return out.getvalue()
def binary(root,path,data):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def source_map(folder):
    return {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*') if p.is_file() and not any(v in {'.git','__pycache__','.DS_Store'} for v in p.relative_to(folder).parts)}

def build(root):
    reg=json.loads((root/'library-registry.json').read_text('utf-8'));meta=json.loads((root/'collection.json').read_text('utf-8'))
    all_skills={s['id']:s for s in reg['skills']}
    selection=reg['collections'][meta['repository']]['skills']
    chosen=sorted(all_skills) if selection=='*' else sorted(selection)
    selected=[all_skills[n] for n in chosen]
    common=root/'skills/common';descriptions=json.loads((root/'host-descriptions.json').read_text('utf-8'))
    for skill in selected:descriptions.setdefault(skill['id'],skill['en']['purpose'][:190])
    for name in chosen:
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',name) or not (common/name/'SKILL.md').is_file():raise ValueError('Missing or invalid root '+name)
    title=meta['title']
    for lang in ('en','tr'):
        put(root,'README'+('.tr' if lang=='tr' else '')+'.md',views.readme(reg,selected,title,meta['summary_tr' if lang=='tr' else 'summary'],lang,meta['repository']))
        for s in selected:put(root,f'docs/skills/{s["id"]}.{lang}.md',views.skill_page(s,common,lang))
    for theme in ('dark','light'):
        put(root,f'assets/hero-{theme}.svg',views.hero(title,'Clear questions. Repeatable workflows. Reviewable results.',str(len(selected))+' MAINTAINED WORKFLOWS',theme))
    old=root/'docs/index.html';history=root/'docs/legacy-index.html'
    if old.exists() and not history.exists():history.write_bytes(old.read_bytes())
    html=site(reg,selected).replace('<title>Universal AI Skill Library', '<title>'+meta['title'])
    if not history.exists():html=html.replace('legacy-index.html','https://github.com/yigityildiz0/universal-ai-skill-library/blob/main/LEGACY.md')
    put(root,'docs/index.html',html)
    put(root,'docs/favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#101c29"/><path d="M17 17L32 34L47 17M32 34V49" fill="none" stroke="#8fe0cd" stroke-width="5" stroke-linecap="round"/></svg>')
    portable={};codex={};gpt_skills={};claude_files={};gemini_files={};download_rows=[];claude_counts={};coverage={}
    for name in chosen:
        mapping=source_map(common/name)
        portable.update({name+'/'+k:v for k,v in mapping.items()})
        binary(root,f'packages/portable/{name}.zip',pack({name+'/'+k:v for k,v in mapping.items()}))
        gpt=host.desired_files(common/name,'codex',descriptions)
        codex.update({name+'/'+k:v for k,v in gpt.items()})
        gpt_skills[name]=gpt
        one=plugin_files({name:gpt},{'version':reg['release']},name,provider='codex')
        binary(root,f'packages/chatgpt/{name}.zip',pack(one))
        cl=fit_claude_upload(name,host.desired_files(common/name,'claude',descriptions),reg['release'][:10].replace('.','-'));parts={name:cl};coverage[name]={'source_skill':name,'split':False,'parts':[name]};part_names=[]
        for upload,payload in parts.items():
            blob=pack({upload+'/'+k:v for k,v in payload.items()});filename=upload+'.zip'
            binary(root,'packages/claude/'+filename,blob);claude_files[filename]=blob;part_names.append(filename)
        claude_counts[name]=len(part_names)
        gem=pack({name+'/'+k:v for k,v in gemini_web_payload(name,gpt).items()});binary(root,f'packages/gemini/{name}.zip',gem);gemini_files[name+'.zip']=gem
        links=' · '.join(f'[{i+1}](packages/claude/{p})' for i,p in enumerate(part_names))
        download_rows.append(f'| [{name}](docs/skills/{name}.en.md) | [Source](packages/portable/{name}.zip) | [OpenAI plugin](packages/chatgpt/{name}.zip) | {links} | [Gemini app](packages/gemini/{name}.zip) |')
    binary(root,'downloads/portable-skills.zip',pack(portable));binary(root,'downloads/Gemini.zip',pack(gemini_files));binary(root,'downloads/Codex.zip',pack(codex));binary(root,'downloads/Claude.zip',pack(claude_files))
    plugin=plugin_files(gpt_skills,{'version':reg['release']},meta['repository'],provider='codex')
    jput(root,'claude-coverage.json',coverage)
    binary(root,'downloads/ChatGPT.zip',pack(plugin))
    put(root,'DOWNLOADS.md','# Downloads / İndirmeler\n\n[Portable sources](downloads/portable-skills.zip) · [Codex local folders](downloads/Codex.zip) · [OpenAI-compatible plugin bundle](downloads/ChatGPT.zip) · [Claude upload collection](downloads/Claude.zip) · [Gemini app uploads](downloads/Gemini.zip)\n\nGemini CLI, OpenCode and DeepSeek Harness use the portable sources. / Gemini CLI, OpenCode ve DeepSeek Harness taşınabilir kaynakları kullanır.\n\nA plugin bundle needs a compatible host. Uploading a ZIP to GPT Knowledge does not install tools or executable skills. Unpack the Claude collection and upload individual part ZIPs; the outer ZIP is not one skill. Local folders and cloud-account imports differ. / Plugin paketi uyumlu host gerektirir. GPT Knowledge yüklemesi araç kurmaz. Claude dış ZIP açılır; içindeki skill/parça ZIPleri ayrı yüklenir.\n\n| Skill | Portable | Compatible OpenAI host | Claude parts | Gemini app |\n|---|---|---|---|---|\n'+'\n'.join(download_rows)+'\n\nFor a partitioned skill, include its routing root and supporting parts together. Do not rename/delete support files. / Parçalı skill için yönlendirme kökü ve destek parçaları birlikte gerekir.\n')
    put(root,'docs/INSTALL.md',INSTALL)
    put(root,'INSTALL.md','# Installation\n\n[Current bilingual platform guide](docs/INSTALL.md) · [Downloads](DOWNLOADS.md).\n\nGüncel platform rehberi ve Türkçe bölüm aynı belgede bulunur. Eski paket bağlantıları kurulum başarısı kanıtı değildir.\n')
    put(root,'INSTALL.tr.md','# Kurulum\n\n[Güncel iki dilli rehber](docs/INSTALL.md) · [İndirmeler](DOWNLOADS.md).\n')
    put(root,'MAINTAINING.md',MAINTAINING);put(root,'LEGACY.md',LEGACY);put(root,'docs/LICENSE-SCOPE.md',LICENSE_SCOPE)
    links=['# Collections / Koleksiyonlar','', 'One canonical source; stable audience-specific views. / Tek kaynak; kalıcı alan görünümleri.','', '| Collection | Scope / Kapsam |','|---|---|']
    for name,item in reg['collections'].items():links.append(f'| [{item["title"]}](https://github.com/{reg["owner"]}/{name}) | {item["summary"]}<br>{item["summary_tr"]} |')
    links+=['','[Super Memory](https://github.com/yigityildiz0/super-memory) is included in the canonical library; its existing repository remains a focused view of the same source.']
    put(root,'COLLECTIONS.md','\n'.join(links))
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for directory in ('downloads','packages/portable','packages/chatgpt','packages/claude','packages/gemini') for p in (root/directory).glob('*.zip') if p.is_file() and ((p.parent.name=='downloads' and p.name in {'portable-skills.zip','Codex.zip','Claude.zip','ChatGPT.zip','Gemini.zip'}) or (p.parent.name=='claude' and p.name in claude_files) or (p.parent.name in {'portable','chatgpt','gemini'} and p.stem in chosen))}
    put(root,'downloads/SHA256SUMS-current.txt','\n'.join(f'{digest}  {path}' for path,digest in sorted(hashes.items())))
    current={'edition':reg['release'],'repository':meta['repository'],'canonical':reg['canonical_repository'],'skills':chosen,'claude_parts':claude_counts,'artifact_sha256':hashes,'validation_scope':'structure, hashes and archives; not live account activation or clinical/financial efficacy'}
    jput(root,'current-release.json',current)
    return current

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    result=build(a.root.resolve());print(json.dumps({'repository':result['repository'],'skills':len(result['skills']),'artifacts':len(result['artifact_sha256'])}))
if __name__=='__main__':main()
