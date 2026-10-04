# Examples

Small projects built on `nytimes-games`. Each is a single script.

| Example | What it does | Cookies |
|---|---|---|
| [letter_boxed_solver.py](letter_boxed_solver.py) | Every two-word Letter Boxed solution, from the day's accepted word list | No |
| [clue_reuse.py](clue_reuse.py) | Answers that repeat across recent crosswords, and how each was clued, using `puzzle.entries()` | No |
| [solve_times.py](solve_times.py) | Your daily crossword times by weekday and by constructor | Yes |
| [api/](api) | Run your own NYT Games REST API, with a Dockerfile | Optional |

```bash
pip install nytimes-games
python letter_boxed_solver.py 2026-10-03
python clue_reuse.py --days 30 --type mini
NYT_COOKIES="NYT-S=..." python solve_times.py --days 180
```

The first two print answers, so they contain spoilers for the puzzles they
look at.
