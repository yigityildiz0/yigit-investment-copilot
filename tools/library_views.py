"""Pure bilingual documentation and SVG rendering; standard library only."""
from html import escape
from pathlib import Path
import re

CATEGORY_TR={"Everyday workflows":"Günlük işler","Learn & write":"Öğrenme ve yazı","Build software":"Yazılım geliştirme","Research & analyze":"Araştırma ve analiz","Design & create":"Tasarım ve üretim","Health & rehabilitation":"Sağlık ve rehabilitasyon","Finance & decisions":"Finans ve karar"}
ORDER=list(CATEGORY_TR)
BASE="https://github.com/yigityildiz0/universal-ai-skill-library"

def hero(title, subtitle, count, theme="dark"):
    bg,fg,muted,panel,accent=("#101C29","#EFF8F7","#A6BAC6","#1C3041","#8FE0CD") if theme=="dark" else ("#F2F6F4","#152B39","#526977","#E2EDEA","#14675B")
    words=title.split(); lines=[title]
    if len(title)>22:
        k=len(words)//2; lines=[' '.join(words[:k]),' '.join(words[k:])]
    tspans=''.join(f'<tspan x="64" dy="{0 if i==0 else 65}">{escape(t)}</tspan>' for i,t in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="420" viewBox="0 0 1280 420" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}. Discover, choose, apply and verify.</desc>
