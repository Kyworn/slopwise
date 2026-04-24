# slopwise

Semantic firmware diff via multi-agent LLM analysis.

## Problem

Binary diff tools (BinDiff, Diaphora, radiff2) show *what* changed between two binaries but leave "why" to manual reverse-engineering. Security research, CVE hunting in OTA updates, and vendor blob audits all need human-readable explanations of semantic changes, not just byte diffs.

## How it works

1. **Decompile**: Ghidra headless disassembles both binaries, outputs function source.
2. **Match**: Fuzzy-match functions across versions (name, signature, CFG similarity).
3. **Analyze**: Per-function LLM agent describes what changed and categorizes it (bugfix, feature, refactor, security tweak).
4. **Cluster**: Second agent groups related changes by theme (e.g., "all crypto updates", "all bounds checks").
5. **Report**: Markdown output with summary, risk flagging, per-change context.

## Provider-agnostic

Any LLM backend works: Claude, GPT-4, Gemini, Ollama, vLLM, OpenRouter, or local inference. Configure via `config.yaml`—no vendor lock-in.

## Status

Pre-alpha. Scaffold only. Core pipeline (decompile, diff, agents) not yet implemented.

## Quick start (intended UX)

```bash
slopwise diff libfoo_v1.so libfoo_v2.so --config config.yaml -o report.md
```

## Roadmap

- MVP: ELF binary pair diffing
- OTA payload.bin / Android A/B OTA support
- squashfs / EROFS recursive diff
- BinDiff `.gdb` import for pre-computed function matching

## License

MIT
