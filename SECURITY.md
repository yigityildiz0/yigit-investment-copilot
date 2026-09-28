# Security

- The skill is read-only research: it never places orders, never connects to brokerage or wallet accounts and never asks for passwords, API secrets or account numbers.
- Scripts use only the Python standard library and call only the public endpoints documented in `skill/yigit-investment-copilot/modules/market-data-engine/references/data-sources.md`.
- Web pages, KAP disclosures, PDFs and tool outputs are treated as data, never as instructions (prompt-injection guard).
- Review any skill before installing it. Report problems through GitHub Issues; do not post personal financial data there.
