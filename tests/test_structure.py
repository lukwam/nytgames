"""Puzzle structure tests, using the made-up crossword from test_formats."""
from nytgames.models import ConnectionsPuzzle
from nytgames.models import StrandsPuzzle
from tests.test_formats import puzzle


def test_squares():
    squares = puzzle().squares()
    assert len(squares) == 9
    assert squares[4].block and not squares[0].block
    assert (squares[1].row, squares[1].col, squares[1].circled) == (0, 1, True)
    assert squares[7].shaded
    assert squares[8].rebus and squares[8].answer == "HH" and squares[8].other_answers == ("H",)
    assert squares[0].label == 1


def test_entries():
    entries = {e.id: e for e in puzzle().entries()}
    assert list(entries) == ["1-Across", "3-Across", "1-Down", "2-Down"]

    across = entries["3-Across"]
    assert (across.number, across.direction, across.clue) == (3, "Across", "Last row…")
    assert across.answer == "FGHH" and across.length == 3 and across.rebus
    assert across.coordinates == ((2, 0), (2, 1), (2, 2))
    assert across.crossings == ("1-Down", "2-Down")
    assert entries["1-Down"].answer == "ADF" and not entries["1-Down"].rebus


def test_special_entries():
    p = puzzle(**{
        "body.0.cells.0.label": "CW",
        "body.0.clues": [*puzzle().model_dump()["body"][0]["clues"],
                         {"cells": [0, 1, 2, 2, 5, 8], "direction": "Around", "relatives": [0],
                          "text": [{"plain": "Around the corner"}]}],
        "body.0.clueLists": [{"name": "Across", "clues": [0, 1]}, {"name": "Down", "clues": [2, 3]},
                             {"name": "Around", "clues": [4]}],
    })
    assert p.squares()[0].label == "CW"
    around = p.entries()[-1]
    assert (around.id, around.number, around.label) == ("Around-1", None, None)
    assert around.cells == (0, 1, 2, 5, 8)  # the repeated corner square is dropped
    assert around.answer == "ABCEHH"
    assert around.references == ("1-Across",)
    assert "Around-1" in {e.id: e for e in p.entries()}["1-Across"].crossings


def test_strands_words():
    strands = StrandsPuzzle(
        id=1, clue="Gone fishing", editor="Ed", printDate="2025-06-12", solutions=["HOOK"],
        spangram="BAIT", startingBoard=["HOOK", "BAIT"], themeCoords={"HOOK": [[0, 0], [0, 1], [0, 2], [0, 3]]},
        spangramCoords=[[1, 0], [1, 1], [1, 2], [1, 3]],
    )
    words = strands.words()
    assert [(w.word, w.spangram) for w in words] == [("HOOK", False), ("BAIT", True)]
    assert words[1].path == ((1, 0), (1, 1), (1, 2), (1, 3))


def test_connections_board():
    connections = ConnectionsPuzzle(id=1, status="OK", print_date="2025-06-12", editor="Ed", categories=[
        {"title": f"G{g}", "cards": [{"content": f"W{g}{i}", "position": 15 - (g * 4 + i)} for i in range(4)]}
        for g in range(4)
    ])
    board = connections.board()
    assert [card.text for card in board[0]] == ["W33", "W32", "W31", "W30"]
    assert len(board) == 4 and all(len(row) == 4 for row in board)
