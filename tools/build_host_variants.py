"""Canonical-only host renderings and hash-owned deployment primitives.

No installed copy or legacy cloud subset is ever a source. Importing this module
does not write. --check compares bytes without creating directories or manifests.
"""
from pathlib import Path, PurePosixPath
import argparse
import datetime as dt
import hashlib
import json
import os
import re

MASTER = Path(__file__).resolve().parent
MANIFEST = ".yigit-host-generated.json"
SKIP = {"__pycache__", ".DS_Store", ".git"}
HOSTS = ("codex", "claude")
LITERATURE = ("medical-evidence-research", "physio-clinical-copilot")
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

PROVIDER_NOTES = {
    "codex": """## GPT / Codex execution environment

Use only search, browser, connector and file tools exposed in the active session.
Inspect live capabilities before selecting a provider; optional PubMed/Elicit/scite
tools are not mandatory dependencies. Follow the host's tool instructions and
report unavailable network/full text explicitly. Packaged references are relative
to this skill; do not assume local Windows paths exist in ChatGPT web/mobile.
Local installation does not install a plugin into the user's cloud account.
""",
    "claude": """## Claude execution environment

Use only enabled web/search/MCP/file tools in this Claude session and inspect their
live capabilities. Do not assume Codex connectors, local Windows paths, network
access or subscriptions exist in Claude.ai. A Claude API skill container needs an
external retrieval tool for live literature; it cannot establish access by itself.
Use the package's own search/appraisal gates when optional companion skills are
absent. Local Claude Code files do not upload changes to the Claude.ai account.
""",
}

