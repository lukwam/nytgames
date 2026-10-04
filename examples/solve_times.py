"""Your crossword solve times by weekday and by constructor.

Needs your NYT-S cookie in the NYT_COOKIES environment variable, for example
NYT_COOKIES="NYT-S=...".

    pip install nytimes-games
    NYT_COOKIES="NYT-S=..." python solve_times.py --days 180
"""
import argparse
import collections
import datetime
import os
import statistics

from nytgames import NYTGamesClient


def minutes(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=180, help="How many days back to look.")
    args = parser.parse_args()

    client = NYTGamesClient(cookies=os.environ["NYT_COOKIES"])
    end = datetime.date.today()
    start = end - datetime.timedelta(days=args.days - 1)

    # NYT's list allows about 90 days per request; game states allow 30 IDs.
    listing = []
    window = start
    while window <= end:
        window_end = min(window + datetime.timedelta(days=89), end)
        listing += client.crossword_puzzles("daily", date_start=window.isoformat(),
                                            date_end=window_end.isoformat()).results
        window = window_end + datetime.timedelta(days=1)
    solved = [p for p in listing if p.solved]
    ids = [p.puzzle_id for p in solved]
    seconds = {}
    for i in range(0, len(ids), 30):
        for state in client.crossword_game(ids[i:i + 30], "daily").states:
            seconds[int(state.puzzle_id)] = state.game_data.playTimeSeconds

    by_weekday = collections.defaultdict(list)
    by_author = collections.defaultdict(list)
    for p in solved:
        if seconds.get(p.puzzle_id):
            by_weekday[datetime.date.fromisoformat(p.print_date).strftime("%A")].append(seconds[p.puzzle_id])
            by_author[p.author].append(seconds[p.puzzle_id])

    print(f"{len(solved)} dailies solved in the last {args.days} days\n\nBy weekday (median):")
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if by_weekday[day]:
            print(f"  {day:<10} {minutes(statistics.median(by_weekday[day])):>6}  ({len(by_weekday[day])} puzzles)")
    print("\nConstructors you've solved most often (median time):")
    for author, times in sorted(by_author.items(), key=lambda item: -len(item[1]))[:10]:
        print(f"  {author:<35} {minutes(statistics.median(times)):>6}  ({len(times)} puzzles)")


if __name__ == "__main__":
    main()
