"""Exact game maths by enumerating every reel-stop combination.

Base game: each of the prod(len(reel)) stop combinations is equally likely, so averaging over all of them gives
exact E[win], E[win^2], hit frequency and trigger probability.

Free games (retriggerable) are solved in closed form; see README.md "Free games" for the derivation.
  T  = total free-game win from one trigger (a block of F spins, each of which may retrigger another block)
  Y  = win from one free spin including any retriggered block:  Y = w + r*T'
  E[T]   = F*E[w] / (1 - F*p)
  E[T^2] = (F*(E[w^2] + 2*E[w*r]*E[T]) + F*(F-1)*E[Y]^2) / (1 - F*p)
"""
import itertools, math
from collections import Counter
from fractions import Fraction

from slot import Game


def exact_stats(game):
    combos = list(itertools.product(*(range(len(r)) for r in game.reels)))
    n = len(combos)
    m, F = game.fg["multiplier"], game.fg["spins"]

    # Fractions keep the base-game moments exact; converted to float only for the feature algebra.
    sb = sb2 = sbt = Fraction(0)
    trig = hits = 0
    dist = Counter()
    for stops in combos:
        b, scat = game.evaluate(stops)
        t = game.triggers(scat)
        sb += b
        sb2 += b * b
        sbt += b * t
        trig += t
        hits += (b > 0) or t
        dist[b] += 1

    Eb, Eb2, Ebt, p = (float(x / n) for x in (sb, sb2, sbt, Fraction(trig)))
    assert F * p < 1, "expected free spins per trigger is infinite (F*p >= 1)"

    # One free spin: w = m*b on the same strips, r = retrigger indicator.
    Ew, Ew2, Ewr = m * Eb, m * m * Eb2, m * Ebt
    ET = F * Ew / (1 - F * p)
    EY = Ew + p * ET
    ET2 = (F * (Ew2 + 2 * Ewr * ET) + F * (F - 1) * EY ** 2) / (1 - F * p)

    # Whole spin: Z = b + t*T
    EZ = Eb + p * ET
    EZ2 = Eb2 + 2 * Ebt * ET + p * ET2
    sd = math.sqrt(EZ2 - EZ ** 2)
    bet = game.bet
    return {
        "combinations": n,
        "rtp_base": Eb / bet,
        "rtp_free": p * ET / bet,
        "rtp_total": EZ / bet,
        "hit_frequency": hits / n,
        "trigger_probability": p,
        "expected_free_spins_per_trigger": F / (1 - F * p),
        "mean_feature_win_x_bet": ET / bet,
        "sd_per_spin_x_bet": sd / bet,
        # Industry "volatility index": RTP is within +/- VI/sqrt(N) of theory for 90% of N-spin sessions.
        "volatility_index_90": 1.645 * sd / bet,
        "base_win_distribution": {k: v / n for k, v in sorted(dist.items())},
    }


def report(game, s):
    print(f"{game.name}: {len(game.reels)} reels, {game.rows} rows, {len(game.lines)} lines, bet {game.bet} credits")
    print(f"  combinations enumerated   {s['combinations']:,}")
    print(f"  RTP base game             {s['rtp_base']:.4%}")
    print(f"  RTP free games            {s['rtp_free']:.4%}")
    print(f"  RTP total                 {s['rtp_total']:.4%}")
    print(f"  hit frequency             {s['hit_frequency']:.4%}  (1 in {1 / s['hit_frequency']:.2f})")
    print(f"  free games trigger        1 in {1 / s['trigger_probability']:,.1f}")
    print(f"  free spins per trigger    {s['expected_free_spins_per_trigger']:.3f} (incl. retriggers)")
    print(f"  mean feature win          {s['mean_feature_win_x_bet']:.2f} x bet")
    print(f"  standard deviation        {s['sd_per_spin_x_bet']:.3f} x bet per spin")
    print(f"  volatility index (90%)    {s['volatility_index_90']:.3f}")


if __name__ == "__main__":
    g = Game()
    report(g, exact_stats(g))
