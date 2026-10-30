"""Game definition and spin evaluation, shared by exact.py, simulate.py and par_sheet.py.

Units: each line bets 1 credit, so a spin costs len(lines) credits.
RTP = expected total win per spin / cost per spin.
"""
import json
from functools import lru_cache
from pathlib import Path


class Game:
    def __init__(self, path=Path(__file__).with_name("game.json")):
        cfg = json.loads(Path(path).read_text())
        self.name = cfg["name"]
        self.rows = cfg["rows"]
        self.lines = cfg["lines"]
        self.wild = cfg["wild"]
        self.scatter = cfg["scatter"]
        self.paytable = cfg["paytable"]
        self.fg = cfg["free_games"]
        self.reels = cfg["reels"]
        self.bet = len(self.lines)
        self._check()

    def _check(self):
        for i, strip in enumerate(self.reels):
            # Scatters must be >= rows apart so at most one shows per reel; par_sheet's formula relies on it.
            pos = [k for k, s in enumerate(strip) if s == self.scatter]
            for a in pos:
                for b in pos:
                    gap = (b - a) % len(strip)
                    assert a == b or gap >= self.rows, f"reel {i + 1}: scatters closer than {self.rows} stops"
            unknown = set(strip) - set(self.paytable) - {self.scatter}
            assert not unknown, f"reel {i + 1}: symbols missing from paytable: {unknown}"

    def window(self, stops):
        """Visible symbols: window[reel][row]; the stop index is the top row."""
        return [[strip[(stop + r) % len(strip)] for r in range(self.rows)]
                for strip, stop in zip(self.reels, stops)]

    def line_win(self, symbols):
        """Pay for one line: all reels match, with WILD substituting for anything except the scatter."""
        if self.scatter in symbols:
            return 0
        non_wild = {s for s in symbols if s != self.wild}
        if not non_wild:
            return self.paytable[self.wild]
        if len(non_wild) == 1:
            return self.paytable[non_wild.pop()]
        return 0

    @lru_cache(maxsize=None)
    def evaluate(self, stops):
        """(line win in credits at 1x, number of reels showing a scatter) for one spin."""
        w = self.window(stops)
        win = sum(self.line_win([w[reel][row] for reel, row in enumerate(line)]) for line in self.lines)
        scatters = sum(self.scatter in col for col in w)
        return win, scatters

    def triggers(self, scatters):
        return scatters >= self.fg["scatters_needed"]
