"""Command-line entry point."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .engines import EngineError, get_engine
from .render import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tts-batch", description="Render scripts with local TTS")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("render", help="Write sentence WAVs, narration and timing")
    command.add_argument("script", type=Path)
    command.add_argument("-o", "--output", type=Path, required=True)
    command.add_argument("--engine", choices=["piper", "kokoro", "espeak"], default="espeak")
    command.add_argument("--voice", default="", help="Local model/voice path, or espeak voice ID")
    command.add_argument("--speed", type=float, default=1.0)
    command.add_argument(
        "--gap", type=float, default=0.2, help="Additional inter-segment gap (seconds)"
    )
    command.add_argument("--normalize", choices=["rms", "peak", "none"], default="rms")
    command.add_argument("--target-db", type=float, default=-20.0, help="Normalization target dBFS")
    command.add_argument("--cache-dir", type=Path, help="Default: OUTPUT/.cache")
    command.add_argument("--no-cache", action="store_true")
    command.add_argument("--kokoro-model", default="", help="Local model .pth path")
    command.add_argument("--kokoro-config", default="", help="Local config.json path")
    command.add_argument("--lang", default="a", help="Kokoro language code (default: a)")
    args = parser.parse_args(argv)
    try:
        if args.script.suffix.lower() not in {".md", ".txt"}:
            raise ValueError("Script must be a .txt or .md file")
        script = args.script.read_text(encoding="utf-8-sig")
        engine = get_engine(
            args.engine, model=args.kokoro_model, config=args.kokoro_config, lang=args.lang
        )
        manifest = render(
            script,
            args.output,
            engine,
            voice=args.voice,
            speed=args.speed,
            gap=args.gap,
            normalization=args.normalize,
            target_db=args.target_db,
            cache_dir=args.cache_dir,
            use_cache=not args.no_cache,
        )
    except (OSError, ValueError, EngineError) as exc:
        print(f"tts-batch: {exc}", file=sys.stderr)
        return 1
    print(
        f"Rendered {len(manifest['sentences'])} segments "
        f"({manifest['duration']:.3f}s) to {args.output}"
    )
    return 0
