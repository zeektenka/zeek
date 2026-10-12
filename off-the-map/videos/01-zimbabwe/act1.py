"""Video 1, Act 1 (0:00-2:46) — animated against the real Cedric M narration.

Every shot is cued to a phrase in the voiceover, so re-generating the audio
re-times the animation automatically: nothing here hard-codes a second.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np                                                    # noqa: E402

from engine import geo, post                                          # noqa: E402
from engine import style as S, paper as P, shots as sh                # noqa: E402
from engine.ease import ramp, stagger, drift, Track, mix_color        # noqa: E402
from engine.text import text_sprite                                   # noqa: E402

_world = None


def world():
    global _world
    if _world is None:
        _world = geo.World()
    return _world


# ------------------------------------------------------------------ 1. HOOK
def hook(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 10, seed=1)
        sh.base(cv, t, n=8)
        bread = S.cached(cv, "loaf", lambda r: S.loaf(r, seed=2), 1.4)
        S.slap(cv, bread, 640, 520, t, cue("a loaf of bread") - 0.45, -4, 2.0, dur=0.5)
        tag = S.cached(cv, "tag_am", lambda r: P.label("ONE LOAF · HARARE, 2008", r, 30, seed=3))
        S.slap(cv, tag, 640, 880, t, cue("a loaf of bread") + 0.5, -2, shadow=S.SHADOW_LOW)
        # the price ticks up while he says it keeps rising
        t_up = cue("and more by the afternoon") - 0.35
        if t > t_up - 0.6:
            sh.counter(cv, t, t_up, 2.8, 1.2e6, 2.5e7, 1390, 470, size=128,
                       prefix="Z$", shake=3.0, seed=4)
            tag2 = S.cached(cv, "tag_pm", lambda r: P.label("BY THE AFTERNOON", r, 28, seed=5))
            S.slap(cv, tag2, 1390, 610, t, t_up + 0.6, 2, shadow=S.SHADOW_LOW)
        note = S.cached(cv, "note", lambda r: S.banknote(r, seed=1), 1.1)
        for i, (dx, dy, rot) in enumerate([(-26, 34, -13), (-10, 16, -9), (0, 0, -5)]):
            S.slap(cv, note, 1390 + dx, 870 + dy, t, cue("cost millions of dollars") + i * 0.09,
                   rot, 0.82)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 2. TITLE
def title(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.08, 8, seed=2)
        sh.base(cv, t, n=10)
        big = S.cached(cv, "ghost08", lambda r: text_sprite("2008", S.ANTON, 520, r, "#2b2823"))
        cv.place(big, 1480, 620, depth=0.7, alpha=ramp(t, 0, 0.55), rot=-3)
        sh.headline(cv, t, ["WHEN MONEY", "STOPS MEANING", "ANYTHING"], t0=0.1,
                    x=640, y=300, size=124, accent_line=2, seed=4)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 3. MAP
def map_intro(cue):
    def draw(cv, t):
        sh.map_shot(cv, t, world(), "ZWE", highlight={"ZWE": S.ACCENT}, fill=0.34,
                    zoom_from=["ZAF", "COD", "TZA", "AGO"], zoom_dur=3.0, lift_at=2.6,
                    title="ZIMBABWE", sub="SOUTHERN AFRICA", seed=2,
                    label=[(28.0, -14.6, "ZAMBIA"), (35.0, -19.6, "MOZAMBIQUE"),
                           (23.6, -22.3, "BOTSWANA"), (26.5, -24.0, "SOUTH AFRICA")])
        st = S.cached(cv, "st_worked", lambda r: P.stamp("IT USED TO WORK", r, 46, S.ACCENT, seed=6))
        S.slap(cv, st, 1430, 880, t, cue("Zimbabwe used to work"), -9, depth=0,
               shadow=None, dur=0.25, spin=0)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 4. EXPORTS
def exports(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=3)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["IT EXPORTED", "FOOD"], t0=0.05, x=540, y=230, size=98,
                    accent_line=1, seed=7)
        sh.cards(cv, t, ["TOBACCO", "MAIZE", "BEEF"], t0=cue("Tobacco, maize, beef") - 0.15,
                 gap=0.17, y=720, w=400, h=300, size=58, seed=2)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 5. IT WORKED
def it_worked(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=4)
        sh.base(cv, t, n=6)
        sh.ledger(cv, t, ["FACTORIES", "A WORKING BANKING SYSTEM",
                          "ONE OF AFRICA'S BEST-EDUCATED POPULATIONS"],
                  t0=0.15, x=420, y=380, step=170, size=62, seed=3)
        bank = S.cached(cv, "bank", lambda r: S.bank_facade(r, seed=3), 1.0)
        S.slap(cv, bank, 1480, 760, t, cue("a functioning banking system") - 0.2, 4, 0.78,
               depth=0.9)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 6. BREADBASKET
def breadbasket(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 10, seed=5)
        sh.base(cv, t, n=7, light=(0.5, 0.46))
        sh.headline(cv, t, ["THE BREADBASKET"], t0=0.0, x=960, y=430, size=170,
                    accent_line=0, seed=9, align_left=False)
        sub = S.cached(cv, "bb_sub", lambda r: P.label("OF THE REGION", r, 34, seed=11))
        S.slap(cv, sub, 960, 590, t, 0.25, 1.5, shadow=S.SHADOW_LOW)
        # the honest beat: the claim gets qualified on screen as he qualifies it
        t_d = cue("Historians now argue that title")
        st = S.cached(cv, "st_disp", lambda r: P.stamp("DISPUTED", r, 54, "#e8dcc0", seed=12))
        S.slap(cv, st, 1290, 330, t, t_d + 0.3, -13, depth=0, shadow=None, dur=0.25, spin=0)
        sh.two_sided(cv, t,
                     "ZIMBABWE FED ITSELF\nAND SOLD THE SURPLUS",
                     "BUT IT WAS NEVER\nAFRICA'S BIGGEST\nFOOD PRODUCER",
                     t0=t_d + 0.9, y=800, seed=4)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 7. THREE BILLS
def three_bills(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 9, seed=6)
        sh.base(cv, t, n=7)
        sh.headline(cv, t, ["THREE BILLS", "IT COULD NOT PAY"], t0=0.0, x=960, y=230,
                    size=96, accent_line=1, seed=13, align_left=False)
        for i in range(3):
            a = stagger(t, cue("three bills it could not pay") - 0.4, i, 0.5, 8, ease="soft_back")
            if a <= 0:
                continue
            card = S.cached(cv, ("bill", i), lambda r, i=i: S.folder(r, 420, 300, seed=20 + i,
                                                                    tab=f"BILL {i + 1}"))
            cv.place(card, 440 + i * 520, 760, scale=0.86 + 0.14 * a, rot=(-4, 2, -2)[i],
                     alpha=min(1, a * 2), shadow=S.SHADOW)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 8. BILL ONE
def bill_one(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=7)
        sh.base(cv, t, n=5)
        card = S.cached(cv, "b1", lambda r: S.folder(r, 1180, 640, seed=20, tab="BILL 1"))
        S.slap(cv, card, 960, 580, t, 0.0, -1.5, dur=0.45)
        sh.big_stat(cv, t, "1997", t0=0.35, y=600, size=250, color=S.ACCENT, glow=False)
        lab = S.cached(cv, "b1l", lambda r: P.label("WAR VETERANS' PENSIONS", r, 34, seed=14))
        S.slap(cv, lab, 960, 790, t, 0.6, 1.5, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 9. VETERANS
def veterans(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=8)
        sh.base(cv, t, n=7)
        sh.headline(cv, t, ["THEY HAD BEEN", "PROMISED PENSIONS"], t0=0.0, x=500, y=270,
                    size=80, accent_line=None, seed=15)
        news = S.cached(cv, "news_vets", lambda r: S.newsprint(
            620, 760, r * 0.8, 31, headline="VETERANS\nDEMAND\nWHAT THEY\nARE OWED", cols=2))
        S.slap(cv, news, 1420, 600, t, 0.5, 3, 0.95)
        tp = S.cached(cv, "tp_v", lambda r: P.tape(150, 44, r, seed=16))
        S.slap(cv, tp, 1340, 250, t, 0.75, -24, shadow=S.SHADOW_LOW, spin=0)
        t_m = cue("President Robert Mugabe gave in")
        st = S.cached(cv, "st_gavein", lambda r: P.stamp("HE GAVE IN", r, 52, S.ACCENT, seed=17))
        S.slap(cv, st, 620, 760, t, t_m + 0.25, -11, depth=0, shadow=None, dur=0.25, spin=0)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 10. THE MATHS
def the_maths(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 9, seed=9)
        sh.base(cv, t, n=5, light=(0.5, 0.44))
        sh.equation(cv, t, "50,000", "×", "Z$50,000", "Z$4.2 BILLION",
                    t0=0.1, y=430, size=104, result_size=165, seed=5,
                    caption="PLUS MONTHLY PENSIONS — NONE OF IT BUDGETED")
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 11. UNBUDGETED
def unbudgeted(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 8, seed=10)
        sh.base(cv, t, n=6)
        sheet = S.cached(cv, "budget", lambda r: S.newsprint(
            900, 620, r * 0.9, 41, headline="NATIONAL BUDGET\n1997", cols=2, tone=S.PAPER))
        S.slap(cv, sheet, 860, 560, t, 0.0, -2, dur=0.4)
        st = S.cached(cv, "st_unb", lambda r: P.stamp("NOT IN IT", r, 72, S.ACCENT, seed=18))
        S.slap(cv, st, 1120, 640, t, 0.5, -12, depth=0, shadow=None, dur=0.22, spin=0)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 12/13. BIG NUMBERS
def total_bill(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=11)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "Z$4.2bn", label="THE TOTAL BILL", t0=0.1, y=520, size=270,
                    sub="UNBUDGETED, 1997", seed=7)
        S.finish(cv)
    return draw


def share_of_economy(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=12)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "3%", label="OF THE ENTIRE ECONOMY", t0=0.05, y=500, size=330,
                    sub="CONJURED OUT OF NOTHING", seed=8)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 14. THE FALL
def black_friday_chart(cue):
    pts = [(0, 100), (1, 99), (2, 100), (3, 98), (4, 99), (5, 97), (6, 28), (7, 27), (8, 26)]

    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=13)
        sh.base(cv, t, n=5, light=(0.52, 0.46))
        sh.line_chart(cv, t, pts, t0=0.1, rect=(430, 330, 1060, 470),
                      title="THE ZIMBABWE DOLLAR", dur=2.2, seed=10, label_end=None, fill=False,
                      y_range=(0, 105))
        t_f = cue("fell by roughly seventy-two percent")
        if t > t_f - 0.3:
            sh.big_stat(cv, t, "−72%", t0=t_f - 0.2, x=1380, y=890, size=180, glow=True,
                        sub="IN ONE DAY", seed=9)
        S.finish(cv)
    return draw


def stock_market(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=14)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "−46%", label="THE STOCK MARKET", t0=0.05, y=510, size=320,
                    sub="THE SAME DAY", seed=11)
        S.finish(cv)
    return draw


def black_friday_card(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.08, 6, seed=15)
        sh.base(cv, t, n=10, light=(0.5, 0.5))
        sh.headline(cv, t, ["BLACK", "FRIDAY"], t0=0.0, x=960, y=420, size=230,
                    accent_line=1, seed=19, align_left=False, gap=1.1)
        sub = S.cached(cv, "bf_sub", lambda r: P.label("14 NOVEMBER 1997", r, 36, seed=20))
        S.slap(cv, sub, 960, 790, t, 0.4, 1.5, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 15. DRC WAR
def drc_war(cue):
    def draw(cv, t):
        W = world()
        sh.map_shot(cv, t, W, ["COD", "ZWE"], highlight={"ZWE": S.KRAFT, "COD": S.ACCENT},
                    fill=0.68, lift_at=0.5, seed=5,
                    label=[(23.0, -3.0, "DR CONGO"), (29.6, -19.0, "ZIMBABWE")])
        a, b = W.point(30.0, -19.0), W.point(23.5, -4.0)
        sh.arrow(cv, t, cue("sent troops into the war") - 0.2, a, b, dur=1.0,
                 width=6.0 / max(cv.cam.zoom, 0.2), bow=0.26, head=26 / max(cv.cam.zoom, 0.2))
        lab = S.cached(cv, "drc_l", lambda r: S.title_strip("AN EXPENSIVE FOREIGN WAR", r, 62, seed=21))
        S.slap(cv, lab, 960, 960, t, cue("An expensive foreign war") - 0.25, -1.5, depth=0)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 16. LAND REFORM
def third_bill(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 7, seed=16)
        sh.base(cv, t, n=6)
        card = S.cached(cv, "b3", lambda r: S.folder(r, 1180, 620, seed=22, tab="BILL 3"))
        S.slap(cv, card, 960, 560, t, 0.0, -2, dur=0.45)
        sh.headline(cv, t, ["THE BIGGEST", "OF THE THREE"], t0=0.3, x=960, y=470, size=92,
                    accent_line=0, seed=23, align_left=False)
        S.finish(cv)
    return draw


def land_reform(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=17)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["FROM 2000:", "THE FARMS", "WERE SEIZED"], t0=0.0, x=520, y=250,
                    size=88, accent_line=2, seed=24)
        news = S.cached(cv, "news_farm", lambda r: S.newsprint(
            600, 700, r * 0.8, 51, headline="COMMERCIAL\nFARMS\nTAKEN", cols=2))
        S.slap(cv, news, 1450, 600, t, 0.5, 3.5, 0.92)
        S.finish(cv)
    return draw


def contested(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 9, seed=18)
        sh.base(cv, t, n=6, light=(0.5, 0.46))
        sh.headline(cv, t, ["GENUINELY CONTESTED"], t0=0.0, x=960, y=230, size=86,
                    accent_line=None, seed=25, align_left=False)
        sh.two_sided(cv, t,
                     "THIS WAS LAND TAKEN\nUNDER COLONIAL RULE.\nTHE CASE FOR RETURNING\nIT WAS REAL.",
                     "BUT THE EXECUTION\nDESTROYED THE THING\nTHAT PAID THE BILLS.",
                     t0=0.25, y=640, seed=6,
                     left_label="THE CASE FOR", right_label="WHAT HAPPENED")
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 17. OUTPUT FALLS
def output_falls(cue):
    pts = [(0, 100), (1, 92), (2, 71), (3, 55), (4, 41), (5, 33), (6, 28)]

    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=19)
        sh.base(cv, t, n=5)
        sh.line_chart(cv, t, pts, t0=0.15, rect=(450, 350, 1020, 450),
                      title="FARM OUTPUT", dur=2.4, seed=12, y_range=(0, 105))
        sh.ledger(cv, t, ["NO EQUIPMENT", "NO CREDIT", "NO EXPERTISE"],
                  t0=cue("without equipment") - 0.25, x=1260, y=430, step=118, size=50,
                  seed=7, numbered=False, strike=(0, 1, 2))
        S.finish(cv)
    return draw


def exports_fell(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 7, seed=20)
        sh.base(cv, t, n=5)
        sh.headline(cv, t, ["OUTPUT FELL."], t0=0.0, x=960, y=380, size=130,
                    accent_line=None, seed=26, align_left=False)
        sh.headline(cv, t, ["EXPORTS FELL WITH IT."], t0=cue("Exports fell with it") - 0.2,
                    x=960, y=580, size=130, accent_line=0, seed=27, align_left=False)
        sub = S.cached(cv, "ef_sub", lambda r: P.label(
            "AND EXPORTS WERE HOW ZIMBABWE EARNED FOREIGN CURRENCY", r, 32, seed=28))
        S.slap(cv, sub, 960, 830, t, cue("earned foreign currency") - 0.4, 1.2,
               shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ 18. THE SQUEEZE
def squeeze(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=21)
        sh.base(cv, t, n=7, light=(0.5, 0.48))
        sh.ledger(cv, t, ["LESS COMING IN", "FAR MORE GOING OUT", "NOBODY WILLING TO LEND"],
                  t0=0.15, x=430, y=400, step=190, size=86, seed=8,
                  accent_rows=(2,), numbered=False)
        S.finish(cv)
    return draw


# ------------------------------------------------------------------ assembly
SHOTS = [
    ("In 2008", hook),
    ("This is how a country's money", title),
    ("you have to start somewhere unexpected", map_intro),
    ("this was a country that exported food", exports),
    ("It had factories", it_worked),
    ("People called it the breadbasket", breadbasket),
    ("that economy ran into three bills", three_bills),
    ("The first arrived in 1997", bill_one),
    ("For years, veterans", veterans),
    ("Fifty thousand veterans would each receive", the_maths),
    ("None of it was in the budget", unbudgeted),
    ("The total came to around", total_bill),
    ("About three percent of the entire economy", share_of_economy),
    ("The markets understood immediately", black_friday_chart),
    ("The stock market lost nearly half", stock_market),
    ("Zimbabweans still call it", black_friday_card),
    ("The second bill came a year later", drc_war),
    ("The third was the biggest", third_bill),
    ("the government began seizing large commercial farms", land_reform),
    ("The politics of that are genuinely contested", contested),
    ("Farms changed hands", output_falls),
    ("Output fell", exports_fell),
    ("So now the government had", squeeze),
]


def build(video, timing, total, offset=0.0):
    reel = sh.Reel(timing, offset, total)
    for cue, factory in SHOTS:
        reel.add(cue, factory, lead=0.25)
    return reel.build(video, end=total)
