<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <img src="assets/hero-light.svg" width="1280" alt="Investment Research Copilot — clear questions, repeatable workflows, reviewable results">
</picture>

# Investment Research Copilot

[English](README.md) · [Türkçe](README.tr.md)

![Edition](https://img.shields.io/badge/edition-2026.10.14.2-0f6e8c) [![Validate](https://github.com/yigityildiz0/yigit-investment-copilot/actions/workflows/validate.yml/badge.svg)](https://github.com/yigityildiz0/yigit-investment-copilot/actions/workflows/validate.yml) [![Release](https://img.shields.io/github/v/release/yigityildiz0/yigit-investment-copilot?display_name=tag&sort=date)](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest) ![Skills](https://img.shields.io/badge/skills-1-b0303f) ![Languages](https://img.shields.io/badge/EN%20%2B%20TR-guides-e0a43a)

**Investment research workflows for market evidence, scenarios, portfolio risk and decision plans.**

1 maintained entry point. Choose one for the job; do not load the entire library into context.

[Start here](docs/INSTALL.md) · [Browse the catalog](https://yigityildiz0.github.io/universal-ai-skill-library/) · [Downloads](DOWNLOADS.md) · [Maintenance model](MAINTAINING.md)

## New in 2026.10.14.2

- Gemini packages (CLI folders and filtered Gemini app uploads), an installation table for every app and a real GitHub Release with SHA-256 checksums.
- One ZIP per skill for every app, never split into parts; Claude gets grouped bulk-upload ZIPs on the Desktop edition.

## Works with

| App | Package |
|---|---|
| Claude Code | portable folder → ~/.claude/skills |
| Claude.ai | one upload ZIP per skill |
| Codex / ChatGPT desktop | Codex.zip → ~/.codex/skills |
| ChatGPT web | plugin ZIP where the account offers import |
| Gemini CLI / app | ~/.gemini/skills · Skills upload (filtered copy) |
| OpenCode · DeepSeek Harness | portable folder + skills path |

Step-by-step: [Installation](docs/INSTALL.md). A file on disk is not proof of activation; test with one example request.

## Start with the work you want to do

<details open>
<summary><strong>Finance & decisions</strong> · 1</summary>

| Skill | What it helps with |
|---|---|
| [yigit-investment-copilot](docs/skills/yigit-investment-copilot.en.md) | Research BIST, TEFAS and US investments with valuation, scenarios and portfolio-risk checks. |

</details>

## What happens when a skill runs?

~~~mermaid
flowchart LR
 A[Your goal] --> B[Match the skill]
 B --> C[Load relevant module]
 C --> D[Use available tools]
 D --> E[Verify and explain]
~~~

This is the workflow, not a claim that tools ran or every result is verified. Each skill page explains an example request, trigger, mechanics, inputs/outputs and source modules.

## One source. Durable collections.

The canonical source is [Universal AI Skill Library](https://github.com/yigityildiz0/universal-ai-skill-library). Domain repositories are selected views of the same release—not independently edited forks. Existing links and history stay intact.

[All collections / Tüm koleksiyonlar](COLLECTIONS.md) · [Legacy/community resources](LEGACY.md) · [Licenses & provenance](docs/LICENSE-SCOPE.md)

## Honest scope

- Installing a skill does not train a model or connect an account/tool.
- Local files and a web-account import are different; follow the supported host flow.
- No automatic extra billed API or model download.
- The historical community catalog is not counted as maintained or claimed as runtime-tested.
- Source licenses remain attached; no blanket third-party license is assumed.

---
Maintained by [Yigit Yildiz](https://github.com/yigityildiz0) · Source edition 2026.10.14.2
