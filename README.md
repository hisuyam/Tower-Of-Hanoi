# Tower of Hanoi: Prolog × Python

An animated Tower of Hanoi where **Prolog does the reasoning and Python does the presenting**.
SWI-Prolog computes the optimal solution, and Python independently checks it against the rules
and animates it in a Tkinter window.

## Features

- Animated GUI with 1 to 10 disks, adjustable speed, and **Auto**, **Step** and **Reset** controls
- Optimal solution every time: `2ⁿ − 1` moves
- Python re-plays every move against the rules, so an invalid solution is caught immediately
- Headless `--cli` mode that prints the moves and verifies them
- Falls back to a pure-Python solver if SWI-Prolog isn't installed

## Files

| File       | What it does                                                        |
|------------|---------------------------------------------------------------------|
| `hanoi.pl` | SWI-Prolog solver (uses DCGs, so it runs in O(2ⁿ))                   |
| `hanoi.py` | GUI, CLI, move verification, and the bridge that calls Prolog       |

## Requirements

- **Python 3.8+** (Tkinter ships with the standard Windows and macOS installers)
- **[SWI-Prolog](https://www.swi-prolog.org/Download.html)** (optional). Make sure `swipl` is on your PATH.
  Without it the program still works and shows `engine: python-fallback` in the status bar.

## Usage

Animated GUI:

```bash
python hanoi.py
```

Headless: solve for N disks and verify the result:

```bash
python hanoi.py --cli 5
```

Example output:

```
   1. disk 1: left -> right
   2. disk 2: left -> middle
   3. disk 1: right -> middle
   ...

engine=prolog moves=31 optimal=31 valid=True
```

The exit code is `0` if the solution is valid and `1` if it isn't.

Run just the Prolog solver on its own:

```bash
swipl -q hanoi.pl 4
```

## How it works

1. `hanoi.py` runs `swipl -q hanoi.pl N` and reads one move per line (`disk from to`).
2. `verify()` replays those moves on three pegs, checking that each disk is on top of its peg,
   that no disk lands on a smaller one, that the tower ends on the right peg, and that the move
   count is exactly `2ⁿ − 1`.
3. The GUI animates each move, lifting the disk, sliding it across, and lowering it onto the new peg.

## License

Add a license of your choice (for example MIT) if you want others to reuse this code.
