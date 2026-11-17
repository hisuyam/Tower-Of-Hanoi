#!/usr/bin/env python3
"""Tower of Hanoi -- a playable game. Prolog is the brain (solver + hints).

  python hanoi.py            # play (GUI)
  python hanoi.py --cli 5    # headless solve + verify
"""
from __future__ import annotations

import argparse
import colorsys
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tkinter as tk
except ImportError:  # headless boxes still get --cli
    tk = None

PROLOG_FILE = Path(__file__).with_name("hanoi.pl")
PEGS = ("left", "middle", "right")


@dataclass(frozen=True)
class Move:
    disk: int
    src: str
    dst: str


# ------------------------------------------------------------ engine ----
def find_swipl() -> str | None:
    """PATH first, then the usual Windows/Mac install spots."""
    found = shutil.which("swipl")
    if found:
        return found
    for p in (r"C:\Program Files\swipl\bin\swipl.exe",
              r"C:\Program Files (x86)\swipl\bin\swipl.exe",
              "/Applications/SWI-Prolog.app/Contents/MacOS/swipl",
              "/opt/homebrew/bin/swipl", "/usr/local/bin/swipl"):
        if os.path.exists(p):
            return p
    return None


def _run_prolog(*args) -> str:
    return subprocess.run([find_swipl(), "-q", str(PROLOG_FILE), *map(str, args)],
                          capture_output=True, text=True, check=True).stdout


def _solve_python(n, a="left", b="right", c="middle"):
    if n:
        yield from _solve_python(n - 1, a, c, b)
        yield Move(n, a, b)
        yield from _solve_python(n - 1, c, b, a)


def solve(n: int) -> tuple[list[Move], str]:
    if not find_swipl():
        return list(_solve_python(n)), "python-fallback"
    moves = []
    for line in _run_prolog(n).splitlines():
        d, s, t = line.split()
        moves.append(Move(int(d), s, t))
    return moves, "prolog"


def _best_python(k, target, pegs):
    if k == 0:
        return None
    here = pegs[k - 1]
    if here == target:
        return _best_python(k - 1, target, pegs)
    other = next(p for p in PEGS if p not in (here, target))
    if all(pegs[i] == other for i in range(k - 1)):
        return Move(k, here, target)
    return _best_python(k - 1, other, pegs)


def hint(state: dict, n: int) -> Move | None:
    """Optimal next move from the CURRENT position (None if solved)."""
    pegs = [next(p for p in PEGS if d in state[p]) for d in range(1, n + 1)]
    if not find_swipl():
        return _best_python(n, "right", pegs)
    out = _run_prolog("hint", n, *pegs).split()
    return None if out[0] == "done" else Move(int(out[0]), out[1], out[2])


def verify(n: int, moves: list[Move]) -> bool:
    state = {p: [] for p in PEGS}
    state["left"] = list(range(n, 0, -1))
    for m in moves:
        src, dst = state[m.src], state[m.dst]
        if not src or src[-1] != m.disk or (dst and dst[-1] < m.disk):
            return False
        dst.append(src.pop())
    return state["right"] == list(range(n, 0, -1)) and len(moves) == 2**n - 1


# --------------------------------------------------------------- GUI ----
BG, PANEL, FG, ACCENT = "#0f111a", "#1a1d2b", "#e6e8f0", "#7c5cff"
GOOD, BAD, MUTED = "#3ddc97", "#ff5c7a", "#9aa0b8"
W, H, BASE_Y, DISK_H, TOP_Y = 900, 440, 380, 26, 70
PEG_X = {"left": 170, "middle": 450, "right": 730}


