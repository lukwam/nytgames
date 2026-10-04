"""Spelling Bee hints."""
import collections
from typing import Any
from typing import Mapping

from nytgames.models import SpellingBeeGameDay


def spelling_bee_hints(puzzle: SpellingBeeGameDay | Mapping[str, Any]) -> dict:
    """Return Spelling Bee Forum style hints for a puzzle.

    `puzzle` can be a SpellingBeeGameDay or a dict with the same fields.
    The `perfect` and `bingo` keys are only included when they apply, matching
    the forum hints.
    """
    if isinstance(puzzle, SpellingBeeGameDay):
        puzzle = puzzle.model_dump()
    answers = [answer.lower() for answer in puzzle["answers"]]
    letters = puzzle["validLetters"]
    pangrams = [answer for answer in answers if set(letters) <= set(answer)]
    lengths = sorted({len(answer) for answer in answers})

    counts = {"lengths": lengths, "letters": {}, "totals": []}
    for letter in sorted({answer[0] for answer in answers}):
        row = [len([a for a in answers if a[0] == letter and len(a) == n]) for n in lengths]
        counts["letters"][letter] = [*row, sum(row)]
    counts["totals"] = [*[len([a for a in answers if len(a) == n]) for n in lengths], len(answers)]

    hints = {
        "counts": counts,
        "date": puzzle["printDate"],
        "letters": letters,
        "pairs": dict(sorted(collections.Counter(answer[:2] for answer in answers).items())),
        "pangrams": len(pangrams),
        "points": sum(
            (1 if len(a) == 4 else len(a)) + (7 if a in pangrams else 0) for a in answers
        ),
        "words": len(answers),
    }
    perfect = len([pangram for pangram in pangrams if len(pangram) == len(letters)])
    if perfect:
        hints["perfect"] = perfect
    if {answer[0] for answer in answers} == set(letters):
        hints["bingo"] = True
    return hints
