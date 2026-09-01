import argparse


def _quality_list(value: str) -> list[str]:
    qualities = value.split(",")
    for q in qualities:
        if q not in ("low", "medium", "high"):
            raise argparse.ArgumentTypeError(f"invalid quality: {q!r} (choose from low, medium, high)")
    return qualities


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Terminal client for downloading Movies and TV shows from The Pirate Bay.",
    )
    parser.add_argument(
        '-h',
        '--help',
        help='Show this message and exit',
        action='help'
    )
    parser.add_argument(
        "-c",
        "--category",
        choices=["movie", "show"],
        help="Category of the media"
    )
    parser.add_argument(
        "-s",
        "--search",
        dest="query",
        help="Search query to search for"
    )
    parser.add_argument(
        "-q",
        "--quality",
        dest="qualities",
        type=_quality_list,
        help="Qualities of the media to include (comma-separated: low,medium,high)"
    )
    return parser.parse_args(argv)
