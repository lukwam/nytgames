"""Find answers that repeat across recent crosswords, and how they were clued.

Uses the games archive to list the puzzles, then each puzzle's entries.

    pip install nytimes-games
    python clue_reuse.py --days 30 --type mini

Prints answers (spoilers) from the puzzles in the range.
"""
import argparse
import collections
import datetime
import time

from nytgames import NYTGamesClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30, help="How many days back to look.")
    parser.add_argument("--type", default="mini", choices=["daily", "mini", "midi"])
    parser.add_argument("--min-length", type=int, default=3, help="Ignore shorter answers.")
    args = parser.parse_args()

    client = NYTGamesClient()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=args.days - 1)
    puzzles = client.archive(f"crossword_{args.type}", start.isoformat(), end.isoformat())

    clues = collections.defaultdict(list)
    for listed in puzzles:
        puzzle = client.crossword(args.type, listed.print_date)
        for entry in puzzle.entries():
            if len(entry.answer) >= args.min_length:
                clues[entry.answer].append((listed.print_date, entry.id, entry.clue))
        time.sleep(0.2)  # be polite to NYT

    repeated = sorted(((answer, uses) for answer, uses in clues.items() if len(uses) > 1),
                      key=lambda item: (-len(item[1]), item[0]))
    print(f"{len(puzzles)} {args.type} crosswords, {len(clues)} different answers, "
          f"{len(repeated)} used more than once\n")
    for answer, uses in repeated[:15]:
        print(f"{answer} ({len(uses)} times)")
        for date, entry_id, clue in uses:
            print(f"  {date} {entry_id:<10} {clue}")


if __name__ == "__main__":
    main()
