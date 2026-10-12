"""Video 10 — Why the US Can Print Money and Zimbabwe Can't.

All three acts. Every shot is cued to a narration phrase, so the whole video
animates itself as soon as the voiceover parts exist.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine import geo, style as S, paper as P, shots as sh          # noqa: E402
from engine.ease import ramp, stagger                                 # noqa: E402
from engine.text import text_sprite                                   # noqa: E402

_world = None


def world():
    global _world
    if _world is None:
        _world = geo.World()
    return _world


# ============================================================ ACT 1
def same_action(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 9, seed=70)
        sh.base(cv, t, n=7)
        note = S.cached(cv, "zwnote", lambda r: S.banknote(r, seed=1), 1.0)
        S.slap(cv, note, 1390, 430, t, cue("Zimbabwe printed money") - 0.3, -6, 0.95)
        sh.headline(cv, t, ["AMERICA PRINTED", "TRILLIONS"], t0=0.05, x=520, y=250,
                    size=84, accent_line=None, seed=80)
        sh.headline(cv, t, ["SAME ACTION.", "OPPOSITE RESULTS."],
                    t0=cue("Same action") - 0.3, x=960, y=760, size=112,
                    accent_line=1, seed=81, align_left=False)
        S.finish(cv)
    return draw


def be_precise(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=71)
        sh.base(cv, t, n=5)
        sh.headline(cv, t, ["IT IS ALMOST NEVER", "PHYSICAL NOTES"], t0=0.05, x=960,
                    y=270, size=92, accent_line=None, seed=82, align_left=False)
        sh.ledger(cv, t, ["A CENTRAL BANK CREATES RESERVES",
                          "IT BUYS ASSETS WITH THEM",
                          "MOSTLY GOVERNMENT BONDS"],
                  t0=cue("A central bank creates reserves") - 0.3, x=460, y=600,
                  step=140, size=54, seed=20)
        S.finish(cv)
    return draw


def fed_balance(cue):
    pts = [(0, 4.17), (1, 6.3), (2, 7.1), (3, 7.3), (4, 7.6), (5, 8.0), (6, 8.5), (7, 8.95)]

    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=72)
        sh.base(cv, t, n=5)
        sh.line_chart(cv, t, pts, t0=0.15, rect=(440, 360, 1010, 420),
                      title="THE FED'S BALANCE SHEET", dur=2.2, seed=21, y_range=(0, 10))
        t_d = cue("roughly doubled")
        if t > t_d - 0.4:
            sh.big_stat(cv, t, "$8.9tn", label="FROM $4.2 TRILLION", t0=t_d - 0.3,
                        x=1300, y=905, size=140, sub="FEB 2020 TO APR 2022", seed=22)
        S.finish(cv)
    return draw


def opposite_outcomes(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=73)
        sh.base(cv, t, n=6, light=(0.5, 0.46))
        sh.two_sided(cv, t,
                     "ZIMBABWE'S CURRENCY\nWENT TO ZERO",
                     "THE DOLLAR\nWENT UP",
                     t0=0.1, y=560, seed=20,
                     left_label="SAME MECHANISM", right_label="SAME YEARS")
        sh.headline(cv, t, ["THE DIFFERENCE IS NOT THE PRINTER"],
                    t0=cue("The difference is not the printer") - 0.3, x=960, y=900,
                    size=72, accent_line=0, seed=83, align_left=False)
        S.finish(cv)
    return draw


def somebody_wants_it(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=74)
        sh.base(cv, t, n=8, light=(0.5, 0.5))
        sh.headline(cv, t, ["SOMEBODY ELSE", "WANTS ITS MONEY"], t0=0.05, x=960, y=400,
                    size=138, accent_line=1, seed=84, align_left=False)
        S.finish(cv)
    return draw


def reserve_share(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=75)
        sh.base(cv, t, n=5)
        sh.share_blocks(cv, t, 0.57, t0=0.1, cols=10, rows=4, y=580, label="57%",
                        sub="OF THE WORLD'S CENTRAL BANK RESERVES ARE HELD IN DOLLARS",
                        seed=3)
        S.finish(cv)
    return draw


def priced_in_dollars(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=76)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["PRICED IN DOLLARS"], t0=0.0, x=960, y=240, size=104,
                    accent_line=0, seed=85, align_left=False)
        sh.cards(cv, t, ["OIL", "METALS", "SHIPPING"], t0=cue("Oil is priced in dollars") - 0.3,
                 y=680, w=400, h=300, size=62, seed=21, gap=0.18)
        S.finish(cv)
    return draw


def nigeria_vietnam(cue):
    def draw(cv, t):
        W = world()
        sh.map_shot(cv, t, W, ["NGA", "VNM"], highlight={"NGA": S.ACCENT, "VNM": S.ACCENT},
                    fill=0.62, lift_at=0.4, seed=11,
                    label=[(8.0, 9.0, "NIGERIA"), (106.0, 16.0, "VIETNAM")])
        a, b = W.point(8.0, 9.0), W.point(106.0, 16.0)
        sh.arrow(cv, t, cue("buying machinery from Vietnam") - 0.3, a, b, dur=1.2,
                 width=6.0 / max(cv.cam.zoom, 0.15), bow=0.3,
                 head=26 / max(cv.cam.zoom, 0.15))
        lab = S.cached(cv, "paid_usd", lambda r: S.title_strip(
            "PAID IN DOLLARS. NO AMERICAN INVOLVED.", r, 54, paper=S.ACCENT,
            ink="#fff8ee", seed=86))
        S.slap(cv, lab, 960, 940, t, cue("may well pay for it in dollars") - 0.2, -1.5, depth=0)
        S.finish(cv)
    return draw


def the_queue(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 9, seed=77)
        sh.base(cv, t, n=7)
        sh.headline(cv, t, ["A STANDING QUEUE", "FOR DOLLARS"], t0=0.05, x=960, y=280,
                    size=110, accent_line=1, seed=87, align_left=False)
        sh.ledger(cv, t, ["CENTRAL BANKS HOLD THEM", "EXPORTERS HOLD THEM",
                          "SAVERS HOLD THEM UNDER THE MATTRESS"],
                  t0=cue("Central banks hold them") - 0.3, x=430, y=640, step=130,
                  size=50, seed=22, numbered=False)
        S.finish(cv)
    return draw


def nobody_wanted(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=78)
        sh.base(cv, t, n=6, light=(0.5, 0.48))
        note = S.cached(cv, "zwnote2", lambda r: S.banknote(r, seed=1), 1.1)
        S.slap(cv, note, 960, 470, t, 0.1, -5, 1.25)
        st = S.cached(cv, "st_nobody", lambda r: P.stamp("NOBODY", r, 86, S.ACCENT, seed=88))
        S.slap(cv, st, 1060, 560, t, cue("Nobody") - 0.15, -12, depth=0, shadow=None,
               dur=0.25, spin=0)
        sub = S.cached(cv, "nb_sub", lambda r: P.label(
            "NOT ONE CENTRAL BANK HELD ZIMBABWE DOLLARS AS A RESERVE", r, 30, seed=89))
        S.slap(cv, sub, 960, 880, t, cue("Not a single central bank") - 0.3, 1.4,
               shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


ACT1 = [
    ("America printed trillions of dollars", same_action),
    ("let's be precise", be_precise),
    ("Between 2020 and 2022", fed_balance),
    ("Zimbabwe's currency went to zero", opposite_outcomes),
    ("Somebody else wants its money", somebody_wants_it),
    ("About fifty-seven percent", reserve_share),
    ("Oil is priced in dollars", priced_in_dollars),
    ("A company in Nigeria", nigeria_vietnam),
    ("That means every country on earth needs a stock of dollars", the_queue),
    ("Now ask the same question about the Zimbabwe dollar", nobody_wanted),
]


# ============================================================ ACT 2
def somewhere_to_park(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=79)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["YOU BUY", "US GOVERNMENT BONDS"], t0=0.05, x=960, y=300,
                    size=98, accent_line=1, seed=90, align_left=False)
        sh.ledger(cv, t, ["THEY PAY INTEREST",
                          "THEY ARE THE EASIEST ASSET ON EARTH TO SELL"],
                  t0=cue("They pay interest") - 0.3, x=470, y=700, step=140, size=52,
                  seed=23, numbered=False)
        S.finish(cv)
    return draw


def who_holds(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=80)
        sh.base(cv, t, n=5)
        sh.share_blocks(cv, t, 0.30, t0=0.1, cols=10, rows=4, y=560, label="30%",
                        sub="OF US PUBLIC DEBT IS HELD ABROAD", seed=5)
        S.finish(cv)
    return draw


def japan_china(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=81)
        sh.base(cv, t, n=5)
        sh.two_sided(cv, t,
                     "JAPAN\nTHE LARGEST\nFOREIGN HOLDER",
                     "CHINA\n$1.3tn IN 2013\nTO ABOUT $700bn",
                     t0=0.1, y=560, seed=24,
                     left_label="BUYING", right_label="SELLING DOWN")
        S.finish(cv)
    return draw


def no_queue(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=82)
        sh.base(cv, t, n=7, light=(0.5, 0.5))
        sh.headline(cv, t, ["ZIMBABWE", "HAD NO QUEUE"], t0=0.0, x=960, y=380, size=140,
                    accent_line=1, seed=91, align_left=False)
        sub = S.cached(cv, "nq_sub", lambda r: P.label(
            "ITS NEW MONEY WENT STRAIGHT INTO DOMESTIC PRICES", r, 32, seed=92))
        S.slap(cv, sub, 960, 790, t, cue("nowhere to go but straight into domestic prices") - 0.4,
               1.4, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


def money_vs_stuff(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=83)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["MONEY", "MEASURED AGAINST", "THE AMOUNT OF STUFF"],
                    t0=0.05, x=960, y=300, size=100, accent_line=2, seed=93, align_left=False)
        S.finish(cv)
    return draw


def two_economies(cue):
    us = [(0, 100), (1, 97), (2, 101), (3, 104), (4, 106)]
    zw = [(0, 100), (1, 86), (2, 64), (3, 44), (4, 29)]

    def draw(cv, t):
        sh.cam_drift(cv, t, 0.03, 11, seed=84)
        sh.base(cv, t, n=4)
        sh.line_chart(cv, t, us, t0=0.15, rect=(190, 420, 700, 300), color=S.KRAFT,
                      title="AMERICA KEPT PRODUCING", dur=1.8, seed=25, fill=False,
                      y_range=(0, 110))
        sh.line_chart(cv, t, zw, t0=cue("production was falling off a cliff") - 0.4,
                      rect=(1030, 420, 700, 300), color=S.ACCENT,
                      title="ZIMBABWE DID NOT", dur=1.8, seed=26, y_range=(0, 110))
        S.finish(cv)
    return draw


def already_dead(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=85)
        sh.base(cv, t, n=8, light=(0.5, 0.5))
        sh.headline(cv, t, ["A CURRENCY NOBODY", "WILL HOLD OVERNIGHT", "IS ALREADY DEAD"],
                    t0=0.05, x=960, y=320, size=106, accent_line=2, seed=94, align_left=False)
        sub = S.cached(cv, "ad_sub", lambda r: P.label(
            "IT JUST HAS NOT BEEN ANNOUNCED YET", r, 32, seed=95))
        S.slap(cv, sub, 960, 840, t, cue("It just has not been announced yet") - 0.4, 1.4,
               shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


ACT2 = [
    ("The other half is having somewhere safe to park it", somewhere_to_park),
    ("Foreign investors and governments hold roughly thirty percent", who_holds),
    ("Japan is the largest single foreign holder", japan_china),
    ("Zimbabwe had no queue", no_queue),
    ("Inflation is not really about the amount of money", money_vs_stuff),
    ("Through the pandemic, the American economy kept producing", two_economies),
    ("That is the accelerant", already_dead),
]


# ============================================================ ACT 3
def not_free(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 8, seed=86)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["NONE OF THIS", "MAKES IT FREE"], t0=0.05, x=960, y=380,
                    size=126, accent_line=1, seed=96, align_left=False)
        S.finish(cv)
    return draw


def us_inflation(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 9, seed=87)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "9.1%", label="US INFLATION, JUNE 2022", t0=0.05, y=470,
                    size=300, sub="THE HIGHEST IN FORTY YEARS", seed=27)
        t_g = cue("Groceries rose more than twelve percent")
        if t > t_g - 0.4:
            sp = S.cached(cv, "groc", lambda r: S.title_strip(
                "GROCERIES +12%", r, 70, seed=97))
            S.slap(cv, sp, 960, 900, t, t_g - 0.3, -1.5, depth=0)
        S.finish(cv)
    return draw


def bent_not_broken(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=88)
        sh.base(cv, t, n=7, light=(0.5, 0.5))
        sh.headline(cv, t, ["THE CURRENCY BENT.", "IT DID NOT BREAK."], t0=0.05,
                    x=960, y=400, size=128, accent_line=1, seed=98, align_left=False)
        S.finish(cv)
    return draw


def reserve_decline(cue):
    pts = [(0, 71), (1, 66), (2, 62), (3, 60), (4, 59), (5, 58), (6, 57)]

    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=89)
        sh.base(cv, t, n=5)
        sh.line_chart(cv, t, pts, t0=0.15, rect=(450, 380, 1020, 400),
                      title="THE DOLLAR'S SHARE OF RESERVES", dur=2.2, seed=28, y_range=(0, 100))
        t_d = cue("Today it is nearer fifty-seven")
        if t > t_d - 0.4:
            sh.big_stat(cv, t, "70% TO 57%", t0=t_d - 0.3, x=1150, y=915, size=118,
                        sub="SLOW, BUT REAL", seed=29)
        S.finish(cv)
    return draw


def reputation(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=90)
        sh.base(cv, t, n=8, light=(0.5, 0.5))
        sh.headline(cv, t, ["NOT A LAW OF PHYSICS.", "A REPUTATION."], t0=0.05,
                    x=960, y=380, size=124, accent_line=1, seed=99, align_left=False)
        sub = S.cached(cv, "rep_sub", lambda r: P.label("AND REPUTATIONS CAN BE SPENT", r, 34, seed=100))
        S.slap(cv, sub, 960, 790, t, cue("Reputations can be spent") - 0.3, 1.4,
               shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


def your_savings(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 10, seed=91)
        sh.base(cv, t, n=6, light=(0.5, 0.46))
        sh.two_sided(cv, t,
                     "A CURRENCY THE\nWORLD WANTS:\nINFLATION IS A TAX\nYOU PAY SLOWLY",
                     "A CURRENCY IT DOES NOT:\nYOUR SAVINGS CAN GO\nINSIDE ONE YEAR",
                     t0=0.1, y=560, seed=30,
                     left_label="SURVIVABLE", right_label="NOT SURVIVABLE")
        S.finish(cv)
    return draw


def lagos_cairo_colombo(cue):
    def draw(cv, t):
        W = world()
        sh.map_shot(cv, t, W, ["NGA", "EGY", "LKA", "USA"], fill=0.9, lift_at=0.5, seed=13,
                    highlight={"USA": S.ACCENT},
                    pins=[(3.4, 6.5, "LAGOS"), (31.2, 30.0, "CAIRO"), (79.9, 6.9, "COLOMBO")])
        lab = S.cached(cv, "wash", lambda r: S.title_strip(
            "A DECISION IN WASHINGTON", r, 56, seed=101))
        S.slap(cv, lab, 960, 940, t, cue("A decision made in Washington") - 0.3, -1.5, depth=0)
        S.finish(cv)
    return draw


def the_press_the_queue(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=92)
        sh.base(cv, t, n=8, light=(0.5, 0.5))
        sh.headline(cv, t, ["ZIMBABWE HAD", "THE PRESS."], t0=0.0, x=960, y=330,
                    size=116, accent_line=None, seed=102, align_left=False)
        sh.headline(cv, t, ["IT NEVER HAD", "THE QUEUE."],
                    t0=cue("It never had the queue") - 0.3, x=960, y=700, size=116,
                    accent_line=1, seed=103, align_left=False)
        S.finish(cv)
    return draw


def end_card(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.08, 7, seed=93)
        sh.base(cv, t, n=10, light=(0.5, 0.5))
        sh.headline(cv, t, ["HOW ZIMBABWE", "GOT THERE"], t0=0.0, x=960, y=400, size=130,
                    accent_line=1, seed=104, align_left=False)
        sub = S.cached(cv, "wn_sub", lambda r: P.label("WATCH NEXT →", r, 40, seed=105))
        S.slap(cv, sub, 960, 790, t, 0.5, 1.5, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


ACT3 = [
    ("None of this makes printing free", not_free),
    ("In June 2022", us_inflation),
    ("Painful, expensive, politically brutal", bent_not_broken),
    ("At the start of this century", reserve_decline),
    ("That exorbitant privilege is not a law of physics", reputation),
    ("So here is the practical version", your_savings),
    ("And it works the other way too", lagos_cairo_colombo),
    ("The printing press is not the thing that matters", the_press_the_queue),
    ("If you want to see what that looks like from the inside", end_card),
]

SHOTS = {1: ACT1, 2: ACT2, 3: ACT3}