COMMON_RUNTIME = """# Host execution adapter

This complete edition is generated only from the canonical master. Preserve the
source's workflow, licenses, explicit activation gates and authorization rules.
The original SKILL.md is retained in source-SKILL.md for provenance, not as a
second auto-discovered skill. Edit the canonical master or generators only.

- Use the live tool catalog. Examples named Read/Write/Bash/Task, web.run,
  functions.*, MCP, or another host's tool names are intent, not available APIs.
- Resolve scripts/references from this skill's actual root, and module-relative
  paths from the module directory. Personal absolute paths in preserved examples
  are examples only: discover the user's workspace, home and shell first.
- Browser/desktop/UI automation requires both a connected tool and user authority.
  No screenshot access, operating-system control, API key, account entitlement,
  plugin activation, GPU, paid quota or network access is created by this package.
- Web/mobile containers cannot be assumed to access local Windows files. Ask for
  the needed input or report the missing capability; never claim an action ran.
- Preserve explicit-only Caveman activation and every source capability.
- Apply the user's no-extra-cost profile to the complete module tree: use this
  host's existing session/tools, public sources and local computation. Never
  fall back to separately billed APIs, cloud jobs, credits or paid trials.
  A saved key or configured connector does not change this choice. Preserved
  provider examples are references; use a free/local equivalent or disclose
  the unavailable capability. Gemini Deep Research is removed from this set.
- Do not auto-enable tools, alter sandbox/configuration, install dependencies or
  delegate merely because an upstream example does so. Respect session policy.
- Local files and cloud/account skills are separate. Select one active source per
  skill if duplicates appear; preserve existing user enable/disable preferences.
"""


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    """Reject Windows and POSIX traversal, ADS, ambiguous names and ZIP aliases."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe relative path: {name!r}")
    parts = name.split("/")
    if any(p in ("", ".", "..") or p.endswith((".", " ")) for p in parts):
        raise ValueError(f"Unsafe relative path: {name!r}")
    if any(ord(c) < 32 for c in name) or PurePosixPath(name).is_absolute():
        raise ValueError(f"Unsafe relative path: {name!r}")
    if any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p) for p in parts):
        raise ValueError(f"Reserved Windows name: {name!r}")
    return name


def checked_path(root, rel=None):
    root = Path(root).absolute()
    path = root if rel is None else root / safe_relative(rel)
    if path.resolve() != path.absolute():
        raise ValueError(f"Linked/reparse target is not allowed: {path}")
    if rel is not None and not path.is_relative_to(root):
        raise ValueError(f"Path escaped root: {path}")
    return path


def source_files(folder):
    folder = checked_path(folder)
    result, seen = {}, set()
    if not folder.exists():
        return result
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if set(p.relative_to(folder).parts) & SKIP or p.suffix == ".pyc":
            continue
        checked_path(folder, rel)
        if p.is_file():
            safe_relative(rel)
            if rel.casefold() in seen:
                raise ValueError(f"Case-colliding source: {rel}")
            seen.add(rel.casefold())
            result[rel] = p.read_bytes()
    return result


def split_frontmatter(text):
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md requires YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("Unterminated YAML frontmatter")
    return lines[1:end], "".join(lines[end + 1:])


def set_frontmatter(text, **values):
    """Replace top-level scalars with JSON-quoted YAML; no regex replacement.

    Other metadata and the complete body survive. Folded/literal old values are
    removed through their indented block. JSON escaping handles quotes, colons,
    backslashes and newlines without interpreting replacement backreferences.
    """
    lines, body = split_frontmatter(text)
    out, found, skip = [], set(), False
    for line in lines:
        key = line.split(":", 1)[0] if ":" in line and not line[:1].isspace() else None
        if key in values:
            if key in found:
                raise ValueError(f"Duplicate frontmatter key: {key}")
            out.append(key + ": " + json.dumps(values[key], ensure_ascii=False) + "\n")
            found.add(key)
            skip = True
        elif skip and (not line.strip() or line[:1].isspace()):
            continue
        else:
            skip = False
            out.append(line.rstrip("\r\n") + "\n")
    for key in values.keys() - found:
        out.append(key + ": " + json.dumps(values[key], ensure_ascii=False) + "\n")
    return "---\n" + "".join(out) + "---\n" + body


def frontmatter_scalar(text, key):
    lines, _ = split_frontmatter(text)
    for i, line in enumerate(lines):
        if line.startswith(key + ":"):
            value = line.partition(":")[2].strip()
            if value.startswith('"'):
                return json.loads(value)
            if value.startswith("'") and value.endswith("'"):
                return value[1:-1].replace("''", "'")
            if value in (">", ">-", ">+", "|", "|-", "|+"):
                block = []
                for following in lines[i + 1:]:
                    if following.strip() and not following[:1].isspace():
                        break
                    block.append(following.strip())
                return (" " if value.startswith(">") else "\n").join(block).strip()
            return value
    return ""


def release_info(master=MASTER, targets=None):
    targets = targets if targets is not None else json.loads((Path(master) / "targets.json").read_text("utf-8"))
    value = targets.get("release_date")
    if not value:
        stamps = [p.stat().st_mtime for p in (Path(master) / "skills").rglob("SKILL.md")]
        value = dt.datetime.fromtimestamp(max(stamps), dt.timezone.utc).date().isoformat() if stamps else dt.date.today().isoformat()
    day = dt.date.fromisoformat(value)
    return {"date": day.isoformat(), "version": targets.get("release_version", f"{day.year}.{day.month}.{day.day}")}


def validate_skill(name, mapping, short=False):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValueError(f"Invalid skill name: {name}")
    text = mapping["SKILL.md"].decode("utf-8-sig")
    if frontmatter_scalar(text, "name") != name:
        raise ValueError(f"SKILL name mismatch: {name}")
    desc = frontmatter_scalar(text, "description")
    if not desc or len(desc) > (200 if short else 1024):
        raise ValueError(f"Invalid description ({len(desc)} characters): {name}")
    if any(x in desc for x in ("<", ">")):
        raise ValueError(f"XML-like description: {name}")
    for rel in mapping:
        safe_relative(rel)
        if rel != "SKILL.md" and PurePosixPath(rel).name == "SKILL.md":
            raise ValueError(f"Nested skill entrypoint: {name}/{rel}")


def desired_files(folder, provider, descriptions=None):
    if provider not in HOSTS:
        raise ValueError(f"Unknown provider: {provider}")
    folder = Path(folder)
    files = source_files(folder)
    original = dict(files)
    name = folder.name
    validate_skill(name, original)
    for rel in ("yigit/source-SKILL.md", "yigit/host-runtime.md", "yigit/host-manifest.json"):
        if rel in files:
            raise ValueError(f"Reserved generated path in canonical source: {name}/{rel}")
    text = files["SKILL.md"].decode("utf-8-sig")
    if provider == "claude":
        if descriptions is None:
            descriptions = json.loads((folder.parent.parent / "claude-descriptions.json").read_text("utf-8"))
        desc = descriptions[name]
        if not isinstance(desc, str) or not 0 < len(desc) <= 200:
            raise ValueError(f"Invalid Claude description: {name}")
        text = set_frontmatter(text, description=desc)
    fm, body = split_frontmatter(text)
    intro = "\n## Host execution\n\nRead [the host adapter](yigit/host-runtime.md) before execution.\n\n"
    files["SKILL.md"] = ("---\n" + "".join(fm) + "---\n" + intro + body.lstrip("\n")).encode("utf-8")
    files["yigit/source-SKILL.md"] = original["SKILL.md"]
    runtime = COMMON_RUNTIME + "\n" + PROVIDER_NOTES[provider]
    files["yigit/host-runtime.md"] = runtime.encode("utf-8")
    if provider == "codex" and name in LITERATURE:
        display, short = {
            "medical-evidence-research": ("Tıbbi Kanıt ve Literatür", "PubMed/PEDro taraması ve klinik kanıt değerlendirmesi"),
            "physio-clinical-copilot": ("Fizyoterapi Klinik Yardımcısı", "Klinik akıl yürütme, güvenli rehabilitasyon ve ölçüm"),
        }[name]
        files["agents/openai.yaml"] = ("interface:\n  display_name: " + json.dumps(display, ensure_ascii=False)
            + "\n  short_description: " + json.dumps(short, ensure_ascii=False)
            + '\n  default_prompt: "Use $' + name + ' to help with my clinical or literature question in Turkish."\n'
            + "policy:\n  allow_implicit_invocation: true\n").encode("utf-8")
    if provider == "codex" and name in ("caveman", "parallel-web"):
        rel = "agents/openai.yaml"
        if rel not in files:
            files[rel] = b"policy:\n  allow_implicit_invocation: false\n"
    files["yigit/host-manifest.json"] = json_bytes({
        "format": 1, "host": provider, "skill": name,
        "source_files": {k: digest(v) for k, v in sorted(original.items())},
        "adaptations": ["host runtime", "original entrypoint retained", "Claude upload description" if provider == "claude" else "Codex metadata"],
    })
    validate_skill(name, files, short=provider == "claude")
    return files


def render_all(master=MASTER, provider="codex", names=None):
    master = Path(master)
    descriptions = json.loads((master / "claude-descriptions.json").read_text("utf-8"))
    roots = sorted(p for p in (master / "skills").iterdir() if (p / "SKILL.md").is_file())
    return {p.name: desired_files(p, provider, descriptions) for p in roots if names is None or p.name in names}


def load_manifest(root, manifest=MANIFEST):
    path = checked_path(root, manifest)
    if not path.exists():
        return {}
    value = json.loads(path.read_text("utf-8"))
    if value.get("format") != 1 or not isinstance(value.get("files"), dict):
        raise ValueError(f"Invalid managed manifest: {path}")
    for rel, sha in value["files"].items():
        safe_relative(rel)
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError(f"Invalid managed hash: {path}/{rel}")
    return value["files"]


def sync_mapping(root, mapping, *, check=False, manifest=MANIFEST, adopt=None, backup=None):
    """Apply only hash-owned files; preserve all unmanaged extras.

    adopt is an independently verified {relative-path: SHA256} baseline, never an
    implicit same-name overwrite. Preflight every collision before the first write.
    backup(path) may retain an overwritten/deleted owned file. Check is read-only.
    """
    root = checked_path(root)
    prior = load_manifest(root, manifest)
    owned = dict(adopt or {})
    owned.update(prior)
    seen = set()
    for rel, data in mapping.items():
        safe_relative(rel)
        if rel == manifest or rel.casefold() in seen or not isinstance(data, bytes):
            raise ValueError(f"Invalid/colliding managed entry: {rel}")
        seen.add(rel.casefold())
    changes, conflicts = [], []
    for rel in sorted(set(mapping) | set(owned)):
        path = checked_path(root, rel)
        current = path.read_bytes() if path.is_file() else None
        desired = mapping.get(rel)
        if current == desired:
            continue
        if path.exists() and not path.is_file():
            conflicts.append(rel + " (not a file)")
        elif current is not None and digest(current) != owned.get(rel):
            conflicts.append(rel + " (unmanaged or modified)")
        else:
            changes.append(rel)
    if conflicts:
        raise ValueError("Refusing to overwrite/delete unowned files at " + str(root) + ": " + ", ".join(conflicts[:20]))
    payload = json_bytes({"format": 1, "files": {k: digest(v) for k, v in sorted(mapping.items())}})
    marker = checked_path(root, manifest)
    if not marker.exists() or marker.read_bytes() != payload:
        changes.append(manifest)
    if not check:
        for rel in changes:
            if rel == manifest:
                continue
            path = checked_path(root, rel)
            if path.exists() and backup is not None:
                backup(path)
            if rel in mapping:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(mapping[rel])
            elif path.is_file():
                path.unlink()
        if manifest in changes:
            root.mkdir(parents=True, exist_ok=True)
            marker.write_bytes(payload)
    return changes


def flatten(skills):
    return {f"{name}/{rel}": data for name, fs in sorted(skills.items()) for rel, data in sorted(fs.items())}


def verified_baseline(master, target):
    """Read a configured migration snapshot, verifying its ZIP bytes and hashes.

    This is solely ownership evidence for legacy output. It is never source input.
    """
    master, target = Path(master), Path(target).absolute()
    config = json.loads((master / "targets.json").read_text("utf-8"))
    snapshot = config.get("migration_backup")
    if not snapshot:
        return {}
    base = Path(os.path.expanduser(snapshot))
    hashes = json.loads((base / "sha256.json").read_text("utf-8"))
    import zipfile
    candidates = [(master, "master/")]
    for local, prefix in config.get("migration_roots", {}).items():
        candidates.append((Path(os.path.expanduser(local)).absolute(), prefix.rstrip("/") + "/"))
    for local, prefix in candidates:
        if target.is_relative_to(local):
            suffix = target.relative_to(local).as_posix()
            prefix += "" if suffix == "." else suffix + "/"
            selected = {k[len(prefix):]: v for k, v in hashes.items() if k.startswith(prefix)}
            with zipfile.ZipFile(base / "before-rebuild.zip") as z:
                for rel, sha in selected.items():
                    safe_relative(rel)
                    if digest(z.read(prefix + rel)) != sha:
                        raise ValueError("Migration snapshot hash mismatch: " + rel)
            return selected
    return {}


def refresh_variants(check=False, master=MASTER, providers=HOSTS, names=None):
    master = Path(master)
    plans = []
    for provider in providers:
        rendered = render_all(master, provider, names)
        # A selected compatibility refresh must not retire unrelated skills.
        if names is not None:
            for name, fs in rendered.items():
                root = master / "variants" / provider / name
                plans.append((root, fs))
        else:
            plans.append((master / "variants" / provider, flatten(rendered)))
    changed = []
    for root, mapping in plans:
        adoption = verified_baseline(master, root)
        delta = sync_mapping(root, mapping, check=True, adopt=adoption)
        changed.extend(f"{root.relative_to(master).as_posix()}/{rel}" for rel in delta)
    if not check:
        for root, mapping in plans:
            sync_mapping(root, mapping, adopt=verified_baseline(master, root))
    print(f"Host variants: {len(changed)} file(s) {'would change' if check else 'changed'}")
    return changed


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--master", type=Path, default=MASTER)
    ap.add_argument("--provider", choices=HOSTS, action="append")
    args = ap.parse_args()
    changes = refresh_variants(args.check, args.master, args.provider or HOSTS)
    raise SystemExit(1 if args.check and changes else 0)
