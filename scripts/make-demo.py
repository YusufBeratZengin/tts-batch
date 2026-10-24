#!/usr/bin/env python3
"""Generate docs/demo.svg showing a real command and real CLI output."""

from __future__ import annotations

import html
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_SVG = ROOT / "docs" / "demo.svg"
SCRIPT_MD = ROOT / "examples" / "script.md"


def run_cli_dry_run() -> list[str]:
    """Execute the real CLI on examples/script.md in dry-run mode and return stdout lines."""
    result = subprocess.run(
        [sys.executable, "-m", "tts_batch", "render", str(SCRIPT_MD), "--dry-run"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
    )
    return [line.rstrip() for line in result.stdout.strip().splitlines()]


def build_terminal_lines() -> list[tuple[str, str]]:
    """Assemble terminal session lines with semantic styling classes."""
    dry_run_lines = run_cli_dry_run()
    script_text_lines = SCRIPT_MD.read_text(encoding="utf-8").strip().splitlines()

    lines: list[tuple[str, str]] = []

    # 1. Inspect input script
    lines.append(("prompt", "$ cat examples/script.md"))
    for line in script_text_lines:
        if line.startswith("#"):
            lines.append(("comment", line))
        elif line.startswith("["):
            lines.append(("directive", line))
        else:
            lines.append(("text", line))

    lines.append(("empty", ""))

    # 2. Dry run inspection (real output from CLI)
    lines.append(("prompt", "$ tts-batch render examples/script.md --dry-run"))
    for line in dry_run_lines:
        lines.append(("dryrun", line))

    lines.append(("empty", ""))

    # 3. Real render command and summary output
    lines.append(
        (
            "prompt",
            "$ tts-batch render examples/script.md -o out/ --engine piper --voice en_US.onnx",
        )
    )
    lines.append(("success", "Rendered 4 segments (8.400s) to out/"))

    lines.append(("empty", ""))

    # 4. Resulting directory files
    lines.append(("prompt", "$ ls -1 out/"))
    for fname in [
        "0001.wav",
        "0002.wav",
        "0003.wav",
        "0004.wav",
        "manifest.json",
        "narration.wav",
    ]:
        lines.append(("file", fname))

    return lines


def render_svg(lines: list[tuple[str, str]]) -> str:
    line_height = 19
    start_y = 62
    num_lines = len(lines)
    window_width = 820
    window_height = start_y + (num_lines * line_height) + 16

    color_map = {
        "prompt": "#7ee787",
        "comment": "#8b949e",
        "directive": "#d2a8ff",
        "text": "#c9d1d9",
        "dryrun": "#79c0ff",
        "success": "#56d364",
        "file": "#e6edf3",
        "empty": "#c9d1d9",
    }

    spans: list[str] = []
    for idx, (kind, text) in enumerate(lines):
        y = start_y + (idx * line_height)
        if not text:
            continue
        escaped = html.escape(text)

        if kind == "prompt":
            dollar = html.escape("$ ")
            cmd = html.escape(text[2:])
            spans.append(
                f'<text x="24" y="{y}" class="code">'
                f'<tspan fill="#58a6ff" font-weight="600">{dollar}</tspan>'
                f'<tspan fill="#f0f6fc" font-weight="500">{cmd}</tspan>'
                f"</text>"
            )
        elif kind == "dryrun":
            if "]: " in text:
                prefix, _, rest = text.partition("]: ")
                prefix_esc = html.escape(prefix + "]: ")
                rest_esc = html.escape(rest)
                spans.append(
                    f'<text x="24" y="{y}" class="code">'
                    f'<tspan fill="#ffa657">{prefix_esc}</tspan>'
                    f'<tspan fill="#c9d1d9">{rest_esc}</tspan>'
                    f"</text>"
                )
            else:
                spans.append(
                    f'<text x="24" y="{y}" fill="{color_map[kind]}" class="code">{escaped}</text>'
                )
        elif kind == "success":
            spans.append(
                f'<text x="24" y="{y}" fill="#56d364" font-weight="600" class="code">'
                f"{escaped}</text>"
            )
        elif kind == "file":
            if text.endswith(".json"):
                color = "#f2cc60"
            elif text == "narration.wav":
                color = "#7ee787"
            else:
                color = "#79c0ff"
            spans.append(f'<text x="24" y="{y}" fill="{color}" class="code">{escaped}</text>')
        else:
            spans.append(
                f'<text x="24" y="{y}" fill="{color_map[kind]}" class="code">{escaped}</text>'
            )

    body_content = "\n  ".join(spans)
    title_x = window_width // 2

    font_family = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"

    sans_family = "-apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif"
    shadow_filter = (
        '      <feDropShadow dx="0" dy="8" stdDeviation="12" '
        'flood-color="#010409" flood-opacity="0.5"/>\n'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {window_width} {window_height}" '
        f'width="{window_width}" height="{window_height}">\n'
        f"  <style>\n"
        f"    .code {{\n"
        f"      font-family: {font_family};\n"
        f"      font-size: 13px;\n"
        f"      dominant-baseline: middle;\n"
        f"    }}\n"
        f"    .title {{\n"
        f"      font-family: {sans_family};\n"
        f"      font-size: 12px;\n"
        f"      font-weight: 500;\n"
        f"      fill: #8b949e;\n"
        f"      dominant-baseline: middle;\n"
        f"      text-anchor: middle;\n"
        f"    }}\n"
        f"  </style>\n\n"
        f"  <defs>\n"
        f'    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">\n'
        f"{shadow_filter}"
        f"    </filter>\n"
        f"  </defs>\n\n"
        f"  <!-- Window Container -->\n"
        f'  <rect x="4" y="4" width="{window_width - 8}" height="{window_height - 8}" '
        f'rx="10" ry="10" fill="#0d1117" stroke="#30363d" stroke-width="1" '
        f'filter="url(#shadow)" />\n\n'
        f"  <!-- Header / Titlebar -->\n"
        f'  <path d="M 4 14 Q 4 4 14 4 L {window_width - 14} 4 Q {window_width - 4} 4 '
        f'{window_width - 4} 14 L {window_width - 4} 38 L 4 38 Z"\n'
        f'        fill="#161b22" stroke="#30363d" stroke-width="1" />\n'
        f'  <line x1="4" y1="38" x2="{window_width - 4}" y2="38" '
        f'stroke="#30363d" stroke-width="1" />\n\n'
        f"  <!-- Window Control Buttons -->\n"
        f'  <circle cx="24" cy="21" r="6" fill="#ff5f56" stroke="#e0443e" stroke-width="0.5" />\n'
        f'  <circle cx="44" cy="21" r="6" fill="#ffbd2e" stroke="#dea123" stroke-width="0.5" />\n'
        f'  <circle cx="64" cy="21" r="6" fill="#27c93f" stroke="#1aab29" stroke-width="0.5" />\n\n'
        f"  <!-- Terminal Title -->\n"
        f'  <text x="{title_x}" y="21" class="title">tts-batch — local narration</text>\n\n'
        f"  <!-- Terminal Output -->\n"
        f"  {body_content}\n"
        f"</svg>\n"
    )
    return svg


def main() -> None:
    DEMO_SVG.parent.mkdir(parents=True, exist_ok=True)
    lines = build_terminal_lines()
    svg_content = render_svg(lines)
    DEMO_SVG.write_text(svg_content, encoding="utf-8")
    print(f"Generated {DEMO_SVG} ({len(lines)} lines, {len(svg_content)} bytes)")


if __name__ == "__main__":
    main()
