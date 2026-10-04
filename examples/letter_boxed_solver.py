"""Find every two-word solution to a Letter Boxed puzzle.

NYT includes the puzzle's whole accepted word list, so the solver doesn't
need a dictionary of its own. A two-word solution is a pair of accepted
words where the second starts with the last letter of the first, and together
they use all 12 letters.

    pip install nytimes-games
    python letter_boxed_solver.py 2026-10-03

Prints spoilers for that day's puzzle.
"""
import argparse
import datetime

from nytgames import NYTGamesClient


def two_word_solutions(dictionary: list[str], letters: set[str]) -> list[tuple[str, str]]:
    """Return every pair of words that chains and uses all the letters."""
    by_first_letter: dict[str, list[str]] = {}
    for word in dictionary:
        by_first_letter.setdefault(word[0], []).append(word)
    return sorted(
        (first, second)
        for first in dictionary
        for second in by_first_letter.get(first[-1], [])
        if set(first) | set(second) == letters
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("date", nargs="?", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    puzzle = NYTGamesClient().letter_boxed(args.date)
    letters = set("".join(puzzle.sides))
    solutions = two_word_solutions(puzzle.dictionary, letters)

    print(f"Letter Boxed {puzzle.printDate}: {' '.join(puzzle.sides)}, par {puzzle.par}")
    print(f"{len(puzzle.dictionary)} accepted words, {len(solutions)} two-word solutions\n")
    for first, second in sorted(solutions, key=lambda pair: len(pair[0]) + len(pair[1]))[:20]:
        print(f"  {first} → {second}")
    official = tuple(puzzle.ourSolution)
    if len(official) == 2:
        print(f"\nNYT's solution {' → '.join(official)} is "
              f"{'one of them' if official in solutions else 'not in the list'}.")


if __name__ == "__main__":
    main()
