"""
SPARK - a 60-second Maya animated short (1440 frames @ 24 fps)

Story
-----
A little scrap-robot named Bolt sleeps alone in a dark field under the moon.
A falling star crashes nearby. Bolt wakes, walks over and picks it up - but the
star is dying, its light fading in his hands. Bolt opens his chest and gives the
star his own glowing core. His eye goes dark. The star, reborn, rises home into
the sky... and the whole night sky lights up in thanks. One tiny star drifts
back down and settles into Bolt's chest. He wakes, and waves goodbye.

Beat sheet (seconds / frames)
  00-08s   1-192   Establishing: moonlit field, Bolt asleep.
  08-16s 192-384   A shooting star streaks across and crashes. Bolt wakes.
  16-28s 384-672   Bolt walks to the crater.
  28-36s 672-864   He lifts the star - its light fades.
  36-44s 864-1056  He opens his chest and gives it his core. His eye goes dark.
  44-54s 1056-1296 The star rises home; the sky fills with stars; one returns.
  54-60s 1296-1440 Bolt glows again and waves. Camera pulls back. The End.

Usage
-----
Maya 2022+ (Python 3). Open the Script Editor (Python tab), paste or source
this file and run. It builds the full scene in a new file, then:
    playblast_story("C:/temp/spark.mov")   # quick viewport movie
or render the "shotCam" camera with Arnold for final quality.
"""

import math
import maya.cmds as cmds

FPS = 24
END = 60 * FPS  # 1440


def sec(s):
    return int(round(s * FPS)) + 1


