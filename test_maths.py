"""python3 -m pytest test_maths.py  (or just: python3 test_maths.py)"""
import json, tempfile
from pathlib import Path

from exact import exact_stats
from simulate import simulate
from slot import Game


def tiny_game(**overrides):
    """A game small enough to check by hand."""
    cfg = {"name": "tiny", "rows": 1, "lines": [[0, 0, 0]], "wild": "W", "scatter": "S",
           "paytable": {"W": 10, "A": 2}, "free_games": {"scatters_needed": 3, "spins": 2, "multiplier": 3},
           "reels": [["A", "W", "S", "A"]] * 3}
    cfg.update(overrides)
    path = Path(tempfile.mkdtemp()) / "g.json"
    path.write_text(json.dumps(cfg))
    return Game(path)


def test_line_evaluation():
    g = Game()
    assert g.line_win(["WILD", "WILD", "WILD"]) == g.paytable["WILD"]
    assert g.line_win(["DRAGON", "WILD", "DRAGON"]) == g.paytable["DRAGON"]
    assert g.line_win(["DRAGON", "WILD", "COIN"]) == 0
    assert g.line_win(["WILD", "LANTERN", "WILD"]) == 0


def test_tiny_game_by_hand():
    # Per reel: P(A)=1/2, P(W)=1/4, P(S)=1/4.
    # P(AAA-with-wilds) = (3/4)^3 - (1/4)^3 = 26/64, P(WWW) = 1/64 -> base RTP = 2*26/64 + 10/64 = 62/64.
    # p = (1/4)^3 = 1/64; F=2, m=3: E[T] = 2*3*(62/64) / (1 - 2/64) = 6
    # total RTP = 62/64 + (1/64)*6 = 68/64
    s = exact_stats(tiny_game())
    assert abs(s["rtp_base"] - 62 / 64) < 1e-12
    assert abs(s["rtp_total"] - 68 / 64) < 1e-12


def test_simulation_matches_exact():
    g = Game()
    ex = exact_stats(g)
    for seed in (1, 2, 3):
        sim = simulate(g, 300_000, seed)
        assert abs(sim["rtp"] - ex["rtp_total"]) < 4 * sim["se_rtp"], seed
        assert abs(sim["sd"] - ex["sd_per_spin_x_bet"]) / ex["sd_per_spin_x_bet"] < 0.05, seed


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
