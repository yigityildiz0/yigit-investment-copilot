"""Deterministic, complete per-host Desktop packages; cloud limits never drop files.

All builders accept in-memory renderings and arbitrary staging destinations.
Writing a real Desktop is the sync CLI's responsibility. No work runs on import.
"""
from pathlib import Path
import datetime as dt
import io
import json
import zipfile

from build_host_variants import (PLUGIN_SCHEMA, digest, flatten, frontmatter_scalar,
    json_bytes, safe_relative, set_frontmatter, source_files, sync_mapping, validate_skill)

DESKTOP_MANIFEST = ".yigit-desktop-managed.json"
DOCS = {
    "claude_upload": "https://support.claude.com/en/articles/12512198-how-to-create-custom-skills",
    "claude_plugin": "https://code.claude.com/docs/en/plugins/manifest-reference",
    "openai_plugin": "https://developers.openai.com/plugins/build/plugins",
    "agent_schema": PLUGIN_SCHEMA,
    "gemini_cli_skills": "https://geminicli.com/docs/cli/creating-skills/",
}
# Gemini app (web) Skills accept SKILL.md folders with these reference file types (≤100 MB total).
GEMINI_WEB_EXT = {".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml", ".csv", ".pdf", ".jpg", ".jpeg", ".png"}


def gemini_web_payload(name, mapping):
    """Gemini app upload copy: supported file types only; the rest is listed, never silently lost."""
    keep, dropped = {}, []
    for rel, data in sorted(mapping.items()):
        if Path(rel).suffix.lower() in GEMINI_WEB_EXT or rel.endswith("LICENSE") or Path(rel).name.upper().startswith(("LICENSE", "NOTICE")):
            keep[rel if Path(rel).suffix else rel + ".txt"] = data
        else:
            dropped.append(rel)
    if dropped:
        keep["GEMINI-UNSUPPORTED-FILES.md"] = ("# Files not included in the Gemini app copy\n\n"
            "The Gemini app accepts text, code (.py/.sh), data and document/image files only. These files exist in the "
            "complete source (Gemini/gemini-cli-skills.zip or the full-source ZIP) and must be run locally when needed:\n\n"
            + "".join(f"- {r}\n" for r in dropped)).encode("utf-8")
    return keep


def files(root):
    return source_files(root)


def zip_bytes(mapping, release_date="1980-01-01"):
    day = dt.date.fromisoformat(release_date)
    stamp = (max(1980, min(day.year, 2107)), day.month, day.day, 0, 0, 0)
    seen = set()
    for rel in mapping:
        safe_relative(rel)
        if rel.casefold() in seen:
            raise ValueError("Case-colliding ZIP entry: " + rel)
        seen.add(rel.casefold())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, data in sorted(mapping.items()):
            zi = zipfile.ZipInfo(rel, stamp)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = buf.getvalue()
    validate_zip(data)
    return data


def validate_zip(data, *, skill=None, limit=None):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) != len({n.casefold() for n in names}):
            raise ValueError("Duplicate/case-colliding ZIP entries")
        for info in z.infolist():
            safe_relative(info.filename)
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("ZIP symlink is not allowed")
        if z.testzip() is not None:
            raise ValueError("Corrupt ZIP")
        if limit is not None and len(names) > limit:
            raise ValueError(f"ZIP has {len(names)} files; limit {limit}")
        if skill is not None:
            if f"{skill}/SKILL.md" not in names or any(not n.startswith(skill + "/") for n in names):
                raise ValueError("Skill ZIP must have exactly one skill directory at root")
    return names


def plugin_manifest(name, release, count, provider="agent"):
    result = {"name": name, "version": release["version"],
              "description": f"Complete canonical-generated skill bundle ({count} skills)."}
    if provider == "agent":
        result["$schema"] = PLUGIN_SCHEMA
    elif provider not in ("codex", "claude"):
        raise ValueError("Unknown plugin manifest provider")
    validate_plugin_manifest(result, provider)
    return result


