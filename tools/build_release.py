#!/usr/bin/env python3
"""Build the public release of Yiğit Investment Copilot.

  python tools/build_release.py --refresh-from <path-to-private-master-skill>   # copy + privacy transforms
  python tools/build_release.py                                                # validate + build dist/*.zip
  python tools/build_release.py --check                                        # validate only (CI)

--refresh-from also copies the command and agent files from the master's `externals/` folder
(two levels above the skill) into platforms/ and regenerates the Claude Code plugin commands and
.claude-plugin/marketplace.json.

Outputs in dist/:
  yigit-investment-copilot-chatgpt.zip       skill folder at the ZIP root (ChatGPT Skills upload; also Codex)
  yigit-investment-copilot-claude.zip        skill folder at the ZIP root, <=200-char description (claude.ai upload)
  yigit-investment-copilot-claude-code.zip   skills/ + commands/ + INSTALL.md for ~/.claude/ (manual Claude Code install)
  yigit-investment-copilot-opencode.zip      skills/ + agents/ + commands/ + INSTALL.md for ~/.config/opencode/
  yigit-investment-copilot-all-in-one.zip    everything above + installers + docs
  SHA256SUMS.txt
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "yigit-investment-copilot"
VERSION = "2.1.0"
SKILL = ROOT / "skill" / NAME
DIST = ROOT / "dist"
PLATFORMS = ROOT / "platforms"
PLUGIN_NAME = "borsa"
SHORT_DESCRIPTION = ("Investment copilot: scans all BIST, TEFAS funds and US stocks by horizon; fundamental/technical/KAP/macro analysis, "
                     "buy-sell-stop plans, portfolio risk. Hisse/fon: ne alayım, satayım mı. Never trades.")
PLUGIN_DESCRIPTION = ("BIST / TEFAS / US-stock research copilot: whole-market scan, deep stock analysis, committee and red team, "
                      "trade plans, fund screening, morning notes, portfolio risk. Research only; never places orders.")
# local Claude Code / OpenCode command name -> short name inside the plugin (/borsa:<short>)
PLUGIN_COMMANDS = {"borsa-tara": "tara", "hisse-analiz": "hisse", "hisse-sat": "sat", "piyasa": "piyasa",
                   "strateji-test": "strateji", "sabah-bulteni": "bulten", "sektor": "sektor", "fon-tara": "fon",
                   "portfoy-kur": "portfoy", "izle": "izle"}
PUBLIC_REPLACEMENTS = [
    ("Yiğit's investment research and decision copilot", "Investment research and decision copilot"),
]
PRIVATE_MARKERS = ["(Yiğit — private)", "Yiğit's investment"]
# Owner-specific replacements and markers (e.g. personal bank or broker names) live in an untracked
# local file so they are never published: {"replacements": [[old, new], ...], "markers": [...]}.
LOCAL_TRANSFORMS = Path(__file__).with_name(".private-transforms.json")
if LOCAL_TRANSFORMS.exists():
    _local = json.loads(LOCAL_TRANSFORMS.read_text(encoding="utf-8"))
    PUBLIC_REPLACEMENTS += [tuple(pair) for pair in _local.get("replacements", [])]
    PRIVATE_MARKERS += list(_local.get("markers", []))
PROFILE_TEMPLATE = """# Investor profile (fill in, optional)

Use this file to give the copilot stable preferences. Keep it free of account numbers, balances, passwords
or anything you would not want to share. Treat every dated item as historical until confirmed in chat.

## Stable preferences

- Language and answer style: (e.g. short Turkish answers, explain terms once)
- Typical horizons: (e.g. swing 2–6 weeks, core 1+ years)
- Risk posture: (e.g. 1% of capital per trade; separate small speculative budget)
- Benchmark: (e.g. beat deposit rates in TL and stay positive in USD)
- Constraints: (e.g. cash equities only, no leverage/short selling; participation-index only)
- Markets and products used: (e.g. BIST shares, TEFAS funds, gold)

