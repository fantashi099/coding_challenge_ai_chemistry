import argparse
from pathlib import Path

from src.generator import VideoGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a narrated chemistry explainer video")
    parser.add_argument("--question", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(VideoGenerator().generate(args.question, args.output))


if __name__ == "__main__":
    main()