# --------------------------------------------------------------------------- helpers
def material(name, color, incandescence=(0, 0, 0)):
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.setAttr(shader + ".color", *color, type="double3")
    cmds.setAttr(shader + ".incandescence", *incandescence, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader", force=True)
    return shader, sg


def assign(obj, sg):
    cmds.sets(obj, edit=True, forceElement=sg)


def key(obj, attr, frame, value, tangent="auto"):
    cmds.setKeyframe(obj, attribute=attr, time=frame, value=value,
                     inTangentType=tangent, outTangentType=tangent)


def key_glow(shader, frame, rgb):
    for ch, v in zip("RGB", rgb):
        key(shader, "incandescence" + ch, frame, v)


def key_xyz(obj, attr, frame, xyz, tangent="auto"):
    for axis, v in zip("XYZ", xyz):
        key(obj, attr + axis, frame, v, tangent)


# --------------------------------------------------------------------------- scene setup
def setup_scene():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film", linear="cm")
    cmds.playbackOptions(minTime=1, maxTime=END, animationStartTime=1, animationEndTime=END)
    cmds.setAttr("defaultResolution.width", 1280)
    cmds.setAttr("defaultResolution.height", 720)
    cmds.setAttr("defaultResolution.deviceAspectRatio", 1280.0 / 720.0)


def build_world():
    _, ground_sg = material("groundMat", (0.05, 0.08, 0.14))
    ground = cmds.polyPlane(name="ground", width=600, height=400, sx=40, sy=30)[0]
    # gentle rolling hills
    verts = cmds.ls(ground + ".vtx[*]", flatten=True)
    for v in verts:
        x, _, z = cmds.pointPosition(v, world=True)
        y = 2.5 * math.sin(x * 0.03) * math.cos(z * 0.04) + (max(0, -z - 60) * 0.25)
        cmds.move(0, y, 0, v, relative=True)
    assign(ground, ground_sg)

    # crater where the star lands
    _, crater_sg = material("craterMat", (0.02, 0.03, 0.05))
    crater = cmds.polyTorus(name="crater", radius=7, sectionRadius=1.6, sx=24, sy=8)[0]
    cmds.move(30, 0.2, 0, crater)
    cmds.scale(1, 0.35, 1, crater)
    assign(crater, crater_sg)

    # moon
    _, moon_sg = material("moonMat", (0.9, 0.9, 0.8), (0.85, 0.85, 0.7))
    moon = cmds.polySphere(name="moon", radius=18)[0]
    cmds.move(-120, 140, -260, moon)
    assign(moon, moon_sg)

    # moonlight + fill
    moon_light = cmds.directionalLight(name="moonLight", intensity=0.6, rgb=(0.55, 0.65, 1.0))
    cmds.xform(cmds.listRelatives(moon_light, parent=True)[0], rotation=(-40, -30, 0))
    cmds.ambientLight(name="nightFill", intensity=0.12, rgb=(0.3, 0.35, 0.6))

    # a few junk props so the field feels lived in
    _, junk_sg = material("junkMat", (0.18, 0.14, 0.12))
    for i, (x, z, s) in enumerate([(-55, -20, 4), (-12, -35, 3), (60, -25, 5), (75, 15, 2.5)]):
        junk = cmds.polyCube(name="junk%d" % i, width=s, height=s * 0.7, depth=s)[0]
        cmds.move(x, s * 0.3, z, junk)
        cmds.rotate(0, i * 37, 8, junk)
        assign(junk, junk_sg)


def build_stars():
    """Base star field (always on) + 'thank-you' stars that bloom at 46-51s."""
    _, star_sg = material("skyStarMat", (1, 1, 1), (1, 1, 0.9))
    base, bloom = [], []
    rnd = _lcg(7)
    for i in range(220):
        theta = rnd() * math.pi * 1.1 - math.pi * 0.55
        phi = 0.15 + rnd() * 1.2
        r = 320
        x, y, z = r * math.sin(theta) * math.cos(phi), 20 + r * math.sin(phi), -r * math.cos(theta) * math.cos(phi)
        star = cmds.polySphere(name="skyStar%d" % i, radius=0.6 + rnd() * 0.9, sx=6, sy=4)[0]
        cmds.move(x, y, z, star)
        assign(star, star_sg)
        (base if i < 70 else bloom).append(star)
    cmds.group(base, name="baseStars_grp")
    cmds.group(bloom, name="bloomStars_grp")
    for i, star in enumerate(bloom):
        start = sec(46) + int(rnd() * 5 * FPS)
        key(star, "scaleX", 1, 0); key(star, "scaleY", 1, 0); key(star, "scaleZ", 1, 0)
        for a in "XYZ":
            key(star, "scale" + a, start, 0)
            key(star, "scale" + a, start + 8, 1.6)
            key(star, "scale" + a, start + 16, 1.0)


def _lcg(seed):
    state = [seed]

    def rnd():
        state[0] = (state[0] * 1103515245 + 12345) % (2 ** 31)
        return state[0] / float(2 ** 31)
    return rnd


# --------------------------------------------------------------------------- Bolt
def build_bolt():
    _, metal_sg = material("boltMetal", (0.75, 0.42, 0.18))
    _, dark_sg = material("boltDark", (0.12, 0.12, 0.14))
    eye_shader, eye_sg = material("boltEye", (0.2, 0.8, 1.0))
    core_shader, core_sg = material("boltCore", (1.0, 0.75, 0.3))

    body = cmds.polyCube(name="bolt_body", width=6, height=7, depth=5)[0]
    cmds.polyBevel3(body, offset=0.6, segments=3)
    cmds.move(0, 7.5, 0, body)
    assign(body, metal_sg)

    chest_door = cmds.polyCube(name="bolt_chestDoor", width=3, height=3, depth=0.4)[0]
    cmds.move(0, 8, 2.6, chest_door)
    cmds.xform(chest_door, pivots=(0, 9.5, 2.6), worldSpace=True)  # hinge at top
    assign(chest_door, dark_sg)

    core = cmds.polySphere(name="bolt_core", radius=1.0)[0]
    cmds.move(0, 8, 2.1, core)
    assign(core, core_sg)

    head = cmds.polyCube(name="bolt_head", width=5, height=4, depth=4.5)[0]
    cmds.polyBevel3(head, offset=0.5, segments=3)
    cmds.move(0, 13.2, 0, head)
    assign(head, metal_sg)
    eye = cmds.polySphere(name="bolt_eye", radius=1.1)[0]
    cmds.move(0, 13.4, 2.1, eye)
    cmds.scale(1, 1, 0.5, eye)
    assign(eye, eye_sg)
    antenna = cmds.polyCylinder(name="bolt_antenna", radius=0.15, height=2.5)[0]
    cmds.move(0, 16.4, 0, antenna)
    assign(antenna, dark_sg)
    tip = cmds.polySphere(name="bolt_antennaTip", radius=0.4)[0]
    cmds.move(0, 17.7, 0, tip)
    assign(tip, eye_sg)
    head_grp = cmds.group(head, eye, antenna, tip, name="bolt_head_grp")
    cmds.xform(head_grp, pivots=(0, 11.2, 0), worldSpace=True)  # neck

    limbs = {}
    for side, sx in (("L", 1), ("R", -1)):
        arm = cmds.polyCylinder(name="bolt_arm" + side, radius=0.55, height=5)[0]
        cmds.move(sx * 3.7, 8.2, 0, arm)
        hand = cmds.polySphere(name="bolt_hand" + side, radius=0.85)[0]
        cmds.move(sx * 3.7, 5.5, 0, hand)
        assign(arm, dark_sg); assign(hand, metal_sg)
        arm_grp = cmds.group(arm, hand, name="bolt_arm%s_grp" % side)
        cmds.xform(arm_grp, pivots=(sx * 3.7, 10.5, 0), worldSpace=True)  # shoulder

        leg = cmds.polyCylinder(name="bolt_leg" + side, radius=0.7, height=4)[0]
        cmds.move(sx * 1.6, 2.2, 0, leg)
        foot = cmds.polyCube(name="bolt_foot" + side, width=1.8, height=0.8, depth=2.6)[0]
        cmds.move(sx * 1.6, 0.4, 0.4, foot)
        assign(leg, dark_sg); assign(foot, metal_sg)
        leg_grp = cmds.group(leg, foot, name="bolt_leg%s_grp" % side)
        cmds.xform(leg_grp, pivots=(sx * 1.6, 4.2, 0), worldSpace=True)  # hip
        limbs[side] = (arm_grp, leg_grp)

    torso = cmds.group(body, chest_door, core, head_grp,
                       limbs["L"][0], limbs["R"][0], name="bolt_torso_grp")
    cmds.xform(torso, pivots=(0, 4.2, 0), worldSpace=True)
    root = cmds.group(torso, limbs["L"][1], limbs["R"][1], name="bolt_root")

    core_light = cmds.pointLight(name="bolt_coreLight", intensity=0.0, rgb=(1, 0.75, 0.35))
    core_light_t = cmds.listRelatives(core_light, parent=True)[0]
    cmds.move(0, 8, 3.5, core_light_t)
    cmds.parent(core_light_t, torso)

    return dict(root=root, torso=torso, head=head_grp, door=chest_door, core=core,
                core_shader=core_shader, eye_shader=eye_shader, core_light=core_light,
                armL=limbs["L"][0], armR=limbs["R"][0], legL=limbs["L"][1], legR=limbs["R"][1])


# --------------------------------------------------------------------------- the falling star
def build_star():
    shader, sg = material("fallenStarMat", (1, 0.95, 0.6), (1, 0.9, 0.5))
    star = cmds.polyPlatonicSolid(name="fallenStar", radius=1.6, solidType=0)[0]  # dodecahedron
    assign(star, sg)
    light = cmds.pointLight(name="fallenStarLight", intensity=0, rgb=(1, 0.9, 0.55))
    light_t = cmds.listRelatives(light, parent=True)[0]
    cmds.parent(light_t, star, relative=True)
    return star, shader, light


# --------------------------------------------------------------------------- animation
def walk_cycle(bolt, start, end, x0, x1):
    step = 12  # frames per step
    key(bolt["root"], "translateX", start, x0, "linear")
    key(bolt["root"], "translateX", end, x1, "linear")
    f, phase = start, 1
    while f <= end:
        swing = 25 * phase
        key(bolt["legL"], "rotateX", f, swing)
        key(bolt["legR"], "rotateX", f, -swing)
        key(bolt["armL"], "rotateX", f, -swing * 0.8)
        key(bolt["armR"], "rotateX", f, swing * 0.8)
        key(bolt["torso"], "translateY", f, 0)
        key(bolt["torso"], "translateY", f + step // 2, 0.5)
        f += step
        phase *= -1
    for limb in ("legL", "legR", "armL", "armR"):
        key(bolt[limb], "rotateX", end + 6, 0)
    key(bolt["torso"], "translateY", end + 6, 0)


def animate(bolt, star, star_shader, star_light):
    root, torso, head = bolt["root"], bolt["torso"], bolt["head"]
    dim, glow_eye, off = (0, 0, 0), (0.2, 0.85, 1.0), (0.02, 0.02, 0.03)
    warm, faint = (1.0, 0.75, 0.3), (0.15, 0.1, 0.05)

    # ---- 0-8s asleep: slumped, eye off, slow "breathing" core
    cmds.rotate(0, 90, 0, root)  # face +X toward the crater
    key(root, "rotateY", 1, 90)
    key(root, "translateX", 1, -30)
    key(torso, "rotateX", 1, 18)
    key(head, "rotateX", 1, 25)
    key_glow(bolt["eye_shader"], 1, off)
    for i, f in enumerate(range(1, sec(9), 36)):
        key_glow(bolt["core_shader"], f, warm if i % 2 else (0.6, 0.4, 0.15))
        key(bolt["core_light"], "intensity", f, 1.2 if i % 2 else 0.6)

    # ---- 8-16s shooting star + wake up
    key_xyz(star, "translate", 1, (-140, 160, -160))
    key_xyz(star, "translate", sec(8.4), (-140, 160, -160), "linear")
    key_xyz(star, "translate", sec(10.8), (30, 1.5, 0), "linear")
    key(star_light, "intensity", sec(8.4), 2.0)
    key(star_light, "intensity", sec(10.8), 8.0)   # impact flash
    key(star_light, "intensity", sec(11.6), 2.5)
    key_glow(star_shader, sec(10.8), (1, 0.95, 0.6))

    key(torso, "rotateX", sec(11.5), 18)
    key(torso, "rotateX", sec(12.5), -6)
    key(torso, "rotateX", sec(13.2), 0)
    key(head, "rotateX", sec(11.5), 25)
    key(head, "rotateX", sec(12.3), -10)
    key(head, "rotateX", sec(13.5), 0)
    key_glow(bolt["eye_shader"], sec(11.8), off)
    key_glow(bolt["eye_shader"], sec(12.0), glow_eye)   # blink on
    key_glow(bolt["eye_shader"], sec(12.4), off)
    key_glow(bolt["eye_shader"], sec(12.6), glow_eye)
    key(head, "rotateY", sec(13.5), 0)
    key(head, "rotateY", sec(14.3), 25)   # curious tilt
    key(head, "rotateZ", sec(14.3), 12)
    key(head, "rotateY", sec(15.5), 0)
    key(head, "rotateZ", sec(15.5), 0)
    key_glow(bolt["core_shader"], sec(9), warm)
    key(bolt["core_light"], "intensity", sec(9), 1.2)

    # ---- 16-28s walk to the crater
    walk_cycle(bolt, sec(16), sec(27), -30, 23)

    # ---- 28-36s lift the star, it fades
    key_xyz(star, "translate", sec(28.5), (30, 1.5, 0))
    key(torso, "rotateX", sec(28), 0)
    key(torso, "rotateX", sec(29.5), 30)           # bend down toward the star
    for arm in ("armL", "armR"):
        key(bolt[arm], "rotateX", sec(28.5), 0)
        key(bolt[arm], "rotateX", sec(29.5), -60)
        key(bolt[arm], "rotateX", sec(31.5), -80)
    key(torso, "rotateX", sec(31.5), 0)
    key_xyz(star, "translate", sec(29.5), (30, 1.5, 0))
    key_xyz(star, "translate", sec(31.5), (27, 9.5, 0))  # cradled in front of chest
    key(star_light, "intensity", sec(30), 2.5)
    key(star_light, "intensity", sec(35.5), 0.15)
    key_glow(star_shader, sec(30), (1, 0.95, 0.6))
    key_glow(star_shader, sec(35.5), (0.12, 0.1, 0.08))
    key(head, "rotateX", sec(32), 0)
    key(head, "rotateX", sec(34), 20)               # looks down, sad

    # ---- 36-44s give the core
    key(bolt["door"], "rotateX", sec(36.5), 0)
    key(bolt["door"], "rotateX", sec(38), -110)     # chest swings open
    key_xyz(bolt["core"], "translate", sec(38), (0, 0, 0))
    key_xyz(bolt["core"], "translate", sec(40.5), (0, 1.5, 3.2))  # floats into the star (local)
    key_glow(bolt["core_shader"], sec(40.5), warm)
    key_glow(bolt["core_shader"], sec(41), dim)
    for a in "XYZ":
        key(bolt["core"], "scale" + a, sec(40.4), 1)
        key(bolt["core"], "scale" + a, sec(41), 0)
    key(star_light, "intensity", sec(40.5), 0.15)
    key(star_light, "intensity", sec(41.5), 6.0)
    key_glow(star_shader, sec(40.5), (0.12, 0.1, 0.08))
    key_glow(star_shader, sec(41.5), (1, 0.95, 0.65))
    key(bolt["core_light"], "intensity", sec(40.5), 1.2)
    key(bolt["core_light"], "intensity", sec(41.5), 0)
    key_glow(bolt["eye_shader"], sec(41.5), glow_eye)
    key_glow(bolt["eye_shader"], sec(43), off)     # Bolt goes dark
    key(torso, "rotateX", sec(41.5), 0)
    key(torso, "rotateX", sec(43.5), 20)
    for arm in ("armL", "armR"):
        key(bolt[arm], "rotateX", sec(43), -80)
        key(bolt[arm], "rotateX", sec(44.5), 0)

    # ---- 44-54s the star rises, the sky answers, one returns
    key_xyz(star, "translate", sec(44), (27, 9.5, 0))
    key_xyz(star, "translate", sec(50), (-20, 210, -300))
    for a in "XYZ":
        key(star, "scale" + a, sec(44), 1)
        key(star, "scale" + a, sec(50), 3)

    gift, gift_shader, gift_light = build_star()
    gift = cmds.rename(gift, "giftStar")
    for a in "XYZ":
        key(gift, "scale" + a, 1, 0.4)
    key_xyz(gift, "translate", 1, (60, 220, -300))
    key_xyz(gift, "translate", sec(50.5), (60, 220, -300))
    key_xyz(gift, "translate", sec(52), (40, 40, -40))
    key_xyz(gift, "translate", sec(53.2), (25.5, 8, 0))
    key(gift_light, "intensity", sec(50.5), 1.5)
    key(gift_light, "intensity", sec(53.2), 1.5)
    key(gift_light, "intensity", sec(53.5), 0)
    for a in "XYZ":
        key(gift, "scale" + a, sec(53.2), 0.4)
        key(gift, "scale" + a, sec(53.5), 0)

    key(bolt["door"], "rotateX", sec(52.5), -110)
    key(bolt["door"], "rotateX", sec(54), 0)
    for a in "XYZ":
        key(bolt["core"], "scale" + a, sec(53.2), 0)
        key(bolt["core"], "scale" + a, sec(53.6), 1)
    key_xyz(bolt["core"], "translate", sec(53.2), (0, 0, 0))
    key_glow(bolt["core_shader"], sec(53.2), dim)
    key_glow(bolt["core_shader"], sec(53.6), warm)
    key(bolt["core_light"], "intensity", sec(53.2), 0)
    key(bolt["core_light"], "intensity", sec(53.8), 1.5)
    key_glow(bolt["eye_shader"], sec(53.6), off)
    key_glow(bolt["eye_shader"], sec(54.2), glow_eye)
    key(torso, "rotateX", sec(53.5), 20)
    key(torso, "rotateX", sec(54.3), 0)
    key(head, "rotateX", sec(53.5), 20)
    key(head, "rotateX", sec(54.5), -25)            # looks up at the sky

    # ---- 54-60s wave goodbye
    key(bolt["armR"], "rotateZ", sec(54.5), 0)
    key(bolt["armR"], "rotateZ", sec(55.3), -150)
    for i in range(6):
        key(bolt["armR"], "rotateX", sec(55.3) + i * 8, 20 if i % 2 else -20)
    key(bolt["armR"], "rotateZ", sec(59.5), -150)


def build_camera():
    cam, cam_shape = cmds.camera(name="shotCam", focalLength=35)
    cam = cmds.rename(cam, "shotCam")
    shots = [  # time, translate, rotate
        (0,    (-30, 25, 120), (-6, 0, 0)),
        (7.5,  (-26, 16, 55),  (-6, 0, 0)),     # slow push on sleeping Bolt
        (8.2,  (-10, 30, 140), (2, 0, 0)),      # wide: see the star fall
        (10.8, (-10, 30, 140), (2, 0, 0)),
        (11.2, (-36, 15, 30),  (-5, -10, 0)),   # close on Bolt waking
        (15.8, (-36, 15, 30),  (-5, -10, 0)),
        (16,   (-20, 18, 70),  (-5, 0, 0)),     # tracking walk
        (27,   (22, 18, 70),   (-5, 0, 0)),
        (28,   (40, 14, 32),   (-8, 18, 0)),    # over-shoulder pick-up
        (36,   (36, 12, 26),   (-4, 14, 0)),
        (36.2, (26, 12, 22),   (-2, 0, 0)),     # close: chest opens
        (44,   (26, 11, 20),   (-2, 0, 0)),
        (44.2, (10, 6, 50),    (25, 20, 0)),    # low angle: star rises
        (50,   (0, 4, 60),     (40, 20, 0)),
        (50.5, (12, 10, 45),   (8, 12, 0)),     # gift descends
        (54,   (18, 11, 32),   (2, 6, 0)),
        (54.5, (18, 11, 32),   (2, 6, 0)),
        (60,   (10, 40, 160),  (-2, 0, 0)),     # final pull back
    ]
    for t, tr, ro in shots:
        key_xyz(cam, "translate", sec(t), tr, "linear")
        key_xyz(cam, "rotate", sec(t), ro, "linear")
    # keys less than a second apart are hard cuts: hold the earlier key until the next
    for (t0, _, _), (t1, _, _) in zip(shots, shots[1:]):
        if t1 - t0 < 1.0:
            cmds.keyTangent(cam, attribute=["translate", "rotate"],
                            time=(sec(t0), sec(t0)), outTangentType="step")
    return cam


def playblast_story(path, width=1280, height=720):
    """Viewport movie of the full 60 s through shotCam."""
    panel = cmds.getPanel(withFocus=True)
    if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
        cmds.modelPanel(panel, edit=True, camera="shotCam")
        cmds.modelEditor(panel, edit=True, displayLights="all", grid=False)
    cmds.playblast(filename=path, startTime=1, endTime=END, forceOverwrite=True,
                   format="qt", compression="H.264", percent=100,
                   widthHeight=(width, height), showOrnaments=False, viewer=True)


def build():
    setup_scene()
    build_world()
    build_stars()
    bolt = build_bolt()
    star, star_shader, star_light = build_star()
    animate(bolt, star, star_shader, star_light)
    build_camera()
    cmds.currentTime(1)
    cmds.lookThru("shotCam")
    print("SPARK built: %d frames @ %d fps. Run playblast_story(path) or render shotCam." % (END, FPS))


if __name__ == "__main__":
    build()