## Behavioural guardrails

- Detect "kesin artacak", "parayı katla" or urgent recovery language as a request for scenario discipline, not certainty.
- Distinguish disposable speculative money from core savings; never infer high risk capacity from one small trade.
- Verify instrument identity, live executable price, fees, lot size, budget and maximum loss before giving quantities.
- Do not store balances, account numbers, credentials, tax documents or full portfolio details in this skill.
"""


def split_frontmatter(text):
    match = re.match(r"^﻿?---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not match:
        raise SystemExit("SKILL.md has no frontmatter")
    return match.group(1), match.group(2)


def set_description(text, description):
    fm, body = split_frontmatter(text)
    fm = re.sub(r"^description:.*$", "description: " + json.dumps(description, ensure_ascii=False), fm, flags=re.M)
    return "---\n" + fm + "\n---\n\n" + body.lstrip("\n")


def files_of(folder):
    return sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def refresh(master):
    master = Path(master)
    if not (master / "SKILL.md").exists():
        raise SystemExit(f"{master} is not a skill folder")
    if SKILL.exists():
        shutil.rmtree(SKILL)
    shutil.copytree(master, SKILL, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (SKILL / "references" / "investor-profile.md").write_text(PROFILE_TEMPLATE, encoding="utf-8")
    for path in files_of(SKILL):
        if path.suffix not in (".md", ".json", ".py", ".txt"):
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for old, rep in PUBLIC_REPLACEMENTS:
            new = new.replace(old, rep)
        if new != text:
            path.write_bytes(new.encode("utf-8"))
    normalize_lf(SKILL)
    print(f"refreshed {SKILL.relative_to(ROOT)} from {master}")
    externals = master.parents[1] / "externals"
    if externals.exists():
        copy_externals(externals)
    generate_plugin()


def public_text(text):
    for old, rep in PUBLIC_REPLACEMENTS:
        text = text.replace(old, rep)
    return text.replace("\r\n", "\n")


def copy_externals(externals):
    """Commands and the OpenCode agent come from the master; only the investment-copilot files are copied."""
    plan = [(externals / "opencode-agents" / "borsa-analist.md", PLATFORMS / "opencode" / "agents" / "borsa-analist.md")]
    for name in PLUGIN_COMMANDS:
        plan.append((externals / "opencode-commands" / f"{name}.md", PLATFORMS / "opencode" / "commands" / f"{name}.md"))
        plan.append((externals / "claude-commands" / f"{name}.md", PLATFORMS / "claude" / "commands" / f"{name}.md"))
    copied = 0
    for src, dst in plan:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(public_text(src.read_text(encoding="utf-8")).encode("utf-8"))
            copied += 1
    print(f"copied {copied} command/agent files from {externals}")


def generate_plugin():
    """Claude Code plugin: the repo root is the plugin source (skills + short-named commands)."""
    src_dir, out_dir = PLATFORMS / "claude" / "commands", PLATFORMS / "claude" / "plugin-commands"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for local, short in PLUGIN_COMMANDS.items():
        src = src_dir / f"{local}.md"
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        for other_local, other_short in PLUGIN_COMMANDS.items():
            text = text.replace(f"/{other_local} ", f"/{PLUGIN_NAME}:{other_short} ").replace(f"/{other_local})", f"/{PLUGIN_NAME}:{other_short})")
        (out_dir / f"{short}.md").write_bytes(text.encode("utf-8"))
    marketplace = {
        "name": NAME,
        "description": "Investment research copilot for Borsa İstanbul, TEFAS and US stocks (skill + slash commands).",
        "owner": {"name": "yigityildiz0"},
        "metadata": {"version": VERSION},
        "plugins": [{
            "name": PLUGIN_NAME,
            "description": PLUGIN_DESCRIPTION,
            "version": VERSION,
            "source": "./",
            "strict": False,
            "skills": [f"./skill/{NAME}"],
            "commands": ["./platforms/claude/plugin-commands/"],
            "homepage": f"https://github.com/yigityildiz0/{NAME}",
            "repository": f"https://github.com/yigityildiz0/{NAME}",
            "license": "MIT",
            "keywords": ["finance", "investing", "stocks", "borsa-istanbul", "bist", "tefas", "turkey", "research"],
        }],
    }
    (ROOT / ".claude-plugin").mkdir(exist_ok=True)
    (ROOT / ".claude-plugin" / "marketplace.json").write_bytes(
        (json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"generated plugin '{PLUGIN_NAME}' ({len(list(out_dir.glob('*.md')))} commands) + .claude-plugin/marketplace.json")


def validate():
    problems = []
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
    desc_raw = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()
    desc = json.loads(desc_raw) if desc_raw.startswith('"') else desc_raw
    if name != NAME:
        problems.append(f"name {name} != {NAME}")
    if not 1 <= len(desc) <= 1024 or "<" in desc or ">" in desc:
        problems.append(f"description invalid ({len(desc)} chars)")
    if len(SHORT_DESCRIPTION) > 200:
        problems.append("short description > 200 chars")
    if body.count("\n") >= 500:
        problems.append("SKILL.md body >= 500 lines")
    files = files_of(SKILL)
    if len(files) > 200:
        problems.append(f"{len(files)} files > 200")
    if any(p.name == "SKILL.md" and p.parent != SKILL for p in files):
        problems.append("nested SKILL.md")
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    for md in [p for p in files if p.suffix == ".md"]:
        for target in link.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http", "mailto:", "#")):
                continue
            if not (md.parent / target.split("#")[0]).exists():
                problems.append(f"broken link {md.relative_to(SKILL)} -> {target}")
    for path in files + files_of(ROOT / "platforms"):
        if path.suffix in (".md", ".json", ".py", ".txt"):
            content = path.read_text(encoding="utf-8")
            for marker in PRIVATE_MARKERS:
                if marker in content:
                    problems.append(f"private marker '{marker}' in {path.relative_to(ROOT)}")
    for path in [p for p in files if p.suffix == ".json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"bad json {path.relative_to(SKILL)}: {exc}")
    for path in [p for p in files if p.suffix == ".py"]:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            problems.append(f"syntax {path.relative_to(SKILL)}: {exc}")
    market = ROOT / ".claude-plugin" / "marketplace.json"
    if market.exists():
        try:
            data = json.loads(market.read_text(encoding="utf-8"))
            for entry in data.get("plugins", []):
                for rel in entry.get("skills", []) + entry.get("commands", []):
                    if not (ROOT / rel).exists():
                        problems.append(f"marketplace path missing: {rel}")
                if entry.get("version") != VERSION:
                    problems.append(f"marketplace version {entry.get('version')} != {VERSION}")
        except json.JSONDecodeError as exc:
            problems.append(f"bad marketplace.json: {exc}")
    for folder in (PLATFORMS / "claude" / "commands", PLATFORMS / "claude" / "plugin-commands", PLATFORMS / "opencode" / "commands"):
        for md in folder.glob("*.md") if folder.exists() else []:
            head = md.read_text(encoding="utf-8").split("---")
            if len(head) < 3 or "description:" not in head[1]:
                problems.append(f"command without frontmatter description: {md.relative_to(ROOT)}")
    return problems, len(files), len(desc)


TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".sh", ".ps1", ".svg", ".yml", ".yaml", ".csv"}


def normalize_lf(folder):
    """Rewrite text files with LF line endings so every platform gets identical bytes."""
    for path in files_of(folder):
        if path.suffix in TEXT_SUFFIXES:
            data = path.read_bytes()
            if b"\r\n" in data:
                path.write_bytes(data.replace(b"\r\n", b"\n"))


def zip_tree(zf, folder, prefix, transform=None):
    for path in files_of(folder):
        arc = (Path(prefix) / path.relative_to(folder)).as_posix()
        if transform and path.name == "SKILL.md" and path.parent == folder:
            zf.writestr(arc, transform(path.read_text(encoding="utf-8")).replace("\r\n", "\n"))
        elif path.suffix in TEXT_SUFFIXES:
            zf.writestr(arc, path.read_bytes().replace(b"\r\n", b"\n"))
        else:
            zf.write(path, arc)


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    outputs = []
    chatgpt = DIST / f"{NAME}-chatgpt.zip"
    with zipfile.ZipFile(chatgpt, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_tree(zf, SKILL, NAME)
    outputs.append(chatgpt)
    claude = DIST / f"{NAME}-claude.zip"
    with zipfile.ZipFile(claude, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_tree(zf, SKILL, NAME, lambda t: set_description(t, SHORT_DESCRIPTION))
    outputs.append(claude)
    claude_code = DIST / f"{NAME}-claude-code.zip"
    with zipfile.ZipFile(claude_code, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_tree(zf, SKILL, f"skills/{NAME}")
        zip_tree(zf, PLATFORMS / "claude" / "commands", "commands")
        zf.writestr("INSTALL.md", CLAUDE_CODE_INSTALL)
    outputs.append(claude_code)
    opencode = DIST / f"{NAME}-opencode.zip"
    with zipfile.ZipFile(opencode, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_tree(zf, SKILL, f"skills/{NAME}")
        zip_tree(zf, ROOT / "platforms" / "opencode" / "agents", "agents")
        zip_tree(zf, ROOT / "platforms" / "opencode" / "commands", "commands")
        zf.write(ROOT / "platforms" / "opencode" / "INSTALL.md", "INSTALL.md")
    outputs.append(opencode)
    allin = DIST / f"{NAME}-all-in-one.zip"
    with zipfile.ZipFile(allin, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in outputs:
            zf.write(item, f"platform-zips/{item.name}")
        zip_tree(zf, SKILL, f"skill/{NAME}")
        zip_tree(zf, ROOT / "platforms", "platforms")
        zip_tree(zf, ROOT / "install", "install")
        for doc in ("README.md", "README.en.md", "LICENSE", "DISCLAIMER.md", "CHANGELOG.md"):
            if (ROOT / doc).exists():
                zf.writestr(doc, (ROOT / doc).read_bytes().replace(b"\r\n", b"\n"))
    outputs.append(allin)
    lines = []
    for item in outputs:
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        lines.append(f"{digest}  {item.name}")
    (DIST / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for item in outputs:
        print(f"built {item.name} ({item.stat().st_size:,} bytes)")


CLAUDE_CODE_INSTALL = """# Claude Code kurulumu / installation