def validate_plugin_manifest(value, provider="agent"):
    """Validate our emitted minimal subset against the official manifest contracts.

    Agent Plugins 1.0.0 requires $schema AND name, additionalProperties=false.
    Claude and the legacy Codex manifest require name, support version/description.
    The authoritative URLs are included in the package's build manifest.
    """
    import re
    allowed = {"$schema", "name", "version", "description"} if provider == "agent" else {"name", "version", "description"}
    if set(value) - allowed or not isinstance(value.get("name"), str):
        raise ValueError("Invalid plugin manifest fields")
    if not re.fullmatch(r"(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value["name"]) or len(value["name"]) > 64:
        raise ValueError("Invalid plugin name")
    if provider == "agent" and value.get("$schema") != PLUGIN_SCHEMA:
        raise ValueError("Required Agent Plugins $schema is missing")
    if any(not isinstance(v, str) for v in value.values()):
        raise ValueError("Plugin manifest values must be strings")


def plugin_files(skills, release, name="yigit-skills", provider="codex"):
    result = {f"{name}/skills/{rel}": data for rel, data in flatten(skills).items()}
    if provider == "codex":
        result[f"{name}/plugin.json"] = json_bytes(plugin_manifest(name, release, len(skills)))
        result[f"{name}/.codex-plugin/plugin.json"] = json_bytes(plugin_manifest(name, release, len(skills), "codex"))
    elif provider == "claude":
        result[f"{name}/.claude-plugin/plugin.json"] = json_bytes(plugin_manifest(name, release, len(skills), "claude"))
    else:
        raise ValueError("Unsupported plugin host")
    return result


def cloud_parts(name, mapping, limit=200):
    """Stable module-boundary splitting, with exact SHA256 coverage of every file.

    Full unsplit source is always packaged separately. Shared resources are
    duplicated intentionally; original entrypoints survive as source-SKILL.md.
    Oversized individual modules are split into clearly labelled file segments.
    """
    validate_skill(name, mapping, short=True)
    if len(mapping) <= limit:
        return {name: dict(mapping)}, {"source_skill": name, "split": False,
            "parts": [name], "modules": sorted({r.split('/')[1] for r in mapping if r.startswith('modules/') and len(r.split('/')) > 2}),
            "files": {rel: {"sha256": digest(data), "locations": [f"{name}/{rel}"]} for rel, data in sorted(mapping.items())}}
    shared = {r: b for r, b in mapping.items() if not r.startswith("modules/") and r != "SKILL.md"}
    shared["yigit/complete-host-entrypoint.md"] = mapping["SKILL.md"]
    # Three generated entries: SKILL.md, CLOUD-PART.json, CLOUD-README.md.
    capacity = limit - len(shared) - 3
    if capacity < 1:
        raise ValueError(f"Shared files alone exceed upload budget: {name}")
    modules = {}
    for rel, data in sorted(mapping.items()):
        if rel.startswith("modules/"):
            key = rel.split("/")[1]
            modules.setdefault(key, {})[rel] = data
    if not modules:
        raise ValueError(f"Oversized non-modular skill needs an explicit partition: {name}")
    units = []
    for module, fs in sorted(modules.items()):
        items = list(fs.items())
        for offset in range(0, len(items), capacity):
            units.append((module, dict(items[offset:offset + capacity]), len(items) > capacity))
    groups, group, size = [], [], 0
    for unit in units:
        if group and size + len(unit[1]) > capacity:
            groups.append(group)
            group, size = [], 0
        group.append(unit)
        size += len(unit[1])
    if group:
        groups.append(group)
    parts, coverage = {}, {r: {"sha256": digest(b), "locations": []} for r, b in sorted(mapping.items())}
    part_names = [f"{name[:53]}-part-{i:03d}" for i in range(1, len(groups) + 1)]
    module_parts = {m: [part_names[i] for i, g in enumerate(groups) if any(u[0] == m for u in g)] for m in modules}
    for i, group in enumerate(groups):
        part_name = part_names[i]
        module_names = [u[0] for u in group]
        payload = dict(shared)
        for _, fs, _ in group:
            payload.update(fs)
        desc = f"{name}: part {i + 1}/{len(groups)}, {len(module_names)} modules. Use bundled modules only; CLOUD-PART.json routes the complete library."
        text = "---\nname: " + json.dumps(part_name) + "\ndescription: " + json.dumps(desc) + "\n---\n\n"
        text += f"# {name}: cloud part {i + 1}/{len(groups)}\n\n"
        text += "Read [host runtime](yigit/host-runtime.md) and [part boundaries](CLOUD-README.md).\n\n"
        text += "The complete library spans every part listed in CLOUD-PART.json. This part contains only the modules below.\n"
        text += "Preserved complete entrypoint: [reference only](yigit/complete-host-entrypoint.md); links to other parts are not local files.\n\n"
        for module in module_names:
            rel = f"modules/{module}/MODULE.md"
            text += f"- [{module}]({rel})\n" if rel in payload else f"- {module}: resource segment; entrypoint is in another part.\n"
        payload["SKILL.md"] = text.encode("utf-8")
        payload["CLOUD-PART.json"] = json_bytes({"source_skill": name, "part": i + 1, "part_count": len(groups),
            "parts": part_names, "included_modules": module_names, "all_modules": module_parts,
            "partial_modules": [m for m, _, partial in group if partial]})
        payload["CLOUD-README.md"] = ("# Upload boundaries\n\n"
            "Upload all sibling parts to cover the complete library. This is not the full library by itself. "
            "Cross-module references may belong to another skill part; consult CLOUD-PART.json and load that skill when the host supports it. "
            "Never report an unbundled file as locally available. If the host cannot resolve a cross-part dependency, "
            "use the complete source bundle in an appropriate local environment or ask for the needed file. "
            "A module marked partial requires its sibling resource segments; it is not independently complete. "
            "All source bytes remain in the complete host source ZIP and are accounted for in the coverage manifest.\n").encode("utf-8")
        if len(payload) > limit:
            raise ValueError("Cloud partition exceeded limit")
        validate_skill(part_name, payload, short=True)
        for rel, item in coverage.items():
            location = "yigit/complete-host-entrypoint.md" if rel == "SKILL.md" else rel
            if location in payload and digest(payload[location]) == item["sha256"]:
                item["locations"].append(f"{part_name}/{location}")
        parts[part_name] = payload
    if any(not item["locations"] for item in coverage.values()):
        raise ValueError("Incomplete cloud source coverage")
    return parts, {"source_skill": name, "split": True, "parts": part_names,
                   "modules": module_parts, "files": coverage}


def build_desktop_mapping(gpt, claude, opencode, release):
    if set(gpt) != set(claude) or set(gpt) != set(opencode):
        raise ValueError("Provider skill sets differ; package all canonical skills")
    result, coverage = {}, {}
    z = lambda m: zip_bytes(m, release["date"])
    result["ChatGPT/yigit-skills-plugin.zip"] = z(plugin_files(gpt, release))
    result["ChatGPT/yigit-skills-full-source.zip"] = z({"skills/" + k: v for k, v in flatten(gpt).items()})
    medical = {n: gpt[n] for n in ("medical-evidence-research", "physio-clinical-copilot") if n in gpt}
    if medical:
        result["ChatGPT/medical-literature-plugin.zip"] = z(plugin_files(medical, release, "medical-literature"))
    result["Claude/yigit-skills-claude-code.zip"] = z(plugin_files(claude, release, provider="claude"))
    result["Claude/yigit-skills-full-source.zip"] = z({"skills/" + k: v for k, v in flatten(claude).items()})
    for name, fs in sorted(claude.items()):
        parts, record = cloud_parts(name, fs)
        coverage[name] = record
        for part, payload in parts.items():
            data = z({part + "/" + rel: b for rel, b in payload.items()})
            validate_zip(data, skill=part, limit=200)
            result[f"Claude/skills/{part}.zip"] = data
    config = {"$schema": "https://opencode.ai/config.json", "skills": ["./skills"]}
    portable = {"skills/" + rel: data for rel, data in flatten(opencode).items()}
    portable["opencode.skills.json"] = json_bytes(config)
    portable["README.md"] = ("# OpenCode portable skills\n\n"
        "Keep this directory together. Merge the skills array in opencode.skills.json into the "
        "appropriate OpenCode v2 config, resolving ./skills relative to that config's directory. "
        "If copying the snippet elsewhere, adjust the relative path. Select this complete generated source "
        "instead of duplicate installed copies. This bundle does not enable tools, MCP servers or accounts.\n").encode("utf-8")
    result["OpenCode/yigit-skills-portable.zip"] = z(portable)
    result["OpenCode/opencode.skills.json"] = json_bytes(config)
    result["Claude/coverage-manifest.json"] = json_bytes(coverage)
    counts = {"canonical_skills": len(gpt), "claude_upload_zips": sum(len(r["parts"]) for r in coverage.values()),
              "claude_max_files_per_zip": 200}
    common = ("# Complete generated skill packages\n\n"
        "Edit only the canonical master or generators; never hand-edit generated/installed copies. "
        "Full source is included for every host. Local sync does not upload, install or enable a cloud-account skill. "
        "Account features and supported import flows vary; verify installation and enabled state in that account.\n\n"
        "Personal paths in preserved upstream examples must be resolved to the current environment. "
        "UI/desktop/browser tools, secrets, network and paid services are conditional capabilities; this package grants none.\n")
    result["ChatGPT/README.md"] = (common + "\n## ChatGPT / Codex\n\n"
        "yigit-skills-plugin.zip contains the full plugin (root plugin.json with Agent Plugins schema, "
        "legacy .codex-plugin fallback, complete skills). Use the supported plugin import/creator flow in your account. "
        "The full-source ZIP is also available for inspection/local installation. The medical plugin is an optional "
        "two-skill alternative; do not enable it alongside the same skills in the full plugin.\n\n"
        + DOCS["openai_plugin"] + "\n").encode("utf-8")
    result["Claude/README.md"] = (common + "\n## Claude uploads\n\n"
        "Upload each ZIP in skills/ separately through the supported custom-skill uploader. Each has exactly "
        "one skill folder with SKILL.md at its root, at most 200 files and a description at most 200 characters. "
        "200 characters is the documented Claude.ai uploader contract; Claude Code/API documentation permits longer "
        "descriptions. The conservative 200-file cap is an uploader constraint, not a limit on the full source. "
        "Oversized modular libraries are deterministically split at module boundaries; upload EVERY numbered part. "
        "coverage-manifest.json accounts for every source file/hash and module. A part advertises only its actual "
        "contents. For cross-part dependencies follow CLOUD-README.md.\n\n"
        "yigit-skills-claude-code.zip is the complete local Claude Code plugin; yigit-skills-full-source.zip "
        "contains the complete unsplit source. Choose local or account copies to avoid duplicate activation.\n\n"
        + DOCS["claude_upload"] + "\n" + DOCS["claude_plugin"] + "\n").encode("utf-8")
    result["OpenCode/README.md"] = common.encode("utf-8") + portable["README.md"]
    # Gemini: CLI (Agent Skills folders) + app (web) per-skill upload copies.
    result["Gemini/gemini-cli-skills.zip"] = z({"skills/" + rel: data for rel, data in flatten(gpt).items()})
    for name, fs in sorted(gpt.items()):
        result[f"Gemini/skills/{name}.zip"] = z({name + "/" + rel: b for rel, b in gemini_web_payload(name, fs).items()})
    result["Gemini/README.md"] = (common + "\n## Gemini\n\n"
        "**Gemini CLI:** unzip gemini-cli-skills.zip and copy each folder under skills/ to ~/.gemini/skills/ "
        "(user scope) or <project>/.gemini/skills/ (workspace scope); check with /skills list. Install one copy only.\n\n"
        "**Gemini app (web, Skills):** unzip a file from skills/ and upload the extracted folder (SKILL.md at its root) "
        "in the Skills section. The app accepts md/txt/py/sh/json/yaml/csv/pdf/jpg/png files up to 100 MB in total; "
        "files of other types are listed in GEMINI-UNSUPPORTED-FILES.md inside that skill and stay available in the "
        "CLI/full-source ZIP. Skills availability in the Gemini app rolls out per account; verify it in your account.\n\n"
        + DOCS["gemini_cli_skills"] + "\n").encode("utf-8")
    # DeepSeek Harness reads the canonical master directly (profile agentsHome); the ZIP is for other machines.
    result["DeepSeek-Harness/yigit-skills-portable.zip"] = z({"skills/" + rel: data for rel, data in flatten(gpt).items()})
    result["DeepSeek-Harness/README.md"] = (common + "\n## DeepSeek Harness\n\n"
        "On this computer DeepSeek Harness reads the canonical master folder directly through its skill-filesystem "
        "agentsHome setting, so no copy is needed and none should be installed next to it (duplicates confuse routing). "
        "Use yigit-skills-portable.zip only on another machine: extract it and point the harness skill folder at skills/. "
        "If the model does not see a skill catalog, ask it to read the SKILL.md of the needed skill by path.\n").encode("utf-8")
    result["build-manifest.json"] = json_bytes({"format": 1, "release": release, "counts": counts,
        "documentation": DOCS, "files": {k: digest(v) for k, v in sorted(result.items())}})
    return result


def build_desktop(dest, gpt, claude, opencode, release, *, dry=False, adopt=None, backup=None):
    mapping = build_desktop_mapping(gpt, claude, opencode, release)
    return sync_mapping(dest, mapping, check=dry, manifest=DESKTOP_MANIFEST, adopt=adopt, backup=backup)


def build_compact(dest, gpt, gnames, claude, cnames, dry=False, sample=False, *, opencode=None, release=None):
    """Compatibility wrapper; callers must now provide OpenCode and release data."""
    if sample or opencode is None or release is None:
        raise ValueError("Use build_desktop with all three complete renderings and central release metadata")
    if set(gnames) != set(cnames):
        raise ValueError("Provider skill sets differ")
    return build_desktop(dest, {n: files(Path(gpt) / n) for n in gnames},
                         {n: files(Path(claude) / n) for n in cnames}, opencode, release, dry=dry)
