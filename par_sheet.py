"""Build par_sheet.xlsx: the game's maths as live Excel formulas, plus a check against exact.py and simulate.py.

Edit reel strips or pays in the workbook and the RTP recalculates. Run this script again to refresh the
'Verification' sheet (exact enumeration + simulation numbers come from Python).
"""
import sys
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as col

from exact import exact_stats
from simulate import simulate
from slot import Game

BLUE = Font(name="Arial", color="0000FF")
BOLD = Font(name="Arial", bold=True)
BASE = Font(name="Arial")
HEAD = Font(name="Arial", bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Border(bottom=Side(style="thin", color="999999"))
PCT = "0.0000%"


def header(ws, row, labels, start=1):
    for i, text in enumerate(labels):
        c = ws.cell(row, start + i, text)
        c.font, c.fill = HEAD, HEAD_FILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)


def build(game, out, spins, seed):
    wb = Workbook()
    nreels = len(game.reels)

    # ---- Inputs ----
    inp = wb.active
    inp.title = "Inputs"
    inp["A1"] = f"{game.name} - inputs (yellow cells are editable)"
    inp["A1"].font = Font(name="Arial", bold=True, size=13)
    settings = [("Lines played (1 credit each)", len(game.lines)), ("Rows visible", game.rows),
                ("Free spins awarded", game.fg["spins"]), ("Free spin multiplier", game.fg["multiplier"]),
                ("Wild symbol", game.wild), ("Scatter symbol", game.scatter)]
    header(inp, 3, ["Setting", "Value"])
    for i, (k, v) in enumerate(settings, start=4):
        inp.cell(i, 1, k).font = BASE
        c = inp.cell(i, 2, v)
        c.font, c.fill = BLUE, INPUT_FILL
    LINES, ROWS, FS, MULT, WILD, SCAT = (f"Inputs!$B${r}" for r in range(4, 10))
    inp["A10"] = ("Each payline pays when the symbol on every reel matches; the wild substitutes for every "
                  "symbol except the scatter. Three scatters anywhere award the free spins, which can retrigger.")
    inp["A10"].alignment = Alignment(wrap_text=True)
    inp.merge_cells("A10:B12")

    pay_items = list(game.paytable.items())
    header(inp, 3, ["Symbol", "Pays (3 on a line)"], start=4)
    for i, (sym, pay) in enumerate(pay_items, start=4):
        for j, v in enumerate((sym, pay), start=4):
            c = inp.cell(i, j, v)
            c.font, c.fill = BLUE, INPUT_FILL
    inp.column_dimensions["A"].width = 30
    inp.column_dimensions["B"].width = 14
    inp.column_dimensions["D"].width = 14
    inp.column_dimensions["E"].width = 18

    # ---- Reels ----
    rs = wb.create_sheet("Reels")
    header(rs, 1, [f"Reel {i + 1}" for i in range(nreels)])
    for i, strip in enumerate(game.reels):
        rs.column_dimensions[col(i + 1)].width = 12
        for k, sym in enumerate(strip, start=2):
            c = rs.cell(k, i + 1, sym)
            c.font, c.fill = BLUE, INPUT_FILL
    rs.freeze_panes = "A2"
    rs["A1"].comment = Comment("Reel strips, top to bottom. Add or remove stops freely; Par counts whole columns. "
                               "Keep scatters at least 'Rows visible' stops apart.", "par_sheet.py")

    # ---- Par ----
    par = wb.create_sheet("Par")
    par["A1"] = f"{game.name} - par sheet"
    par["A1"].font = Font(name="Arial", bold=True, size=13)
    reel_cols = [col(i + 1) for i in range(nreels)]

    # Symbol counts per reel
    par["A3"] = "Symbol counts per reel"
    par["A3"].font = BOLD
    header(par, 4, ["Symbol"] + [f"Reel {i + 1}" for i in range(nreels)])
    symbols = [f"=Inputs!D{i}" for i in range(4, 4 + len(pay_items))] + [f"={SCAT}"]
    first = 5
    for r, sym in enumerate(symbols, start=first):
        par.cell(r, 1, sym).font = BOLD
        for i, rc in enumerate(reel_cols):
            par.cell(r, 2 + i, f"=COUNTIF(Reels!{rc}:{rc},$A{r})").font = BASE
    last = first + len(symbols) - 1
    len_row = last + 1
    par.cell(len_row, 1, "Reel length").font = BOLD
    for i, rc in enumerate(reel_cols):
        par.cell(len_row, 2 + i, f"=COUNTA(Reels!{rc}:{rc})-1").font = BOLD
    cnt = lambda sym_row, i: f"{col(2 + i)}{sym_row}"            # count cell for a symbol row and reel index
    L = lambda i: f"{col(2 + i)}${len_row}"
    wild_row = first + [s for s, _ in pay_items].index(game.wild)
    scat_row = last

    # Line probabilities
    top = len_row + 2
    par.cell(top, 1, "Single payline (1 credit)").font = BOLD
    header(par, top + 1, ["Symbol", "Pays", "P(win on a line)", "Contribution"])
    lp_first = top + 2
    for k in range(len(pay_items)):
        r = lp_first + k
        sr = first + k
        par.cell(r, 1, f"=A{sr}").font = BASE
        par.cell(r, 2, f"=Inputs!E{4 + k}").font = BASE
        wild_only = "*".join(f"({cnt(wild_row, i)}/{L(i)})" for i in range(nreels))
        with_wild = "*".join(f"(({cnt(sr, i)}+{cnt(wild_row, i)})/{L(i)})" for i in range(nreels))
        # A symbol line = every reel shows the symbol or a wild, minus the all-wild case (that pays as WILD).
        f = f"=IF(A{r}={WILD},{wild_only},{with_wild}-{wild_only})"
        c = par.cell(r, 3, f)
        c.font, c.number_format = BASE, "0.000000"
        c = par.cell(r, 4, f"=B{r}*C{r}")
        c.font, c.number_format = BASE, "0.000000"
    lp_last = lp_first + len(pay_items) - 1
    sums = lp_last + 1
    par.cell(sums, 1, "Line return (= base RTP)").font = BOLD
    c = par.cell(sums, 4, f"=SUM(D{lp_first}:D{lp_last})")
    c.font, c.number_format = BOLD, PCT
    par.cell(sums + 1, 1, "Every line has the same odds because each row of a reel is uniformly distributed; "
                          "lines only change hit frequency and variance, not RTP.").font = Font(name="Arial", italic=True,
                                                                                                 color="666666")

    # Free games and totals
    t = sums + 3
    par.cell(t, 1, "Free games").font = BOLD
    rows = [
        ("P(scatter visible on reel)", None, None),
        ("P(trigger) = product over reels", "=" + "*".join(f"{col(2 + i)}{t + 1}" for i in range(nreels)), "0.000000"),
        ("Trigger frequency: 1 in", f"=1/B{t + 2}", "#,##0.0"),
        ("Expected free spins per trigger  F/(1-F·p)", f"={FS}/(1-{FS}*B{t + 2})", "0.000"),
        ("Mean win per free spin (x bet)", f"={MULT}*D{sums}", "0.0000"),
        ("Free games RTP", f"=B{t + 2}*B{t + 4}*B{t + 5}", PCT),
    ]
    for k, (label, f, fmt) in enumerate(rows, start=1):
        par.cell(t + k, 1, label).font = BASE
        if f:
            c = par.cell(t + k, 2, f)
            c.font, c.number_format = BASE, fmt
    for i in range(nreels):  # scatters >= rows apart, so each scatter stop gives 'rows' window positions
        c = par.cell(t + 1, 2 + i, f"={ROWS}*{cnt(scat_row, i)}/{L(i)}")
        c.font, c.number_format = BASE, "0.0000"

    tot = t + len(rows) + 2
    par.cell(tot, 1, "RTP summary").font = BOLD
    for k, (label, f) in enumerate([("Base game", f"=D{sums}"), ("Free games", f"=B{t + 6}"),
                                    ("Total RTP", f"=B{tot + 1}+B{tot + 2}")], start=1):
        par.cell(tot + k, 1, label).font = BOLD if label == "Total RTP" else BASE
        c = par.cell(tot + k, 2, f)
        c.font, c.number_format = (BOLD if label == "Total RTP" else BASE), PCT
        c.border = THIN
    par.column_dimensions["A"].width = 46
    for i in range(2, 2 + max(nreels, 4)):
        par.column_dimensions[col(i)].width = 16

    # ---- Verification ----
    ex = exact_stats(game)
    sim = simulate(game, spins, seed)
    vs = wb.create_sheet("Verification")
    vs["A1"] = "Cross-check: Excel formulas vs exact enumeration vs simulation"
    vs["A1"].font = Font(name="Arial", bold=True, size=13)
    header(vs, 3, ["Metric", "Excel (Par sheet)", "Exact (exact.py)", "Simulated (simulate.py)", "Excel - Exact"])
    total_cell = f"Par!B{tot + 3}"
    data = [
        ("Base game RTP", f"=Par!B{tot + 1}", ex["rtp_base"], None),
        ("Free games RTP", f"=Par!B{tot + 2}", ex["rtp_free"], None),
        ("Total RTP", f"={total_cell}", ex["rtp_total"], sim["rtp"]),
        ("Hit frequency", None, ex["hit_frequency"], None),
        ("Standard deviation (x bet)", None, ex["sd_per_spin_x_bet"], sim["sd"]),
        ("Volatility index (90%)", None, ex["volatility_index_90"], None),
    ]
    for r, (label, xl, exv, simv) in enumerate(data, start=4):
        vs.cell(r, 1, label).font = BASE
        fmt = PCT if "RTP" in label or "frequency" in label else "0.0000"
        for j, v in enumerate((xl, exv, simv), start=2):
            if v is not None:
                c = vs.cell(r, j, v)
                c.font, c.number_format = (BASE if j == 2 else BLUE), fmt
        if xl:
            c = vs.cell(r, 5, f"=B{r}-C{r}")
            c.font, c.number_format = BASE, "0.0E+00"
    note = (f"Blue values are pasted from Python: exact.py enumerates all {ex['combinations']:,} stop combinations; "
            f"simulate.py played {spins:,} spins (seed {seed}), RTP ±{1.96 * sim['se_rtp']:.3%} at 95%. "
            "Re-run par_sheet.py after editing inputs to refresh them.")
    vs.cell(11, 1, note).alignment = Alignment(wrap_text=True)
    vs.merge_cells("A11:E13")
    vs.column_dimensions["A"].width = 30
    for c_ in "BCDE":
        vs.column_dimensions[c_].width = 22

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = ws.title != "Par"
    wb.save(out)
    return ex, sim, total_cell


if __name__ == "__main__":
    spins = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
    ex, sim, cell = build(Game(), "par_sheet.xlsx", spins, 1)
    print(f"Wrote par_sheet.xlsx  (exact total RTP {ex['rtp_total']:.4%}, simulated {sim['rtp']:.4%})")