class App(tk.Tk if tk else object):
    def __init__(self):
        super().__init__()
        self.title("Tower of Hanoi · Prolog × Python")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.canvas = tk.Canvas(self, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=16, pady=(16, 6))
        self.canvas.bind("<Button-1>", self.on_click)

        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill="x", padx=16)
        self.n = tk.IntVar(value=4)
        tk.Label(bar, text="Disks", bg=PANEL, fg=FG).pack(side="left", padx=(12, 4))
        tk.Scale(bar, from_=1, to=10, orient="horizontal", variable=self.n, length=120,
                 bg=PANEL, fg=FG, highlightthickness=0, troughcolor=BG,
                 command=lambda _: self.new_game()).pack(side="left")
        for text, cmd in (("💡 Hint (H)", self.show_hint), ("↶ Undo (U)", self.undo),
                          ("⚡ Auto-solve (Space)", self.toggle_auto), ("New game (R)", self.new_game)):
            tk.Button(bar, text=text, command=cmd, bg=ACCENT, fg="white", relief="flat",
                      padx=10, pady=4, activebackground="#6a4ae0").pack(side="left", padx=5, pady=8)
        self.info = tk.StringVar()
        tk.Label(self, textvariable=self.info, bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=18, pady=(6, 12))

        for i, p in enumerate(PEGS):
            self.bind(str(i + 1), lambda e, p=p: self.pick(p))
        for key, fn in (("h", self.show_hint), ("u", self.undo), ("r", self.new_game),
                        ("<space>", self.toggle_auto)):
            self.bind(key, lambda e, fn=fn: fn())
        self.engine = "Prolog" if find_swipl() else "Python fallback (SWI-Prolog not found)"
        self.new_game()

    # -- state ---------------------------------------------------------
    def new_game(self):
        self.gen = getattr(self, "gen", 0) + 1       # invalidates running animations
        n = self.n.get()
        self.state = {p: [] for p in PEGS}
        self.state["left"] = list(range(n, 0, -1))
        self.history, self.moves = [], 0
        self.selected = self.hint_dst = None
        self.busy = self.auto = self.won = False
        self.msg("Click a peg (or press 1/2/3) to pick up its top disk, then click where to drop it.")
        self.draw()

    def msg(self, text, ok=None):
        self.note = text
        self.refresh_info()

    def refresh_info(self):
        n = self.n.get()
        self.info.set(f"Moves: {self.moves}   ·   Optimal: {2**n - 1}   ·   Engine: {self.engine}   ·   {self.note}")

    def legal(self, src, dst):
        s, d = self.state[src], self.state[dst]
        return bool(s) and src != dst and (not d or d[-1] > s[-1])

    # -- drawing -------------------------------------------------------
    def color(self, d):
        r, g, b = colorsys.hsv_to_rgb(0.72 - 0.7 * d / self.n.get(), 0.6, 0.95)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def width(self, d):
        return 50 + d * (190 // self.n.get())

    def disk_item(self, d, x, y, outline=""):
        w = self.width(d) / 2
        return self.canvas.create_rectangle(x - w, y - DISK_H / 2 + 1, x + w, y + DISK_H / 2 - 1,
                                            fill=self.color(d), outline=outline, width=3)

    def y_at(self, level):
        return BASE_Y - DISK_H * (level + 0.5) - 1

    def draw(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(40, BASE_Y, W - 40, BASE_Y + 14, fill=PANEL, outline="")
        for i, (p, x) in enumerate(PEG_X.items()):
            hot = p == self.selected
            c.create_rectangle(x - 5, BASE_Y - 280, x + 5, BASE_Y,
                               fill=ACCENT if hot else "#3a3f5c", outline="")
            c.create_text(x, BASE_Y + 32, text=str(i + 1), fill=MUTED, font=("Segoe UI", 12))
            if p == self.hint_dst:
                c.create_polygon(x - 14, TOP_Y - 34, x + 14, TOP_Y - 34, x, TOP_Y - 12, fill=GOOD, outline="")
            for level, d in enumerate(self.state[p]):
                lifted = hot and level == len(self.state[p]) - 1
                self.disk_item(d, x, TOP_Y if lifted else self.y_at(level), "white" if lifted else "")
        if self.won:
            c.create_rectangle(W/2 - 230, 150, W/2 + 230, 250, fill=PANEL, outline=GOOD, width=2)
            c.create_text(W/2, 188, text="🎉 Solved!", fill=GOOD, font=("Segoe UI", 24, "bold"))
            n = self.n.get()
            tag = "a perfect run!" if self.moves == 2**n - 1 else f"optimal is {2**n - 1}"
            c.create_text(W/2, 225, text=f"{self.moves} moves — {tag}", fill=FG, font=("Segoe UI", 13))

    # -- input ---------------------------------------------------------
    def on_click(self, e):
        self.pick(min(PEG_X, key=lambda p: abs(PEG_X[p] - e.x)))

    def pick(self, peg):
        if self.auto:
            self.auto = False
        if self.busy or self.won:
            return
        self.hint_dst = None
        if self.selected is None:
            if self.state[peg]:
                self.selected = peg
                self.msg(f"Holding disk {self.state[peg][-1]}. Choose a peg to drop it on.")
            else:
                self.msg("That peg is empty.")
        elif self.selected == peg:
            self.selected = None
            self.msg("Put it back.")
        elif self.legal(self.selected, peg):
            src, self.selected = self.selected, None
            self.do_move(Move(self.state[src][-1], src, peg))
            return
        else:
            self.msg("Illegal: a bigger disk can't sit on a smaller one.")
        self.draw()

    def undo(self):
        if self.busy or not self.history:
            return
        self.auto = False
        m = self.history.pop()
        self.state[m.dst].pop()
        self.state[m.src].append(m.disk)
        self.moves -= 1
        self.won, self.selected, self.hint_dst = False, None, None
        self.msg("Undid last move.")
        self.draw()

    def show_hint(self):
        if self.busy or self.won:
            return
        m = hint(self.state, self.n.get())
        if m:
            self.selected, self.hint_dst = m.src, m.dst
            self.msg(f"Prolog suggests: disk {m.disk}  {m.src} → {m.dst}")
            self.draw()

    def toggle_auto(self):
        if self.auto:
            self.auto = False
            return
        if self.busy or self.won:
            return
        self.auto, self.selected, self.hint_dst = True, None, None
        self.msg("Auto-solving from the current position… (click anywhere to stop)")
        self.auto_step()

    def auto_step(self):
        if not self.auto or self.won:
            return
        m = hint(self.state, self.n.get())
        if m:
            self.do_move(m, lambda: self.after(80, self.auto_step))

    # -- animation -----------------------------------------------------
    def do_move(self, m, then=None):
        gen = self.gen
        self.state[m.src].pop()
        self.draw()
        x0, y0 = PEG_X[m.src], self.y_at(len(self.state[m.src]))
        x1, y1 = PEG_X[m.dst], self.y_at(len(self.state[m.dst]))
        path = ([(x0, y0 + (TOP_Y - y0) * i / 8) for i in range(1, 9)] +
                [(x0 + (x1 - x0) * i / 14, TOP_Y) for i in range(1, 15)] +
                [(x1, TOP_Y + (y1 - TOP_Y) * i / 8) for i in range(1, 9)])
        item = self.disk_item(m.disk, x0, y0)
        w = self.width(m.disk) / 2
        self.busy = True

        def frame(i=0):
            if gen != self.gen:
                return
            if i < len(path):
                x, y = path[i]
                self.canvas.coords(item, x - w, y - DISK_H / 2 + 1, x + w, y + DISK_H / 2 - 1)
                self.after(10, frame, i + 1)
                return
            self.state[m.dst].append(m.disk)
            self.history.append(m)
            self.moves += 1
            self.busy = False
            if len(self.state["right"]) == self.n.get():
                self.won, self.auto = True, False
                self.msg("Solved! Press R or move the slider for a new game.")
            else:
                self.msg(f"Moved disk {m.disk}: {m.src} → {m.dst}")
            self.draw()
            if then and not self.won:
                then()
        frame()


def cli(n: int):
    moves, engine = solve(n)
    ok = verify(n, moves)
    for i, m in enumerate(moves, 1):
        print(f"{i:>4}. disk {m.disk}: {m.src} -> {m.dst}")
    print(f"\nengine={engine} moves={len(moves)} optimal={2**n - 1} valid={ok}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", type=int, metavar="N", help="solve headless for N disks")
    args = ap.parse_args()
    if args.cli:
        cli(args.cli)
    elif tk is None:
        sys.exit("tkinter not installed; use --cli N")
    else:
        App().mainloop()
