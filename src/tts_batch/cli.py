"""Command-line entry point."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .engines import EngineError, get_engine, list_espeak_voices
from .render import render
from .script import Speech, parse_script


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tts-batch", description="Render scripts with local TTS")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--list-voices", action="store_true", help="List available voices for espeak"
    )
    commands = parser.add_subparsers(dest="command")
    command = commands.add_parser("render", help="Write sentence WAVs, narration and timing")
    command.add_argument("script", type=Path, nargs="?", default=None)
    command.add_argument("-o", "--output", type=Path, default=None)
    command.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse script and print segments without calling an engine",
    )
    command.add_argument(
        "--list-voices", action="store_true", help="List available voices for espeak"
    )
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
        if getattr(args, "list_voices", False):
            sys.stdout.write(list_espeak_voices())
            return 0

        if args.command != "render":
            parser.print_help(sys.stderr)
            return 2

        if args.script is None:
            raise ValueError("Script argument is required")

        if args.script.suffix.lower() not in {".md", ".txt"}:
            raise ValueError("Script must be a .txt or .md file")
        script = args.script.read_text(encoding="utf-8-sig")

        if args.dry_run:
            events = parse_script(script, voice=args.voice, speed=args.speed)
            segments = [e for e in events if isinstance(e, Speech)]
            if not segments:
                raise ValueError("Script contains no speech")
            for i, seg in enumerate(segments, 1):
                voice_str = seg.voice if seg.voice else "(default)"
                print(f"Segment {i:04d} [voice: {voice_str}, speed: {seg.speed:.2f}]: {seg.text}")
            return 0

        if args.output is None:
            raise ValueError("Output directory (-o/--output) is required")

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
