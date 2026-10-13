"""
SPARK in full 3D, built and rendered with Blender's Python module (bpy).

Same story and timing as spark_story.py (the Maya version); the pose and timing
curves are shared with render_preview.py so all versions stay in sync.

    pip install bpy pillow numpy          # bpy 4.2+ / 5.x, Python version must match the bpy wheel
    python blender_spark.py build                      # -> spark_3d.blend (fully keyed, 1440 frames)
    python blender_spark.py render START END           # -> frames_3d/####.png for that frame range
    python blender_spark.py finish                     # -> spark_3d.mp4 (bloom, titles, captions, music)

Run several `render` processes with different ranges to use more CPU cores.
"""

import math
import os
import subprocess
import sys

import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_preview as story  # noqa: E402  (shared timing: robot_pose, robot_x, subtitle, music)

FPS, FRAMES = 24, 1440
BLEND = os.path.join(HERE, "spark_3d.blend")
FRAME_DIR = os.path.join(HERE, "frames_3d")
STAR_X = 2.5
STAR_HOME = Vector((-6.0, 55.0, 48.0))  # where the fallen star rejoins the sky


def smooth(t):
    return story.smooth(t)


def vlerp(a, b, k):
    return Vector(a).lerp(Vector(b), k)


# ============================================================================ materials


