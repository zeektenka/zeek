"""Video 1, Act 2 (the printing press and the numbers) — part 2 of the voiceover.

Cued to narration phrases, so it animates itself as soon as audio/part2.mp3
exists. Nothing here hard-codes a second.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine import style as S, paper as P, shots as sh                # noqa: E402
from engine.ease import ramp, stagger                                 # noqa: E402
from engine.text import text_sprite                                   # noqa: E402


def one_option(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 8, seed=30)
        sh.base(cv, t, n=6)
        sh.ledger(cv, t, ["TAX MORE", "BORROW MORE", "PRINT IT"], t0=0.1, x=520, y=380,
                  step=180, size=90, seed=9, accent_rows=(2,), strike=(0, 1), numbered=False)
        S.finish(cv)
    return draw


def last_resort(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=31)
        sh.base(cv, t, n=6)
        bank = S.cached(cv, "bank2", lambda r: S.bank_facade(r, seed=3), 1.1)
        S.slap(cv, bank, 640, 560, t, 0.1, -3, 1.0)
        lab = S.cached(cv, "rbz", lambda r: P.label("RESERVE BANK OF ZIMBABWE", r, 30, seed=33))
        S.slap(cv, lab, 640, 830, t, 0.4, 2, shadow=S.SHADOW_LOW)
        sh.ledger(cv, t, ["THE SOLDIERS GET PAID", "THE CIVIL SERVANTS GET PAID",
                          "THE BILLS GET PAID"],
                  t0=cue("On paper, the bills get paid") - 0.3, x=1180, y=430, step=130,
                  size=48, seed=10, numbered=False)
        S.finish(cv)
    return draw


def gono(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 8, seed=32)
        sh.base(cv, t, n=5)
        fold = S.cached(cv, "gono_f", lambda r: S.folder(r, 1240, 700, seed=24, tab="GOVERNOR"))
        S.slap(cv, fold, 960, 560, t, 0.0, -1.5, dur=0.45)
        sh.headline(cv, t, ["GIDEON GONO"], t0=0.3, x=960, y=460, size=112,
                    accent_line=None, seed=34, align_left=False,
                    sub="RESERVE BANK OF ZIMBABWE, FROM 2003")
        st = S.cached(cv, "st_scale", lambda r: P.stamp("AT SCALE", r, 52, S.ACCENT, seed=35))
        S.slap(cv, st, 1340, 790, t, cue("At scale") - 0.2, -10, depth=0, shadow=None,
               dur=0.25, spin=0)
        S.finish(cv)
    return draw


def claims(cue):
    """The core idea of the whole video: money is claims on goods."""
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=33)
        sh.base(cv, t, n=5, light=(0.5, 0.46))
        bread = S.cached(cv, "loaf2", lambda r: S.loaf(r, seed=2), 1.2)
        S.slap(cv, bread, 560, 540, t, 0.1, -3, 1.3)
        lab = S.cached(cv, "one_loaf", lambda r: P.label("ONE LOAF", r, 30, seed=36))
        S.slap(cv, lab, 560, 790, t, 0.35, -2, shadow=S.SHADOW_LOW)
        note = S.cached(cv, "note2", lambda r: S.banknote(r, seed=1), 1.0)
        t_c = cue("It only creates claims on them")
        for i in range(2):
            S.slap(cv, note, 1360 + i * 26, 470 + i * 150, t, t_c + i * 0.25, -8 + i * 5, 0.78)
        lab2 = S.cached(cv, "two_claims", lambda r: P.label("TWO CLAIMS ON IT", r, 30, seed=37))
        S.slap(cv, lab2, 1360, 800, t, t_c + 0.6, 2, shadow=S.SHADOW_LOW)
        t_d = cue("the price of bread doubles")
        if t > t_d - 0.4:
            sh.big_stat(cv, t, "PRICE ×2", t0=t_d - 0.3, y=960, size=120, glow=True, seed=12)
        S.finish(cv)
    return draw


def the_loop(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=34)
        sh.base(cv, t, n=6)
        sh.ledger(cv, t, ["NOBODY HOLDS THE MONEY", "EVERYONE SPENDS IT FASTER",
                          "PRICES RISE FASTER STILL"],
                  t0=0.15, x=430, y=360, step=175, size=76, seed=11, numbered=True)
        arrow_from = (1520, 820)
        arrow_to = (480, 330)
        sh.arrow(cv, t, cue("makes everybody spend faster still") - 0.2, arrow_from, arrow_to,
                 dur=1.1, width=7, bow=0.34, head=36)
        S.finish(cv)
    return draw


def collapse_of_belief(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.08, 7, seed=35)
        sh.base(cv, t, n=9, light=(0.5, 0.5))
        sh.headline(cv, t, ["NOT HIGH PRICES."], t0=0.0, x=960, y=380, size=120,
                    accent_line=None, seed=38, align_left=False)
        sh.headline(cv, t, ["A COLLAPSE OF BELIEF."],
                    t0=cue("A collapse of belief") - 0.25, x=960, y=600, size=120,
                    accent_line=0, seed=39, align_left=False)
        S.finish(cv)
    return draw


def data_stops(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=36)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "2,600%", label="OFFICIAL INFLATION, JULY 2008", t0=0.05,
                    y=470, size=250, sub="PER MONTH", seed=13)
        t_s = cue("stopped publishing the figures")
        st = S.cached(cv, "st_nodata", lambda r: P.stamp("NO FURTHER DATA", r, 54, "#e8dcc0", seed=40))
        S.slap(cv, st, 960, 830, t, t_s - 0.15, -7, depth=0, shadow=None, dur=0.25, spin=0)
        S.finish(cv)
    return draw


def hanke(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 9, seed=37)
        sh.base(cv, t, n=5)
        sh.headline(cv, t, ["INDEPENDENT", "ECONOMISTS", "KEPT COUNTING"], t0=0.0,
                    x=460, y=300, size=84, accent_line=None, seed=41)
        sh.big_stat(cv, t, "79.6bn%", label="PER MONTH, NOV 2008", t0=cue("seventy-nine point six billion percent") - 0.3,
                    x=1310, y=560, size=170, sub="HANKE, JOHNS HOPKINS", seed=14)
        S.finish(cv)
    return draw


def sextillion(cue):
    """The number nobody can picture — so show the digits."""
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 9, seed=38)
        sh.base(cv, t, n=6, light=(0.5, 0.46))
        sh.big_stat(cv, t, "89.7", label="SEXTILLION PERCENT A YEAR", t0=0.05, y=400,
                    size=260, seed=15)
        t_z = cue("An eight, a nine, and twenty-one more digits")
        if t > t_z - 0.5:
            digits = S.cached(cv, "zeros", lambda r: text_sprite(
                "89,700,000,000,000,000,000,000", S.ANTON, 76, r, S.PAPER))
            a = ramp(t, t_z - 0.4, 0.5, "out")
            cv.place(digits, 960, 760, alpha=a, scale=0.9 + 0.1 * a, depth=0)
            lab = S.cached(cv, "zl", lambda r: P.label("PERCENT", r, 28, seed=42))
            S.slap(cv, lab, 960, 870, t, t_z + 0.1, 1.5, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


def on_the_ground(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=39)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["PRICES DOUBLED", "ROUGHLY EVERY DAY"], t0=0.0, x=960, y=230,
                    size=98, accent_line=1, seed=43, align_left=False)
        rows = ["WAGES WORTHLESS BEFORE THEY COULD BE SPENT",
                "SHOPS REPRICED GOODS MID-QUEUE",
                "THE BAGS WERE WORTH MORE THAN THE NOTES"]
        sh.ledger(cv, t, rows, t0=cue("Wages were worthless") - 0.3, x=400, y=620,
                  step=130, size=48, seed=16, numbered=False)
        S.finish(cv)
    return draw


def hundred_trillion(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=40)
        sh.base(cv, t, n=5, light=(0.5, 0.46))
        note = S.cached(cv, "note100t", lambda r: S.banknote(
            r, value="100", word="TRILLION", seed=1), 1.3)
        S.slap(cv, note, 860, 500, t, 0.1, -5, 1.5, dur=0.5)
        lab = S.cached(cv, "ht_l", lambda r: P.label("ISSUED 16 JANUARY 2009", r, 30, seed=44))
        S.slap(cv, lab, 860, 790, t, 0.5, -2, shadow=S.SHADOW_LOW)
        t_v = cue("it was worth about thirty")
        if t > t_v - 0.4:
            sh.big_stat(cv, t, "US$30", label="WHAT IT WAS WORTH", t0=t_v - 0.3,
                        x=1430, y=900, size=150, seed=17)
        S.finish(cv)
    return draw


SHOTS = [
    ("There was one option left", one_option),
    ("It can have its central bank create money", last_resort),
    ("Under Gideon Gono", gono),
    ("Printing money does not create bread", claims),
    ("once people notice it happening", the_loop),
    ("That loop is what hyperinflation actually is", collapse_of_belief),
    ("By July 2008", data_stops),
    ("Independent economists kept measuring", hanke),
    ("Annualised, that is eighty-nine point seven", sextillion),
    ("So here is what it meant on the ground", on_the_ground),
    ("the Reserve Bank issued a one hundred trillion", hundred_trillion),
]
