"""Monte Carlo check: actually play N spins (free games and retriggers included) and compare with exact.py.

Usage: python3 simulate.py [spins] [seed]
"""
import math, random, sys

from exact import exact_stats
from slot import Game


def play_spin(game, rng):
    """Total win in credits for one paid spin, including any free games it triggers."""
    stops = tuple(rng.randrange(len(r)) for r in game.reels)
    win, scat = game.evaluate(stops)
    pending = game.fg["spins"] if game.triggers(scat) else 0
    while pending:
        pending -= 1
        stops = tuple(rng.randrange(len(r)) for r in game.reels)
        fwin, fscat = game.evaluate(stops)
        win += fwin * game.fg["multiplier"]
        if game.triggers(fscat):
            pending += game.fg["spins"]
    return win


def simulate(game, spins, seed):
    rng = random.Random(seed)
    total = total_sq = hits = 0
    for _ in range(spins):
        w = play_spin(game, rng)
        total += w
        total_sq += w * w
        hits += w > 0
    mean = total / spins
    sd = math.sqrt(total_sq / spins - mean ** 2)
    return {"rtp": mean / game.bet, "sd": sd / game.bet, "hit_rate_paying": hits / spins,
            "se_rtp": sd / game.bet / math.sqrt(spins)}


if __name__ == "__main__":
    spins = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    g = Game()
    ex, sim = exact_stats(g), simulate(g, spins, seed)
    z = (sim["rtp"] - ex["rtp_total"]) / sim["se_rtp"]
    print(f"{spins:,} simulated spins (seed {seed})")
    print(f"  RTP   exact {ex['rtp_total']:.4%}   simulated {sim['rtp']:.4%}  ± {1.96 * sim['se_rtp']:.4%} (95%)"
          f"   z = {z:+.2f}")
    print(f"  SD    exact {ex['sd_per_spin_x_bet']:.4f}     simulated {sim['sd']:.4f}  x bet")
    print("  " + ("OK: simulation agrees with exact maths" if abs(z) < 3 else "MISMATCH: check the maths"))