def principled(name, color, metallic=0.0, roughness=0.5, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def emissive(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return mat


def strength_socket(mat):
    nodes = mat.node_tree.nodes
    if "Emission" in nodes:
        return nodes["Emission"].inputs["Strength"]
    return nodes["Principled BSDF"].inputs["Emission Strength"]


# ============================================================================ mesh helpers


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.empty_display_size = 0.1
    return link(e, parent)


def prim(kind, name, mat, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), parent=None, bevel=0.0, **kw):
    ops = {
        "cube": bpy.ops.mesh.primitive_cube_add,
        "sphere": bpy.ops.mesh.primitive_uv_sphere_add,
        "ico": bpy.ops.mesh.primitive_ico_sphere_add,
        "cyl": bpy.ops.mesh.primitive_cylinder_add,
        "torus": bpy.ops.mesh.primitive_torus_add,
        "cone": bpy.ops.mesh.primitive_cone_add,
    }
    ops[kind](**kw)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.rotation_euler = rot
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        m = obj.modifiers.new("bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        m.limit_method = "ANGLE"
    if kind in ("sphere", "ico", "torus", "cyl", "cone") or bevel:
        bpy.ops.object.shade_smooth()
        if bevel or kind in ("cyl", "cone"):
            try:
                bpy.ops.object.shade_auto_smooth()
            except Exception:
                pass
    obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    obj.location = loc
    return obj


def star_mesh(name, mat, r_out=0.16, r_in=0.07, depth=0.07):
    """Chunky five-pointed star."""
    verts, faces = [(0, 0, depth), (0, 0, -depth)], []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi / 2 + i * math.pi / 5
        verts.append((r * math.cos(a), r * math.sin(a), 0))
    for i in range(10):
        a, b = 2 + i, 2 + (i + 1) % 10
        faces += [(0, a, b), (1, b, a)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    obj.rotation_euler = (math.pi / 2, 0, 0)  # face the camera side (-Y)
    return link(obj)


def ground_height(x, y):
    h = 0.06 * math.sin(x * 0.9) * math.cos(y * 0.7) + 0.04 * math.sin(x * 2.3 + y * 1.7)
    h += max(0.0, y - 10) ** 1.3 * 0.03 + max(0.0, -y - 18) * 0.08  # low hills behind / beyond
    h += 0.6 * math.sin(x * 0.12 + 1.0) * smooth((y - 14) / 10)
    d = math.hypot(x - STAR_X, y)
    if d < 0.9:  # crater
        h -= 0.12 * math.cos(d / 0.9 * math.pi / 2) ** 2
    elif d < 1.3:
        h += 0.05 * math.sin((d - 0.9) / 0.4 * math.pi)
    return h


def build_ground(mat):
    n, size = 220, 90.0
    verts = []
    for j in range(n + 1):
        for i in range(n + 1):
            # denser near the action: warp the grid toward the origin
            u, v = i / n * 2 - 1, j / n * 2 - 1
            x = math.copysign(abs(u) ** 1.8, u) * size
            y = math.copysign(abs(v) ** 1.8, v) * size + 2
            verts.append((x, y, ground_height(x, y)))
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i)
             for j in range(n) for i in range(n)]
    me = bpy.data.meshes.new("ground")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new("ground", me)
    me.materials.append(mat)
    return link(obj)


# ============================================================================ world / sky


def build_world():
    world = bpy.data.worlds.new("NightSky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

    coord = N("ShaderNodeTexCoord")
    sep = N("ShaderNodeSeparateXYZ")
    L(coord.outputs["Generated"], sep.inputs[0])
    ramp = N("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.035, 0.025, 0.07, 1)
    cr.elements[1].position, cr.elements[1].color = 0.45, (0.004, 0.006, 0.022, 1)
    e = cr.elements.new(0.08)
    e.color = (0.05, 0.035, 0.1, 1)
    L(sep.outputs["Z"], ramp.inputs[0])

    def star_layer(scale, size, seed):
        vor = N("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        if "Randomness" in vor.inputs:
            vor.inputs["Randomness"].default_value = 1.0
        mapping = N("ShaderNodeMapping")
        mapping.inputs["Location"].default_value = (seed, seed * 2, seed * 3)
        L(coord.outputs["Generated"], mapping.inputs[0])
        L(mapping.outputs[0], vor.inputs["Vector"])
        dot = N("ShaderNodeMath")
        dot.operation = "LESS_THAN"
        dot.inputs[1].default_value = size
        L(vor.outputs["Distance"], dot.inputs[0])
        # random brightness per star
        mul = N("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        sepc = N("ShaderNodeSeparateColor")
        L(vor.outputs["Color"], sepc.inputs[0])
        L(dot.outputs[0], mul.inputs[0])
        L(sepc.outputs[0], mul.inputs[1])
        return mul

    base = star_layer(140, 0.045, 0.0)
    bloom = star_layer(260, 0.06, 7.3)

    # bloom stars appear in a ring that grows outward from STAR_HOME: mask = clamp((radius - angle) * 4)
    home = STAR_HOME.normalized()
    dirn = N("ShaderNodeVectorMath")
    dirn.operation = "NORMALIZE"
    L(coord.outputs["Generated"], dirn.inputs[0])
    dot = N("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = tuple(home)
    L(dirn.outputs[0], dot.inputs[0])
    radius = N("ShaderNodeValue")
    radius.name = "BloomRadius"
    radius.outputs[0].default_value = -2.0
    sub = N("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    L(dot.outputs["Value"], sub.inputs[0])
    L(radius.outputs[0], sub.inputs[1])
    clamp = N("ShaderNodeMath")
    clamp.operation = "MULTIPLY"
    clamp.use_clamp = True
    clamp.inputs[1].default_value = 6.0
    L(sub.outputs[0], clamp.inputs[0])
    bloom_masked = N("ShaderNodeMath")
    bloom_masked.operation = "MULTIPLY"
    L(bloom.outputs[0], bloom_masked.inputs[0])
    L(clamp.outputs[0], bloom_masked.inputs[1])

    # only above the horizon
    above = N("ShaderNodeMath")
    above.operation = "GREATER_THAN"
    above.inputs[1].default_value = 0.02
    L(sep.outputs["Z"], above.inputs[0])
    stars = N("ShaderNodeMath")
    stars.operation = "ADD"
    L(base.outputs[0], stars.inputs[0])
    L(bloom_masked.outputs[0], stars.inputs[1])
    stars_up = N("ShaderNodeMath")
    stars_up.operation = "MULTIPLY"
    L(stars.outputs[0], stars_up.inputs[0])
    L(above.outputs[0], stars_up.inputs[1])
    star_col = N("ShaderNodeMixRGB")
    star_col.blend_type = "ADD"
    L(stars_up.outputs[0], star_col.inputs["Fac"])
    L(ramp.outputs["Color"], star_col.inputs[1])
    star_col.inputs[2].default_value = (6.0, 5.4, 4.2, 1)

    bg = N("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    L(star_col.outputs[0], bg.inputs["Color"])
    out = N("ShaderNodeOutputWorld")
    L(bg.outputs[0], out.inputs[0])
    return radius.outputs[0]


# ============================================================================ the set


def build_set():
    grass = principled("Ground", (0.05, 0.065, 0.1), roughness=0.95)
    build_ground(grass)

    moon_mat = emissive("Moon", (0.95, 0.93, 0.82), 6.0)
    prim("sphere", "Moon", moon_mat, loc=(-38, 70, 26), scale=(4, 4, 4), segments=48, ring_count=24)

    # moonlight + cool rim from behind + faint warm bounce
    sun = bpy.data.lights.new("MoonLight", "SUN")
    sun.energy, sun.color, sun.angle = 1.5, (0.55, 0.65, 1.0), math.radians(1.5)
    o = link(bpy.data.objects.new("MoonLight", sun))
    o.rotation_euler = Euler((math.radians(55), 0, math.radians(200)))
    rim = bpy.data.lights.new("RimLight", "SUN")
    rim.energy, rim.color = 2.2, (0.45, 0.5, 1.0)
    o = link(bpy.data.objects.new("RimLight", rim))
    o.rotation_euler = Euler((math.radians(70), 0, math.radians(170)))

    junk = principled("Junk", (0.12, 0.08, 0.06), metallic=0.7, roughness=0.6)
    rust = principled("Rust", (0.25, 0.1, 0.04), metallic=0.4, roughness=0.8)
    tire = principled("Tire", (0.02, 0.02, 0.02), roughness=0.9)
    props = [
        ("cube", junk, (-5.6, 1.8, 0.25), (0.5, 0.4, 0.3), (0, 0.1, 0.4)),
        ("cube", rust, (-4.4, 3.5, 0.35), (0.7, 0.5, 0.4), (0.05, 0, 1.1)),
        ("cyl", rust, (-1.5, 2.6, 0.3), (0.35, 0.35, 0.6), (0, 1.4, 0.3)),
        ("torus", tire, (0.3, 1.6, 0.08), (0.3, 0.3, 0.6), (0.2, 0, 0)),
        ("cube", junk, (4.6, 2.4, 0.4), (0.8, 0.6, 0.5), (0, 0, 0.6)),
        ("cyl", junk, (5.8, -0.5, 0.2), (0.25, 0.25, 0.4), (1.57, 0, 0.9)),
        ("torus", tire, (-2.6, -1.8, 0.1), (0.28, 0.28, 0.6), (-0.3, 0.2, 0)),
        ("cube", rust, (7.5, 5.0, 0.6), (1.2, 0.8, 0.7), (0, 0.2, 0.3)),
        ("cube", junk, (-8.5, 6.0, 0.7), (1.4, 1.0, 0.8), (0.1, 0, 0.7)),
    ]
    for i, (kind, mat, loc, sc, rot) in enumerate(props):
        kw = {"major_radius": 1, "minor_radius": 0.35} if kind == "torus" else {}
        prim(kind, "junk%d" % i, mat, loc=loc, scale=sc, rot=rot, bevel=0.03 if kind == "cube" else 0, **kw)
    # rocks
    rock = principled("Rock", (0.06, 0.06, 0.08), roughness=0.9)
    import random
    rnd = random.Random(4)
    for i in range(40):
        x, y = rnd.uniform(-12, 12), rnd.uniform(-4, 10)
        if abs(y) < 1.0 and -3.6 < x < 3.2:
            continue
        s = rnd.uniform(0.05, 0.22)
        r = prim("ico", "rock%d" % i, rock, loc=(x, y, ground_height(x, y) + s * 0.3),
                 scale=(s * rnd.uniform(1, 1.6), s, s * 0.7), rot=(rnd.random(), rnd.random(), rnd.random()),
                 subdivisions=1)
        r.data.polygons.foreach_set("use_smooth", [False] * len(r.data.polygons))
    # a few bare trees on the horizon for silhouette
    bark = principled("Bark", (0.02, 0.02, 0.03), roughness=1.0)
    for i, (x, y, s) in enumerate([(-14, 16, 1.0), (10, 18, 1.3), (16, 14, 0.8), (-22, 22, 1.5)]):
        z = ground_height(x, y)
        prim("cone", "tree%d" % i, bark, loc=(x, y, z + 1.5 * s), scale=(0.12 * s, 0.12 * s, 1.5 * s), vertices=8)
        for k in range(3):
            a = k * 2.1 + i
            prim("cyl", "branch%d_%d" % (i, k), bark, loc=(x + 0.35 * s * math.cos(a), y + 0.35 * s * math.sin(a), z + (1.6 + k * 0.5) * s),
                 scale=(0.03 * s, 0.03 * s, 0.45 * s), rot=(0.9 * math.sin(a), 0.9 * math.cos(a), 0), vertices=6)


# ============================================================================ Bolt


def build_bolt():
    copper = principled("BoltCopper", (0.75, 0.36, 0.14), metallic=0.85, roughness=0.32)
    steel = principled("BoltSteel", (0.18, 0.19, 0.23), metallic=0.9, roughness=0.4)
    dark = principled("BoltDark", (0.02, 0.02, 0.03), metallic=0.3, roughness=0.25)
    eye_mat = emissive("BoltEye", (0.35, 0.85, 1.0), 0.0)
    core_mat = emissive("BoltCore", (1.0, 0.62, 0.22), 0.0)
    tip_mat = emissive("BoltTip", (1.0, 0.25, 0.2), 0.0)

    b = {"eye_mat": eye_mat, "core_mat": core_mat, "tip_mat": tip_mat}
    root = b["root"] = empty("Bolt")
    hip = b["hip"] = empty("Bolt_hip", (0, 0, 0.62), root)
    torso = b["torso"] = empty("Bolt_torso", (0, 0, 0), hip)

    prim("cube", "Bolt_body", copper, loc=(0, 0, 0.47), scale=(0.39, 0.34, 0.49), parent=torso, bevel=0.09)
    prim("cube", "Bolt_belt", steel, loc=(0, 0, 0.09), scale=(0.41, 0.36, 0.05), parent=torso, bevel=0.03)
    for y in (-0.345, 0.345):
        for z in (0.2, 0.85):
            prim("sphere", "rivet", steel, loc=(0.25, y, z), scale=(0.025,) * 3, parent=torso, segments=12, ring_count=6)
    # chest window + core
    prim("cyl", "Bolt_window", dark, loc=(0.385, 0, 0.52), scale=(0.15, 0.15, 0.02), rot=(0, math.pi / 2, 0),
         parent=torso, vertices=32)
    b["core"] = prim("sphere", "Bolt_core", core_mat, loc=(0.37, 0, 0.52), scale=(0.11,) * 3, parent=torso,
                     segments=24, ring_count=12)
    hinge = b["door"] = empty("Bolt_doorHinge", (0.41, 0, 0.69), torso)
    prim("cube", "Bolt_door", steel, loc=(0.012, 0, -0.17), scale=(0.015, 0.17, 0.17), parent=hinge, bevel=0.01)
    core_light = bpy.data.lights.new("CoreLight", "POINT")
    core_light.color, core_light.shadow_soft_size = (1.0, 0.6, 0.25), 0.1
    b["core_light"] = core_light
    o = link(bpy.data.objects.new("CoreLight", core_light), torso)
    o.location = (0.55, 0, 0.52)

    # head
    neck = b["head"] = empty("Bolt_neck", (0, 0, 0.98), torso)
    prim("cyl", "Bolt_neckPost", steel, loc=(0, 0, 0.03), scale=(0.07, 0.07, 0.08), parent=neck, vertices=16)
    prim("cube", "Bolt_head", copper, loc=(0.02, 0, 0.31), scale=(0.36, 0.31, 0.27), parent=neck, bevel=0.08)
    prim("cube", "Bolt_visor", dark, loc=(0.33, 0, 0.32), scale=(0.07, 0.23, 0.14), parent=neck, bevel=0.06)
    prim("sphere", "Bolt_eye", eye_mat, loc=(0.38, 0, 0.33), scale=(0.04, 0.09, 0.09), parent=neck, segments=24, ring_count=12)
    for y in (-0.32, 0.32):  # ear bolts
        prim("cyl", "Bolt_ear", steel, loc=(0, y, 0.32), scale=(0.08, 0.08, 0.03), rot=(math.pi / 2, 0, 0), parent=neck, vertices=16)
    prim("cyl", "Bolt_antenna", steel, loc=(-0.05, 0, 0.7), scale=(0.012, 0.012, 0.14), parent=neck, vertices=8)
    prim("sphere", "Bolt_tip", tip_mat, loc=(-0.05, 0, 0.86), scale=(0.045,) * 3, parent=neck, segments=16, ring_count=8)
    eye_light = bpy.data.lights.new("EyeLight", "POINT")
    eye_light.color, eye_light.shadow_soft_size = (0.4, 0.85, 1.0), 0.05
    b["eye_light"] = eye_light
    o = link(bpy.data.objects.new("EyeLight", eye_light), neck)
    o.location = (0.55, 0, 0.33)

    # arms ("F" = near side, -Y, toward camera)
    for side, y in (("F", -0.44), ("B", 0.44)):
        sh = b["arm" + side] = empty("Bolt_shoulder" + side, (0, y, 0.8), torso)
        prim("sphere", "Bolt_shoulderBall", steel, loc=(0, 0, 0), scale=(0.09,) * 3, parent=sh, segments=16, ring_count=8)
        prim("cyl", "Bolt_arm", steel, loc=(0, 0, -0.25), scale=(0.055, 0.055, 0.25), parent=sh, vertices=16)
        prim("sphere", "Bolt_hand", copper, loc=(0, 0, -0.52), scale=(0.1,) * 3, parent=sh, segments=16, ring_count=8)
    # legs hang from the hip, not the torso, so leaning doesn't swing them
    for side, y in (("F", -0.17), ("B", 0.17)):
        hp = b["leg" + side] = empty("Bolt_hipJoint" + side, (0, y, 0), hip)
        prim("cyl", "Bolt_leg", steel, loc=(0, 0, -0.28), scale=(0.075, 0.075, 0.28), parent=hp, vertices=16)
        prim("cube", "Bolt_foot", copper, loc=(0.07, 0, -0.57), scale=(0.17, 0.1, 0.05), parent=hp, bevel=0.03)
    return b


def build_star(name, scale=1.0):
    mat = emissive(name + "Mat", (1.0, 0.7, 0.2), 0.0)
    star = star_mesh(name, mat, 0.16 * scale, 0.07 * scale, 0.07 * scale)
    halo_mat = mat  # glow comes from the bloom pass in finish()
    light = bpy.data.lights.new(name + "Light", "POINT")
    light.color, light.shadow_soft_size = (1.0, 0.8, 0.45), 0.15
    o = link(bpy.data.objects.new(name + "Light", light), star)
    return star, mat, halo_mat, light


def build_camera():
    cam = bpy.data.cameras.new("ShotCam")
    cam.clip_start, cam.clip_end = 0.05, 400
    obj = link(bpy.data.objects.new("ShotCam", cam))
    bpy.context.scene.camera = obj
    return obj


# ============================================================================ animation (sampled from the shared story curves)


def star_world(t, hold):
    """Fallen star: (location, brightness, scale) or None."""
    if t < 8.4:
        return None
    if t < 10.8:
        k = ((t - 8.4) / 2.4) ** 2
        return vlerp((-34, 48, 30), (STAR_X, 0, 0.14), k), 1.4, 1.0
    if t < 29.5:
        return Vector((STAR_X, 0, 0.14 + 0.02 * math.sin(t * 3))), 0.85 + 0.15 * math.sin(t * 5), 1.0
    if t < 31.5:
        k = smooth((t - 29.5) / 2)
        return vlerp((STAR_X, 0, 0.14), hold, k), story.lerp(0.9, 0.7, k), 1.0
    if t < 40.5:
        b = 0.7 * (1 - smooth((t - 31.5) / 4.5)) + 0.06
        b *= 1 if t < 34 or int(t * 10) % 4 else 0.5
        return Vector(hold), b, 1.0
    if t < 44:
        b = story.track([(40.5, 0.06), (41.5, 1.8), (44, 1.2)], t)
        return Vector(hold) + Vector((0, 0, 0.1 * smooth(t - 41.5))), b, 1.0 + 0.3 * smooth(t - 41.5)
    if t < 49.6:
        k = ((t - 44) / 5.6) ** 1.7
        return vlerp(Vector(hold) + Vector((0, 0, 0.1)), STAR_HOME, k), 1.3, 1.3 + 25 * k
    return None


def gift_world(t, core):
    if not 50.3 <= t <= 53.45:
        return None
    k = smooth((t - 50.3) / 3.1)
    start = Vector((-4, 16, 9))
    p = start.lerp(core, k)
    p += Vector((0.6 * math.sin(k * 6.3), 0, 0)) * (1 - k)
    return p, 1.2, 0.55


def camera_at(t, b):
    def look(pos, target, lens):
        return Vector(pos), Vector(target), lens

    rx = story.robot_x(t) / 100.0
    shots = [
        (0.0, 8.2, ((0.8, -11, 2.4), (-3.0, 0, 1.3), 30), ((-1.2, -6.2, 1.7), (-3.0, 0, 1.15), 36)),
        (8.2, 11.2, ((8.0, -15, 1.8), (-2.0, 6, 4.0), 22), ((7.6, -14.5, 1.7), (-1.0, 4, 2.6), 22)),
        (11.2, 16.0, ((-0.4, -3.3, 1.9), (-3.0, 0, 1.6), 40), ((-0.5, -3.4, 1.85), (-3.0, 0, 1.55), 40)),
        (16.0, 28.0, None, None),
        (28.0, 36.2, ((5.3, -4.1, 2.0), (2.1, 0, 1.15), 34), ((4.8, -3.5, 1.9), (2.1, 0, 1.2), 36)),
        (36.2, 44.2, ((4.0, -2.7, 1.55), (1.95, 0, 1.25), 36), ((3.75, -2.35, 1.5), (1.95, 0, 1.25), 38)),
        (44.2, 50.3, None, None),
        (50.3, 54.6, ((5.3, -4.5, 1.2), (2.4, 0, 2.7), 28), ((4.7, -3.7, 1.5), (1.9, 0, 1.35), 32)),
        (54.6, 60.1, ((4.7, -3.7, 1.6), (1.85, 0, 1.35), 32), ((6.5, -16, 4.6), (1.4, 2, 2.6), 30)),
    ]
    for i, (t0, t1, a, z) in enumerate(shots):
        if not t0 <= t < t1:
            continue
        if i == 3:  # tracking walk, slightly ahead of Bolt
            return look((rx + 1.0, -7.5, 1.6), (rx + 1.0, 0, 1.2), 32)
        if i == 6:  # low angle, tilt up after the rising star
            k = smooth((t - 44.2) / 5.0)
            tgt = Vector((1.9, 0, 1.4)).lerp(Vector((0, 20, 16)), k)
            return look((4.8, -4.6, 0.5), tgt, story.lerp(28, 22, k))
        k = (t - t0) / (t1 - t0)
        k = smooth(k) * 0.6 + k * 0.4
        return look(vlerp(a[0], z[0], k), vlerp(a[1], z[1], k), story.lerp(a[2], z[2], k))
    return look(*shots[-1][3])


def animate(b, star, gift, cam, bloom_radius):
    scn = bpy.context.scene
    star_obj, star_mat, star_halo, star_light = star
    gift_obj, gift_mat, gift_halo, gift_light = gift
    eye_s, core_s, tip_s = (strength_socket(b[k]) for k in ("eye_mat", "core_mat", "tip_mat"))
    star_s, star_hs = strength_socket(star_mat), strength_socket(star_halo)
    gift_s, gift_hs = strength_socket(gift_mat), strength_socket(gift_halo)

    def kf(obj, path):
        obj.keyframe_insert(path, frame=f)

    for f in range(1, FRAMES + 1):
        t = (f - 1) / FPS
        scn.frame_set(f)
        p = story.robot_pose(t)
        b["root"].location = (story.robot_x(t) / 100.0, 0, ground_height(story.robot_x(t) / 100.0, 0) - 0.01)
        b["hip"].location = (0, 0, 0.62 + p["bob"] / 100.0)
        b["torso"].rotation_euler = (0, math.radians(p["lean"]), 0)
        b["head"].rotation_euler = (0, math.radians(p["head"]), 0)
        b["door"].rotation_euler = (0, -math.radians(105) * p["door"], 0)
        b["legF"].rotation_euler = (0, -math.radians(p["legF"]), 0)
        b["legB"].rotation_euler = (0, -math.radians(p["legB"]), 0)
        wave = story.track([(54.5, 0), (55.3, 1)], t)
        armF = p["armF"] if wave == 0 else story.track([(54.5, 0)], t)
        b["armB"].rotation_euler = (0, -math.radians(p["armB"]), 0)
        b["armF"].rotation_euler = (-math.radians(150 + 18 * math.sin((t - 55.3) * 9) * (t > 55.3)) * wave, -math.radians(armF), 0)
        for k in ("root", "hip", "torso", "head", "door", "legF", "legB", "armF", "armB"):
            kf(b[k], "location" if k in ("root", "hip") else "rotation_euler")

        eye_s.default_value = 18.0 * p["eye"]
        core_s.default_value = 14.0 * p["core"]
        tip_s.default_value = 10.0 * p["eye"] * (0.5 + 0.5 * (math.sin(t * 4) > 0))
        b["eye_light"].energy = 3.0 * p["eye"]
        b["core_light"].energy = 12.0 * p["core"]
        for s in (eye_s, core_s, tip_s):
            s.keyframe_insert("default_value", frame=f)
        b["eye_light"].keyframe_insert("energy", frame=f)
        b["core_light"].keyframe_insert("energy", frame=f)

        bpy.context.view_layer.update()
        core = b["core"].matrix_world.translation.copy()
        hold = core + Vector((0.42, 0, 0.08))

        st = star_world(t, hold)
        impact = math.exp(-max(0.0, t - 10.8) * 4) if t >= 10.8 else 0.0
        if st:
            loc, bright, sc = st
            star_obj.location = loc
            star_obj.scale = (sc,) * 3
            star_obj.rotation_euler = (math.pi / 2, t * 0.8, 0)
            star_s.default_value = 9 * bright
            star_light.energy = 40 * bright + 900 * impact
        else:
            star_obj.scale = (0.0001,) * 3
            star_s.default_value = star_light.energy = 0
        for path in ("location", "scale", "rotation_euler"):
            kf(star_obj, path)
        star_s.keyframe_insert("default_value", frame=f)
        star_light.keyframe_insert("energy", frame=f)

        g = gift_world(t, core)
        if g:
            loc, bright, sc = g
            gift_obj.location = loc
            gift_obj.scale = (sc * (1 - smooth((t - 53.15) / 0.3)),) * 3
            gift_obj.rotation_euler = (math.pi / 2, t * 2.0, 0)
            gift_s.default_value, gift_light.energy = 9 * bright, 25 * bright
        else:
            gift_obj.scale = (0.0001,) * 3
            gift_s.default_value = gift_light.energy = 0
        for path in ("location", "scale", "rotation_euler"):
            kf(gift_obj, path)
        gift_s.keyframe_insert("default_value", frame=f)
        gift_light.keyframe_insert("energy", frame=f)

        # the sky answers: a ring of new stars spreading out from where the star arrived
        bloom_radius.default_value = 1.05 - 2.4 * smooth((t - 49.3) / 3.5) if t > 49.3 else 2.0
        bloom_radius.keyframe_insert("default_value", frame=f)

        pos, target, lens = camera_at(t, b)
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        kf(cam, "location")
        kf(cam, "rotation_euler")
        cam.data.keyframe_insert("lens", frame=f)
        if f % 240 == 0:
            print("baked frame", f, flush=True)


# ============================================================================ entry points


def setup_render(scn):
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 1, FRAMES
    scn.render.resolution_x, scn.render.resolution_y = 1280, 720
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.render.resolution_percentage = 75  # 960x540, upscaled in finish()
    scn.cycles.samples = 6
    scn.cycles.use_denoising = True
    scn.cycles.denoising_prefilter = "FAST"
    scn.cycles.max_bounces = 2
    scn.cycles.diffuse_bounces = 1
    scn.cycles.glossy_bounces = 1
    scn.cycles.transmission_bounces = 0
    scn.cycles.volume_bounces = 0
    scn.cycles.transparent_max_bounces = 2
    scn.render.use_persistent_data = True
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.view_settings.exposure = 0.0
    scn.render.image_settings.file_format = "PNG"
    scn.render.filepath = os.path.join(FRAME_DIR, "")


def bake_modifiers():
    """Apply bevel / auto-smooth modifiers so frames don't re-evaluate them (big per-frame saving)."""
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.modifiers:
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
            obj.modifiers.clear()
            obj.data = mesh


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    setup_render(scn)
    bloom_radius = build_world()
    build_set()
    b = build_bolt()
    star = build_star("FallenStar", 1.6)
    gift = build_star("GiftStar", 1.0)
    cam = build_camera()
    bake_modifiers()
    animate(b, star, gift, cam, bloom_radius)
    scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved", BLEND)


def render(start, end):
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scn = bpy.context.scene
    setup_render(scn)
    threads = int(os.environ.get("SPARK_THREADS", "0"))
    scn.render.threads_mode = "FIXED" if threads else "AUTO"
    if threads:
        scn.render.threads = threads
    os.makedirs(FRAME_DIR, exist_ok=True)
    for f in range(start, end + 1):
        out = os.path.join(FRAME_DIR, "%04d.png" % f)
        if os.path.exists(out):
            continue
        scn.frame_set(f)
        scn.render.filepath = out
        bpy.ops.render.render(write_still=True)


def finish(out=os.path.join(HERE, "spark_3d.mp4")):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

    W, H = 1280, 720
    story.init_worker()
    sub_font, title_font, small_font = story.FONT_SUB, story.FONT_TITLE, story.FONT_SMALL
    vignette = story.make_vignette()
    wav = out + ".wav"
    story.synth_audio(wav)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "19",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FPS
        img = Image.open(os.path.join(FRAME_DIR, "%04d.png" % f)).convert("RGB").resize((W, H), Image.LANCZOS)
        # bloom: blur only the brightest parts and add them back
        arr = np.asarray(img, dtype=np.float32)
        bright = np.clip((arr.max(axis=2, keepdims=True) - 170) / 85, 0, 1) * arr
        small = Image.fromarray(bright.astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
        glow = np.asarray(small.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), np.float32)
        glow2 = np.asarray(small.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR), np.float32)
        arr = (arr + glow * 0.9 + glow2 * 0.5) * vignette
        frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(frame, "RGBA")
        d.rectangle([0, 0, W, 42], fill=(0, 0, 0, 255))
        d.rectangle([0, H - 42, W, H], fill=(0, 0, 0, 255))
        text, a = story.subtitle(t)
        if text and a > 0:
            tw = d.textlength(text, font=sub_font)
            d.text(((W - tw) / 2 + 2, H - 112 + 2), text, font=sub_font, fill=(0, 0, 0, int(200 * a)))
            d.text(((W - tw) / 2, H - 112), text, font=sub_font, fill=(250, 240, 220, int(255 * a)))
        title_a = story.fade(t, 0.6, 2.8, 0.8) + story.fade(t, 56.0, 61, 0.9)
        if title_a > 0:
            ty = H * 0.30 if t < 50 else H * 0.12
            for txt, font, y in (("SPARK", title_font, ty), ("a very short story about giving", small_font, ty + 128)):
                if t > 50 and font is small_font:
                    txt = "The End"
                tw = d.textlength(txt, font=font)
                d.text(((W - tw) / 2 + 3, y + 3), txt, font=font, fill=(0, 0, 0, int(160 * min(1, title_a))))
                d.text(((W - tw) / 2, y), txt, font=font, fill=(255, 226, 160, int(255 * min(1, title_a))))
        k = min(smooth(t / 1.0), 1 - smooth((t - 58.8) / 1.2))
        if k < 1:
            frame = Image.blend(Image.new("RGB", (W, H)), frame, k)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("wrote", out)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    cmd = args[0] if args else "build"
    if cmd == "build":
        build()
    elif cmd == "render":
        render(int(args[1]), int(args[2]))
    elif cmd == "finish":
        finish()
