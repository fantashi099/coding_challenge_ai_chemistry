import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generator import VideoGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a narrated chemistry explainer video")
    parser.add_argument("--question", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(VideoGenerator().generate(args.question, args.output))


if __name__ == "__main__":
    main()