Önerilen yol (güncellemeleri otomatik alır) / recommended, auto-updating:

    claude plugin marketplace add yigityildiz0/yigit-investment-copilot
    claude plugin install borsa@yigit-investment-copilot

Komutlar eklentide /borsa:tara, /borsa:hisse, /borsa:sat, /borsa:piyasa, /borsa:bulten, /borsa:sektor,
/borsa:fon, /borsa:portfoy, /borsa:izle, /borsa:strateji olarak görünür.

Elle kurulum / manual install (this ZIP):

    skills/yigit-investment-copilot/  ->  ~/.claude/skills/yigit-investment-copilot/
    commands/*.md                     ->  ~/.claude/commands/   (/borsa-tara, /hisse-analiz, /sabah-bulteni ...)

Aynı anda hem eklentiyi hem elle kurulumu kullanma (skill iki kez yüklenir).
Do not combine the plugin and the manual install (the skill would load twice). Python 3.9+ is required for the data scripts.
"""


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh-from", type=Path)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.refresh_from:
        refresh(a.refresh_from)
    problems, count, desc_len = validate()
    print(f"validate: {count} files, description {desc_len} chars, problems: {len(problems)}")
    for p in problems:
        print("  -", p)
    if problems:
        return 1
    if not a.check:
        build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
