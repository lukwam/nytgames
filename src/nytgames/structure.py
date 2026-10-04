"""Puzzle structure: crossword squares and entries, and Strands word paths.

Use the methods on the models: ``CrosswordPuzzle.squares()``,
``CrosswordPuzzle.entries()``, ``StrandsPuzzle.words()`` and
``ConnectionsPuzzle.board()``. Unlike the file exports, these keep special
puzzles as they are: text square labels, extra clue lists such as "Around",
and entries that turn corners.
"""
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from nytgames.models import CrosswordPuzzle
    from nytgames.models import StrandsPuzzle

CIRCLED = 2
SHADED = 3


@dataclass(frozen=True)
class Square:
    """One square of a crossword grid."""

    index: int
    row: int
    col: int
    block: bool
    #: The square's answer; more than one letter for a rebus.
    answer: str = ""
    #: Other accepted answers for a rebus square, e.g. its first letter.
    other_answers: tuple[str, ...] = ()
    #: Usually the clue number; some special puzzles use text such as "CW".
    label: int | str | None = None
    circled: bool = False
    shaded: bool = False

    @property
    def rebus(self) -> bool:
        return len(self.answer) > 1


@dataclass(frozen=True)
class Entry:
    """One crossword entry: a clue and the squares of its answer."""

    #: For example "17-Across". Unnumbered clues use their position, e.g. "Around-1".
    id: str
    number: int | None
    label: str | None
    direction: str
    clue: str
    #: The full answer, with rebus squares' full answers, e.g. "CIRCULAR".
    answer: str
    #: Square indexes in order. Some special clues turn corners.
    cells: tuple[int, ...]
    #: (row, col) of each square, from 0.
    coordinates: tuple[tuple[int, int], ...]
    #: IDs of the entries sharing a square with this one.
    crossings: tuple[str, ...] = field(default=())
    #: IDs of the entries this clue refers to, e.g. "See 17-Across".
    references: tuple[str, ...] = field(default=())

    @property
    def length(self) -> int:
        """The number of squares."""
        return len(self.cells)

    @property
    def rebus(self) -> bool:
        """Whether the answer is longer than its squares."""
        return len(self.answer) > len(self.cells)


def squares(puzzle: "CrosswordPuzzle") -> list[Square]:
    """Return every square of a crossword, blocks included, in reading order."""
    body = puzzle.body[0]
    width = body.dimensions["width"]
    result = []
    for index, cell in enumerate(body.cells):
        row, col = divmod(index, width)
        if not cell.type:
            result.append(Square(index, row, col, block=True))
            continue
        result.append(Square(
            index, row, col, block=False,
            answer=cell.answer or "",
            other_answers=tuple((cell.moreAnswers or {}).get("valid", [])),
            label=cell.label,
            circled=cell.type == CIRCLED,
            shaded=cell.type == SHADED,
        ))
    return result


def entries(puzzle: "CrosswordPuzzle") -> list[Entry]:
    """Return every entry of a crossword, in clue list order."""
    body = puzzle.body[0]
    width = body.dimensions["width"]
    grid = squares(puzzle)

    ids = {}
    for clue_list in body.clueLists:
        for position, index in enumerate(clue_list.clues, start=1):
            clue = body.clues[index]
            ids[index] = f"{clue.label}-{clue_list.name}" if clue.label else f"{clue_list.name}-{position}"

    # NYT repeats the corner square of clues that turn a corner.
    paths = {}
    for clue_list in body.clueLists:
        for index in clue_list.clues:
            cells = body.clues[index].cells
            paths[index] = tuple(c for n, c in enumerate(cells) if n == 0 or c != cells[n - 1])
    by_cell: dict[int, list[int]] = {}
    for index, cells in paths.items():
        for cell in cells:
            by_cell.setdefault(cell, []).append(index)

    result = []
    for clue_list in body.clueLists:
        for index in clue_list.clues:
            clue = body.clues[index]
            cells = paths[index]
            crossings = dict.fromkeys(
                ids[other] for cell in cells for other in by_cell[cell] if other != index
            )
            references = dict.fromkeys(ids[r] for r in (clue.relatives or []) if r in ids)
            result.append(Entry(
                id=ids[index],
                number=int(clue.label) if (clue.label or "").isdigit() else None,
                label=clue.label,
                direction=clue_list.name,
                clue="".join(part.get("plain", "") for part in clue.text),
                answer="".join(grid[c].answer for c in cells),
                cells=cells,
                coordinates=tuple(divmod(c, width) for c in cells),
                crossings=tuple(crossings),
                references=tuple(references),
            ))
    return result


@dataclass(frozen=True)
class StrandsWord:
    """A Strands theme word or the spangram, with its path through the board."""

    word: str
    #: (row, col) of each letter, from 0, in order.
    path: tuple[tuple[int, int], ...]
    spangram: bool = False


def strands_words(puzzle: "StrandsPuzzle") -> list[StrandsWord]:
    """Return the theme words and the spangram with their paths."""
    words = [StrandsWord(word, tuple((r, c) for r, c in path))
             for word, path in puzzle.themeCoords.items()]
    if puzzle.spangramCoords:
        words.append(StrandsWord(puzzle.spangram, tuple((r, c) for r, c in puzzle.spangramCoords),
                                 spangram=True))
    return words
