# slopwise

Semantic firmware diff via multi-agent LLM analysis.

## Problem

Binary diff tools (BinDiff, Diaphora, radiff2) show *what* changed between two binaries but leave "why" to manual reverse-engineering. Security research, CVE hunting in OTA updates, and vendor blob audits all need human-readable explanations of semantic changes, not just byte diffs.

## How it works

The core pipeline operates in 5 steps:

1. **Decompile**: Ghidra (headless, via a robust Java script) disassembles both binaries and outputs function source code.
2. **Match**: A `DiffEngine` exactly matches functions by name and applies fuzzy-matching (difflib) to track renamed functions and structural changes. External pre-computed matches (like BinDiff/Diaphora) are also supported.
3. **Analyze**: A per-function LLM agent (Analyzer) reads the decompiled C diffs, categorizes the change (bugfix, feature, refactor, security tweak), and assesses the risk.
4. **Review**: A peer-review LLM agent (Critic) double-checks the initial analysis to flag hallucinations, missed context, or incorrect security assumptions.
5. **Cluster**: A final agent (Clusterer) groups all individual changes into high-level semantic themes (e.g., "Memory Management", "Authentication Refactoring").
6. **Report**: Generates a comprehensive, human-readable Markdown output with executive summaries, risk metrics, and detailed context.

## Provider-agnostic

Any LLM backend works: Claude, GPT-4, Gemini, Ollama, vLLM, OpenRouter, or **local inference** (like llama.cpp/unsloth servers). Configure via `config.yaml`—no vendor lock-in. 

## Status

**Alpha.** The core multi-agent pipeline is fully functional and tested on real-world libraries (e.g., cJSON) using both cloud providers and local 35B models.

## Quick start

```bash
# Setup the virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Run a semantic diff on two binaries
slopwise diff libfoo_v1.so libfoo_v2.so --config config.yaml -o report.md
```

## Features Implemented

- ✅ **Ghidra Headless Decompilation**: Robust file-based extraction using a custom Java script (bypasses Jython environment issues).
- ✅ **Fuzzy Matching**: Detects function renames using sequence matching on the AST/decompiled code.
- ✅ **Token Management**: Safely truncates massive functions to prevent LLM context limit exhaustion.
- ✅ **Multi-Agent Orchestration**: Asynchronous orchestration of Analyzer, Critic, and Clusterer agents with concurrency limits (`Semaphore`) to protect API quotas.
- ✅ **Firmware Extraction Support**: Base structure in place to utilize `binwalk` and `unsquashfs` automatically.

## Roadmap

- Native BinDiff `.gdb` import for pre-computed function matching
- OTA payload.bin / Android A/B OTA unpacking integration
- squashfs / EROFS recursive diff pipeline

## License

MIT
