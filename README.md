# slot-math

The maths model for a small poker-machine-style game, worked out three independent ways that check each other:

| | Method | Gives |
|---|---|---|
| `par_sheet.xlsx` | Excel par sheet with live, linked formulas from reel strips and paytable | Base, free-game and total RTP |
| `exact.py` | Exact enumeration of all 27,000 reel-stop combinations, plus a closed-form solution for retriggering free games | RTP, hit frequency, trigger frequency, standard deviation, volatility index |
| `simulate.py` | Monte Carlo: actually plays millions of spins, retriggers included | Checks the two above |

```bash
python3 exact.py              # par figures
python3 simulate.py 2000000   # Monte Carlo check
python3 par_sheet.py          # rebuild par_sheet.xlsx
python3 test_maths.py         # tests, including a game small enough to check by hand
```

## The game (`game.json`)
- **Layout:** 3 reels, 3 visible rows and 5 paylines (3 horizontal, 2 diagonal). Each line bets 1 credit, so a spin costs 5.
- **Line wins:** three of a kind on a line. **WILD** substitutes for every symbol except the scatter. Three wilds pay the WILD prize.
- **Free games:** a **LANTERN** scatter showing anywhere on all three reels awards 8 free spins at 2x. Free spins use the same reels and can retrigger.

## Results

| Metric | Value |
|---|---|
| Base game RTP | 80.85% |
| Free games RTP | 11.06% |
| **Total RTP** | **91.91%** |
| Hit frequency | 37.39% (1 in 2.67) |
| Free games trigger | 1 in 125 |
| Free spins per trigger (with retriggers) | 8.547 |
| Standard deviation | 2.650 x bet per spin |
| Volatility index (90%) | 4.36 |

The Excel formulas and exact enumeration agree to about 1e-16. The simulation (2M spins) agrees within 1.6 standard errors on RTP and within 0.04% on standard deviation. The paytable was tuned to land near 92%; NSW requires gaming machines to return at least 85%.

## The maths

**Notation**
- Reel *i* has length $L_i$.
- $c_i(X)$ is the number of stops on reel *i* showing symbol $X$.
- Every stop combination is equally likely.

### Line wins (`Par` sheet)
Each row of a reel is uniformly distributed, so the symbol at any one window position on reel *i* is $X$ with probability $c_i(X)/L_i$. Reels are independent. A line therefore pays symbol $X$ (with wild help) with probability

$$P(X) = \prod_i \frac{c_i(X) + c_i(W)}{L_i} \;-\; \prod_i \frac{c_i(W)}{L_i}$$

The subtracted term is the all-wild line, which pays as WILD instead: $P(W) = \prod_i c_i(W)/L_i$.

Expected win per line is $\sum_X P(X)\cdot\text{pay}(X)$. Every line has the same odds, so this is also the base-game RTP: adding lines changes hit frequency and variance, but not RTP.

### Scatter trigger
Scatters are kept at least 3 stops apart (enforced in `slot.py`), so each scatter stop puts the scatter in view for 3 of the $L_i$ reel positions:

$$p = \prod_i \frac{3\,c_i(S)}{L_i}$$

### Free games (retriggerable)
**Definitions**
- $F$ = spins awarded, $m$ = multiplier.
- For one free spin: $w = m\cdot b$ (the line win), and $r$ = 1 if it retriggers.
- $T$ = total win from one trigger.

Each of the $F$ spins wins $Y = w + r\,T'$, where $T'$ is an independent copy of $T$. So $T$ is the sum of $F$ independent copies of $Y$.

**Mean:** $E[T] = F\big(E[w] + p\,E[T]\big)$, so

$$E[T] = \frac{F\,E[w]}{1 - F p}, \qquad \text{expected spins} = \frac{F}{1-Fp}$$

**Second moment:** $E[Y^2] = E[w^2] + 2E[wr]E[T] + p\,E[T^2]$, and $E[T^2] = F\,E[Y^2] + F(F-1)E[Y]^2$. Solving gives

$$E[T^2] = \frac{F\big(E[w^2] + 2E[wr]E[T]\big) + F(F-1)E[Y]^2}{1 - Fp}$$

$E[wr]$ matters because a spin that retriggers can also pay a line win. It's measured exactly by enumeration rather than assuming independence.

### Whole spin
The total win from one paid spin is $Z = b + t\,T$, where $t$ = 1 if it triggers. So:
- $E[Z] = E[b] + p\,E[T]$
- $E[Z^2] = E[b^2] + 2E[bt]E[T] + p\,E[T^2]$
- RTP $= E[Z]/\text{bet}$
- SD $= \sqrt{E[Z^2]-E[Z]^2}\,/\,\text{bet}$

**Volatility index** $= 1.645 \times SD$. Over $N$ spins, the actual return falls within $\pm VI/\sqrt{N}$ of the theoretical RTP in about 90% of sessions.

## Ideas to extend
- Move to 5 reels or "243 ways" pays, where enumeration (about 24M stops) needs numpy vectorisation.
- Search reel strips automatically to hit a target RTP *and* volatility.
- Add scatter pays or a pick bonus, and work out the distribution of feature wins, not just its mean and variance.
