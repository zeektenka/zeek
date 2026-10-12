"""Video 1, Act 3 (surrender, the aftermath, and the hand-off to Video 10)."""
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


def surrender(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=50)
        sh.base(cv, t, n=7, light=(0.5, 0.48))
        sh.headline(cv, t, ["NOT A POLICY.", "A SURRENDER."], t0=0.05, x=960, y=400,
                    size=140, accent_line=1, seed=60, align_left=False)
        S.finish(cv)
    return draw


def dollarisation(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 10, seed=51)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["EARLY 2009:", "IT GAVE UP", "ITS OWN CURRENCY"], t0=0.0,
                    x=520, y=260, size=86, accent_line=2, seed=61)
        sh.cards(cv, t, [("US DOLLAR", "ACCEPTED"), ("SA RAND", "ACCEPTED")],
                 t0=cue("let people use U.S. dollars") - 0.3, y=780, w=440, h=300,
                 size=52, seed=12, spread=1040)
        t_i = cue("Inflation stopped almost immediately")
        st = S.cached(cv, "st_stop", lambda r: P.stamp("INFLATION STOPS", r, 50, S.ACCENT, seed=62))
        S.slap(cv, st, 1460, 320, t, t_i - 0.2, -11, depth=0, shadow=None, dur=0.25, spin=0)
        S.finish(cv)
    return draw


def the_cost(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 8, seed=52)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["THE PRICE:", "CONTROL OF", "ITS OWN MONEY"], t0=0.0,
                    x=960, y=300, size=100, accent_line=2, seed=63, align_left=False)
        S.finish(cv)
    return draw


def currencies_since(cue):
    """A timeline of attempts — the real cost is that trust never came back."""
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.04, 11, seed=53)
        sh.base(cv, t, n=6)
        sh.headline(cv, t, ["AND SINCE THEN"], t0=0.0, x=960, y=220, size=86,
                    accent_line=None, seed=64, align_left=False)
        items = [("2016", "BOND NOTES"), ("2019", "A NEW ZIM DOLLAR"), ("2024", "THE ZiG")]
        sh.cards(cv, t, items, t0=cue("Bond notes in 2016") - 0.3, y=620, w=400, h=320,
                 size=72, seed=13, gap=0.5, spread=1420)
        sub = S.cached(cv, "zig_sub", lambda r: P.label(
            "BACKED BY GOLD AND HARD CURRENCY — BECAUSE A PROMISE ALONE WAS NOT ENOUGH",
            r, 28, seed=65))
        S.slap(cv, sub, 960, 900, t, cue("backed by gold and hard currency") - 0.3, 1.2,
               shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


def eighty_percent(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.05, 8, seed=54)
        sh.base(cv, t, n=5)
        sh.big_stat(cv, t, "80%+", label="OF TRANSACTIONS TODAY", t0=0.05, y=480,
                    size=300, sub="STILL IN FOREIGN CURRENCY", seed=18)
        S.finish(cv)
    return draw


def trust(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.07, 8, seed=55)
        sh.base(cv, t, n=8, light=(0.5, 0.5))
        sh.headline(cv, t, ["A COUNTRY CAN LOSE", "THE ABILITY", "TO BE BELIEVED"],
                    t0=0.0, x=960, y=300, size=100, accent_line=2, seed=66, align_left=False)
        sub = S.cached(cv, "trust_sub", lambda r: P.label(
            "AND MAY NOT GET IT BACK IN A GENERATION", r, 32, seed=67))
        S.slap(cv, sub, 960, 820, t, 0.6, 1.4, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


def everyone_prints(cue):
    def draw(cv, t):
        W = world()
        sh.map_shot(cv, t, W, ["USA", "CHN", "RUS", "BRA", "ZAF"], fill=0.95, lift_at=0.5,
                    seed=9, highlight={"USA": S.ACCENT, "GBR": S.KRAFT, "JPN": S.KRAFT,
                                       "DEU": S.KRAFT, "FRA": S.KRAFT})
        lab = S.cached(cv, "ep", lambda r: S.title_strip(
            "THEY ALL PRINTED. THEIRS DIDN'T COLLAPSE.", r, 58, seed=68))
        S.slap(cv, lab, 960, 930, t, cue("The United States created trillions") - 0.3,
               -1.5, depth=0)
        S.finish(cv)
    return draw


def the_question(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.06, 9, seed=56)
        sh.base(cv, t, n=7)
        sh.headline(cv, t, ["WHO TRUSTS YOU.", "WHAT YOU SELL.", "WHO NEEDS YOUR MONEY."],
                    t0=cue("It is a question about who trusts you") - 0.3, x=480, y=320,
                    size=92, accent_line=2, seed=69)
        S.finish(cv)
    return draw


def end_card(cue):
    def draw(cv, t):
        sh.cam_drift(cv, t, 0.08, 7, seed=57)
        sh.base(cv, t, n=10, light=(0.5, 0.5))
        sh.headline(cv, t, ["WHY THE US CAN", "PRINT MONEY", "AND ZIMBABWE CAN'T"],
                    t0=0.0, x=960, y=330, size=104, accent_line=1, seed=70, align_left=False)
        sub = S.cached(cv, "next_sub", lambda r: P.label("NEXT →", r, 40, seed=71))
        S.slap(cv, sub, 960, 830, t, 0.5, 1.5, shadow=S.SHADOW_LOW)
        S.finish(cv)
    return draw


SHOTS = [
    ("What ended it was not a clever policy", surrender),
    ("In early 2009, Zimbabwe gave up", dollarisation),
    ("But it cost Zimbabwe something", the_cost),
    ("And the story did not end there", currencies_since),
    ("more than eighty percent of transactions", eighty_percent),
    ("That is the real cost", trust),
    ("Every government on earth can create money", everyone_prints),
    ("That is not a question about printing presses", the_question),
    ("That is the next video", end_card),
]
