<p align="center">
  <img src="assets/banner.svg" alt="Yiğit Investment Copilot — an AI research desk for Borsa İstanbul" width="100%">
</p>

<p align="center"><a href="README.md">Türkçe</a> · <a href="#download">Download</a> · <a href="#install">Install</a> · <a href="#use">Use</a> · <a href="DISCLAIMER.md">Disclaimer</a></p>

# Yiğit Investment Copilot

An Agent Skill for ChatGPT, Claude, OpenCode and Codex that works like a disciplined equity research desk for **Borsa İstanbul (BIST)** — and handles funds, global stocks/ETFs, crypto, warrants and VİOP context too.

It scans **every listed BIST stock**, ranks candidates for a stated horizon across 11 lanes (momentum, trend, setup, reversal, value, quality, growth, low risk, catalyst, liquidity), builds evidence packs (KAP disclosures, quarterly statements, technical state, probability ranges), checks the **market regime**, runs an **investment committee** (bear case first, then bull, investor lenses, risk committee), an independent **red team** and a **pre-trade gate**, and only then writes a **trade plan** (entry, structure/ATR stop, R-multiple targets, position size, gap scenario, trailing and time stops). Forecasts go into a hash-chained ledger and are scored when they mature.

> **Research and decision support only — not investment advice, no guaranteed returns, never places orders.**

## Download

| Platform | Package | Where |
|---|---|---|
| ChatGPT (web/mobile/desktop) | [yigit-investment-copilot-chatgpt.zip](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest/download/yigit-investment-copilot-chatgpt.zip) | Skills → Create → Upload |
| Claude (claude.ai + Claude Code) | [yigit-investment-copilot-claude.zip](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest/download/yigit-investment-copilot-claude.zip) | Customize → Skills → Upload, or `~/.claude/skills/` |
| OpenCode | [yigit-investment-copilot-opencode.zip](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest/download/yigit-investment-copilot-opencode.zip) | `~/.config/opencode/` (skill + agent + commands) |
| Codex CLI / ChatGPT desktop | same as the ChatGPT package | `~/.agents/skills/` |
| All in one | [yigit-investment-copilot-all-in-one.zip](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest/download/yigit-investment-copilot-all-in-one.zip) | every package + installers + docs |

Checksums: [SHA256SUMS.txt](https://github.com/yigityildiz0/yigit-investment-copilot/releases/latest/download/SHA256SUMS.txt)

## Install

- **ChatGPT:** upload the ChatGPT ZIP in Skills. The ChatGPT sandbox usually has no internet, so the skill browses primary sources or maps a screener CSV you upload (`map_export.py`) and runs the scan offline.
- **claude.ai:** enable Code execution, then Customize → Skills → Upload the Claude ZIP.
- **Claude Code / Codex / OpenCode:** `powershell -ExecutionPolicy Bypass -File install/install.ps1 -Claude -Codex -OpenCodeExtras` (Windows) or `bash install/install.sh --claude --codex --opencode-extras`. OpenCode also reads `~/.claude/skills` and `~/.agents/skills`, so add only the agent and commands when the skill is already installed there.

Scripts need **Python 3.9+** and use only the standard library.

## Use

Ask naturally ("Find the BIST stocks with the best 3-month setup", "Should I buy THYAO for one month?", "Where should my stop be?", "How is the market?", "Does momentum work on BIST? Test it."). On hosts with internet you can also run:

```bash
python scripts/borsa.py pipeline --horizon 3m
python scripts/borsa.py ticker THYAO --horizon 1m
python scripts/borsa.py regime
python scripts/borsa.py kap --days 3
```

## Data

TradingView screener endpoint (unofficial, delayed; screening only), Yahoo Finance (unofficial; corporate actions repaired with the BIST ±10% limit rule), KAP public JSON (primary content), İş Yatırım statements (secondary), TCMB FX (official). Optional connectors: borsa-mcp, OpenBB MCP. Every number is reported with its source and time.

## Design principles

Evidence before opinion · point-in-time honesty · probabilities, not promises · process over picks · risk first · decision support only.

## License

[MIT](LICENSE) · by [Yiğit Yıldız](https://github.com/yigityildiz0) · see [DISCLAIMER.md](DISCLAIMER.md).