<rect width="1280" height="420" rx="24" fill="{bg}"/><path d="M770 0V420M0 342H1280" stroke="{muted}" opacity=".15"/>
<g fill="none" stroke="{accent}" opacity=".13"><circle cx="1054" cy="168" r="127"/><circle cx="1054" cy="168" r="92"/><path d="M865 168H1230M1054 20V315"/></g>
<text x="64" y="63" font-family="Arial,sans-serif" font-size="17" letter-spacing="4" fill="{accent}">YIGIT YILDIZ / OPEN WORKFLOWS</text>
<text x="64" y="147" font-family="Arial,sans-serif" font-size="58" font-weight="700" letter-spacing="-2" fill="{fg}">{tspans}</text>
<text x="66" y="285" font-family="Arial,sans-serif" font-size="20" fill="{muted}">{escape(subtitle)}</text>
<rect x="828" y="73" width="330" height="56" rx="12" fill="{panel}"/><rect x="878" y="142" width="330" height="56" rx="12" fill="{panel}"/><rect x="828" y="211" width="330" height="56" rx="12" fill="{panel}"/>
<g font-family="Arial,sans-serif" font-size="19" fill="{fg}"><text x="852" y="108">01   Clear questions</text><text x="902" y="177">02   Repeatable workflows</text><text x="852" y="246">03   Reviewable results</text></g><circle cx="1180" cy="94" r="7" fill="{accent}"/>
<g font-family="Arial,sans-serif" font-size="16" fill="{muted}"><text x="64" y="385">{escape(str(count))}   /   ENGLISH + TURKCE</text><text x="820" y="385">SOURCE FIRST. TOOLS SECOND.</text></g></svg>'''

def picture(title):
    return f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">\n  <img src="assets/hero-light.svg" width="1280" alt="{escape(title)} — clear questions, repeatable workflows, reviewable results">\n</picture>\n'

def modules(folder):
    result=[]
    for p in sorted(folder.glob('modules/*/MODULE.md')):
        text=p.read_text('utf-8-sig')
        m=re.search(r'(?:Original trigger scope:|> Scope:)([^\n]+)',text)
        desc=m.group(1).strip()[:180] if m else p.parent.name.replace('-',' ')
        result.append((p.parent.name,desc,p.relative_to(folder).as_posix()))
    return result

def skill_page(s, source, lang):
    n=s['id']; tr=lang=='tr'; d=s[lang]; mods=modules(source/n)
    body=(source/n/'SKILL.md').read_text('utf-8-sig')
    fm=re.search(r'^description:\s*(.+)$',body,re.M)
    trigger=fm.group(1).strip('"') if fm else n
    # docs/skills/name.md -> repository root is ../..
    suffix='.tr' if tr else ''
    links=f'[English]({n}.en.md) · [Türkçe]({n}.tr.md) · [Library](../../README{suffix}.md)'
    out=f'# {n}\n\n{links}\n\n**{d["purpose"]}**\n\n'
    out+=('## Örnek istek\n\n' if tr else '## Try it\n\n')+f'> {d["prompt"]}\n\n'
    out+=('## Tetikleme ve yönlendirme\n\nİstek, hostun skill açıklamasıyla eşleştirilir. Host destekliyorsa kanonik adla açık seçim de yapılabilir. Sohbete /ad yazmak tek başına kayıtlı bir komut yaratmaz.\n\n' if tr else '## Trigger and routing\n\nThe host matches the request against the skill description. Explicit selection by canonical name is available where supported. Typing /name in chat does not register a command.\n\n')
    if n=='caveman': out+=('Caveman açık etkinleştirme ister; Ultra, Ultracave modülünü yükler. Durum sorgusu etkinleştirme değildir.\n\n' if tr else 'Caveman requires explicit activation; Ultra loads the Ultracave module. A status query is not activation.\n\n')
    out+=f'<details>\n<summary>{"Kaynak açıklamasının tam metni" if tr else "Exact source description"}</summary>\n\n{trigger}\n\n</details>\n\n'
    out+=('## Çalışma mantığı\n\n' if tr else '## How it works\n\n')+d['flow']+'\n\n'
    out+=('Kök giriş dosyası görevi karşılar; yalnız gereken modül ve referanslar yüklenir. Betik içermesi çalıştırıldığı anlamına gelmez. Mevcut araç, veri ve kapsam doğrulandıktan sonra görev yürütülür.\n\n' if tr else 'The root entry point owns routing; only relevant modules and references are loaded. A bundled script is not an executed result. Work uses actual host tools, available input and the task scope.\n\n')
    out+=('## Girdi, çıktı ve doğrulama\n\n- Girdi: örnek istekteki hedef, ilgili dosya/URL/veri ve sonucu değiştiren kısıtlar.\n- Çıktı: isteğe uygun yanıt, plan, taslak veya yetkili dosya değişikliği; dayanak ve belirsizlik açık.\n- Doğrulama: yapılan kontrol ile önerilen kontrol ayrı belirtilir; erişilmeyen kaynak veya çalıştırılmayan araç kullanılmış sayılmaz.\n\n' if tr else '## Inputs, outputs and verification\n\n- Input: the example goal, relevant files/URLs/data, and constraints that change the result.\n- Output: a task-appropriate answer, plan, draft or authorized file change with evidence and uncertainty.\n- Verification: performed and suggested checks are separate; inaccessible sources and unexecuted tools are not counted as used.\n\n')
    out+=('## Ortam ve sınırlar\n\nPaket model ağırlığı, izin, hesap veya API kredisi sağlamaz. Bu sürüm mevcut host araçları, açık erişim ve yerel işlemi kullanır; ücretli servis otomatik alternatif değildir. Klinik/yatırım çıktıları profesyonel kararın veya emir işleminin yerine geçmez.\n\n' if tr else '## Runtime and boundaries\n\nThe package supplies no model weights, permissions, account or API credit. This edition uses existing host tools, open access and local computation; a separately billed service is not an automatic fallback. Clinical/investment outputs do not replace professional judgment or execute orders.\n\n')
    if n=='research-analyst': out+=('Video: yerel FFmpeg/ffprobe yardımcısı örnek kare ve zaman damgası üretir. Görsel yorum mevcut modele, transkripsiyon ayrı tanıma aracına bağlıdır. Örnekleme bütün videonun izlendiği anlamına gelmez.\n\n' if tr else 'Video: the local FFmpeg/ffprobe helper produces sampled frames and timestamps. Visual interpretation needs host image capability; transcription needs a recognizer. Sampling is not complete coverage.\n\n')
    out+=f'## {"Modüller ve kaynak" if tr else "Modules and source"}\n\n[SKILL.md](../../skills/common/{n}/SKILL.md) · [Installation](../INSTALL.md) · [License scope](../LICENSE-SCOPE.md)\n\n'
    if mods:
        out+='| Module | Source scope |\n|---|---|\n'
        for name,desc,path in mods: out+=f'| [{name}](../../skills/common/{n}/{path}) | {desc.replace("|","/")} |\n'
    else: out+=('Bağımsız kök akışı; referanslar giriş dosyasında listelenir.\n' if tr else 'Standalone root workflow; references are linked by the entry point.\n')
    return out

def readme(reg, selected, title, summary, lang='en'):
    tr=lang=='tr'
    result=picture(title)+f'\n# {title}\n\n[English](README.md) · [Türkçe](README.tr.md)\n\n**{summary}**\n\n'
    result+=(f'{len(selected)} bakımı sürdürülen giriş noktası. Göreve göre birini seç; tüm kütüphaneyi bağlama yükleme.\n\n' if tr else f'{len(selected)} maintained entry points. Choose one for the job; do not load the entire library into context.\n\n')
    result+=f'[{"Başla" if tr else "Start here"}](docs/INSTALL.md) · [{"Katalog" if tr else "Browse the catalog"}](https://yigityildiz0.github.io/universal-ai-skill-library/) · [{"İndirmeler" if tr else "Downloads"}](DOWNLOADS.md) · [{"Bakım modeli" if tr else "Maintenance model"}](MAINTAINING.md)\n\n'
    result+=('## Yapmak istediğin işi seç\n\n' if tr else '## Start with the work you want to do\n\n')
    for cat in ORDER:
        rows=[s for s in selected if s['category']==cat]
        if not rows: continue
        result+=f'<details open>\n<summary><strong>{CATEGORY_TR[cat] if tr else cat}</strong> · {len(rows)}</summary>\n\n| Skill | {"Ne işe yarar?" if tr else "What it helps with"} |\n|---|---|\n'
        for s in rows: result+=f'| [{s["id"]}](docs/skills/{s["id"]}.{lang}.md) | {s[lang]["purpose"]} |\n'
        result+='\n</details>\n\n'
    result+=('## Bir skill nasıl çalışır?\n\n' if tr else '## What happens when a skill runs?\n\n')
    result+='~~~mermaid\nflowchart LR\n A[Your goal] --> B[Match the skill]\n B --> C[Load relevant module]\n C --> D[Use available tools]\n D --> E[Verify and explain]\n~~~\n\n'
    result+=('Bu bir iş akışıdır; araç çalıştırıldığı veya bütün sonuçların doğrulandığı iddiası değildir. Her skill sayfasında örnek istek, tetikleme, mekanik, girdi/çıktı ve kaynak modüller var.\n\n' if tr else 'This is the workflow, not a claim that tools ran or every result is verified. Each skill page explains an example request, trigger, mechanics, inputs/outputs and source modules.\n\n')
    result+=('## Tek kaynak, kalıcı koleksiyonlar\n\n' if tr else '## One source. Durable collections.\n\n')
    result+=('Ana kaynak [Universal AI Skill Library]('+BASE+'). Alan depoları aynı sürümün seçilmiş görünümleridir; ayrı ayrı çatallanıp elle düzenlenmez. Mevcut bağlantılar ve geçmiş korunur.\n\n' if tr else 'The canonical source is [Universal AI Skill Library]('+BASE+'). Domain repositories are selected views of the same release—not independently edited forks. Existing links and history stay intact.\n\n')
    result+='[All collections / Tüm koleksiyonlar](COLLECTIONS.md) · [Legacy/community resources](LEGACY.md) · [Licenses & provenance](docs/LICENSE-SCOPE.md)\n\n'
    result+=('## Dürüst kapsam\n\n- Skill kurmak model eğitmek veya hesap/araç bağlamak değildir.\n- Yerel dosya ile web hesabına yükleme farklıdır; desteklenen host akışını kullan.\n- Ek ücretli API veya model indirme otomatik yapılmaz.\n- Eski topluluk kataloğu güncel giriş noktalarının sayısına veya test iddiasına dahil değildir.\n- Kaynak lisansları korunur; bütün üçüncü taraf içeriğine tek lisans varsayılmaz.\n\n' if tr else '## Honest scope\n\n- Installing a skill does not train a model or connect an account/tool.\n- Local files and a web-account import are different; follow the supported host flow.\n- No automatic extra billed API or model download.\n- The historical community catalog is not counted as maintained or claimed as runtime-tested.\n- Source licenses remain attached; no blanket third-party license is assumed.\n\n')
    result+=f'---\nMaintained by [Yigit Yildiz](https://github.com/yigityildiz0) · Source edition {reg["release"]}\n'
    return result
