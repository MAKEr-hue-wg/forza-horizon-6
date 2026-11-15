from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import (
    GeomVertexFormat, GeomVertexData, Geom, GeomTriangles, GeomVertexWriter,
    GeomNode, DirectionalLight, AmbientLight, Spotlight, PerspectiveLens,
    Fog, Vec3, Vec4, TextNode, Filename, loadPrcFileData, TransparencyAttrib
)
import math, random, os, sys, json, wave, struct

loadPrcFileData('', 'multisamples 2\nframebuffer-multisample 1\nsync-video 0\nwindow-title Forza Horizon 6: Japan\nwin-size 1280 720\n')

def build_mesh(parent, name, quads_data, pos=(0,0,0), hpr=(0,0,0), alpha=False):
    fmt = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    v = GeomVertexWriter(vdata, 'vertex')
    n = GeomVertexWriter(vdata, 'normal')
    c = GeomVertexWriter(vdata, 'color')
    tris = GeomTriangles(Geom.UHStatic)
    idx = 0
    for pts, col in quads_data:
        v0, v1, v2, v3 = pts
        p0, p1, p2, p3 = Vec3(*v0), Vec3(*v1), Vec3(*v2), Vec3(*v3)
        norm = (p1 - p0).cross(p2 - p0)
        if norm.length() > 0:
            norm.normalize()
        for p in (p0, p1, p2, p3):
            v.addData3(p)
            n.addData3(norm)
            c.addData4(*col)
        tris.addVertices(idx, idx + 1, idx + 2)
        tris.addVertices(idx, idx + 2, idx + 3)
        idx += 4
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    np = parent.attachNewNode(node)
    np.setPos(*pos)
    np.setHpr(*hpr)
    if alpha:
        np.setTransparency(TransparencyAttrib.MAlpha)
    return np

def make_prism(parent, name, pos, bot_sz, top_sz, h, y_off, col, hpr=(0,0,0), alpha=False):
    bsx, bsy, _ = bot_sz
    tsx, tsy, _ = top_sz
    bx, by, tx, ty = bsx/2, bsy/2, tsx/2, tsy/2
    z0, z1 = -h/2, h/2
    b0, b1, b2, b3 = (-bx,-by,z0), (bx,-by,z0), (bx,by,z0), (-bx,by,z0)
    t0, t1, t2, t3 = (-tx,-ty+y_off,z1), (tx,-ty+y_off,z1), (tx,ty+y_off,z1), (-tx,ty+y_off,z1)
    quads = [
        ([b0, b1, t1, t0], col), ([b2, b3, t3, t2], col),
        ([b3, b0, t0, t3], col), ([b1, b2, t2, t1], col),
        ([t0, t1, t2, t3], col), ([b3, b2, b1, b0], col)
    ]
    return build_mesh(parent, name, quads, pos, hpr, alpha)

def build_start_tunnel(parent, p_start, p_next, road_w):
    root = parent.attachNewNode('start_tunnel')
    fwd = Vec3(p_next.x - p_start.x, p_next.y - p_start.y, p_next.z - p_start.z)
    fwd.normalize()
    right = Vec3(fwd.y, -fwd.x, 0)
    right.normalize()
    up = Vec3(0, 0, 1)

    hw = road_w * 0.5 + 0.6
    h_wall, h_arch, t_len, steps = 6.5, 8.8, 56.0, 14
    solid_quads, fade_quads = [], []

    p_mouth = p_start + fwd * 2.0
    portal_col = (0.34, 0.36, 0.40, 1)
    m_l_out = p_mouth - right * (hw + 3.5) - up * 8.0
    m_l_in = p_mouth - right * hw - up * 8.0
    m_r_in = p_mouth + right * hw - up * 8.0
    m_r_out = p_mouth + right * (hw + 3.5) - up * 8.0
    m_top_l = p_mouth - right * (hw + 3.5) + up * (h_arch + 2.8)
    m_top_r = p_mouth + right * (hw + 3.5) + up * (h_arch + 2.8)
    m_in_tl = p_mouth - right * hw + up * h_wall
    m_in_tr = p_mouth + right * hw + up * h_wall

    solid_quads.append(([m_l_out, m_l_in, m_in_tl, m_top_l], portal_col))
    solid_quads.append(([m_r_in, m_r_out, m_top_r, m_in_tr], portal_col))
    solid_quads.append(([m_in_tl, m_in_tr, m_top_r, m_top_l], portal_col))

    hill_col = (0.14, 0.25, 0.11, 1)
    h_l_far = p_mouth - right * 160.0 - up * 55.0
    h_r_far = p_mouth + right * 160.0 - up * 55.0
    h_top_peak = p_mouth - fwd * 26.0 + up * 56.0
    solid_quads.append(([h_l_far, m_l_out, m_top_l, h_top_peak], hill_col))
    solid_quads.append(([m_r_out, h_r_far, h_top_peak, m_top_r], hill_col))
    solid_quads.append(([m_top_l, m_top_r, h_top_peak, h_top_peak], hill_col))

    for s in range(steps):
        t0, t1 = s / steps, (s + 1) / steps
        c0 = p_mouth - fwd * (t0 * t_len)
        c1 = p_mouth - fwd * (t1 * t_len)

        shade = max(0.02, 0.28 * (1.0 - t0) ** 1.5)
        wall_c = (shade, shade * 1.02, shade * 1.08, 1)
        rc = max(0.02, 0.19 * (1.0 - t0 * 0.88))
        road_c = (rc, rc * 1.05, rc * 1.2, 1)

        fl0, fr0 = c0 - right * hw, c0 + right * hw
        fl1, fr1 = c1 - right * hw, c1 + right * hw
        wl0, wr0 = fl0 + up * h_wall, fr0 + up * h_wall
        wl1, wr1 = fl1 + up * h_wall, fr1 + up * h_wall
        top0, top1 = c0 + up * h_arch, c1 + up * h_arch

        solid_quads.append(([fl1, fr1, fr0, fl0], road_c))
        solid_quads.append(([fl0, fl1, wl1, wl0], wall_c))
        solid_quads.append(([fr1, fr0, wr0, wr1], wall_c))
        solid_quads.append(([wl0, wl1, top1, top0], wall_c))
        solid_quads.append(([top0, top1, wr1, wr0], wall_c))

        if s >= 1:
            alpha_f = min(0.96, (s / steps) ** 1.2 * 0.62)
            fade_quads.append(([fl0, fr0, wr0, wl0], (0.02, 0.02, 0.03, alpha_f)))
            fade_quads.append(([wl0, wr0, top0, top0], (0.02, 0.02, 0.03, alpha_f)))

    c_end = p_mouth - fwd * t_len
    end_pts = [c_end - right * hw, c_end + right * hw, c_end + right * hw + up * h_arch, c_end - right * hw + up * h_arch]
    solid_quads.append((end_pts, (0.01, 0.01, 0.015, 1)))

    tun_mesh = build_mesh(root, 'tunnel_solid', solid_quads)
    tun_mesh.setLightOff()
    tun_mesh.setTwoSided(True)

    fade_mesh = build_mesh(root, 'tunnel_fade', fade_quads, alpha=True)
    fade_mesh.setLightOff()
    fade_mesh.setTwoSided(True)
    fade_mesh.setBin('transparent', 15)
    return root
def make_glow_halo(parent, name, pos, rx, rz, col, curve_y=0.0):
    fmt = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    v = GeomVertexWriter(vdata, 'vertex')
    n = GeomVertexWriter(vdata, 'normal')
    c = GeomVertexWriter(vdata, 'color')
    tris = GeomTriangles(Geom.UHStatic)

    r, g, b, _ = col
    segs = 28
    rings = [(0.0, 1.0, 1.5), (0.35, 0.65, 1.15), (0.70, 0.22, 0.9), (1.0, 0.0, 0.8)]

    v.addData3(0.0, 0.0, 0.0)
    n.addData3(0.0, 1.0, 0.0)
    c.addData4(r * 1.5, g * 1.5, b * 1.5, 1.0)

    for r_idx in range(1, len(rings)):
        rad_s, alpha_v, boost = rings[r_idx]
        for s in range(segs):
            ang = (s / segs) * math.pi * 2.0
            px = math.cos(ang) * rx * rad_s
            py = curve_y * (rad_s ** 1.5)
            pz = math.sin(ang) * rz * rad_s
            v.addData3(px, py, pz)
            n.addData3(0.0, 1.0, 0.0)
            c.addData4(r * boost, g * boost, b * boost, alpha_v)

    for s in range(segs):
        s_next = (s + 1) % segs
        tris.addVertices(0, 1 + s, 1 + s_next)

    for r_idx in range(1, len(rings) - 1):
        base0 = 1 + (r_idx - 1) * segs
        base1 = 1 + r_idx * segs
        for s in range(segs):
            s_next = (s + 1) % segs
            tris.addVertices(base0 + s, base1 + s, base1 + s_next)
            tris.addVertices(base0 + s, base1 + s_next, base0 + s_next)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    halo = parent.attachNewNode(node)
    halo.setPos(*pos)
    halo.setTransparency(TransparencyAttrib.MAlpha)
    halo.setLightOff()
    halo.setTwoSided(True)
    halo.setDepthWrite(False)
    halo.setBin('transparent', 20)
    return halo

def make_soft_car_shadow(parent, rx=0.98, ry=2.38):
    quads = []
    segs = 20
    layers = [(1.0, 0.0), (0.86, 0.25), (0.68, 0.58)]
    for li in range(len(layers) - 1):
        s_out, a_out = layers[li]
        s_in, a_in = layers[li + 1]
        for i in range(segs):
            ang1, ang2 = (i / segs) * math.pi * 2, ((i + 1) / segs) * math.pi * 2
            c1, sn1, c2, sn2 = math.cos(ang1), math.sin(ang1), math.cos(ang2), math.sin(ang2)
            p1, p2 = (c1 * rx * s_out, sn1 * ry * s_out, 0.025), (c2 * rx * s_out, sn2 * ry * s_out, 0.025)
            p3, p4 = (c2 * rx * s_in, sn2 * ry * s_in, 0.025), (c1 * rx * s_in, sn1 * ry * s_in, 0.025)
            quads.append(([p1, p2, p3, p4], (0.01, 0.01, 0.02, (a_out + a_in) * 0.5)))
    s_core, a_core = layers[-1]
    for i in range(segs):
        ang1, ang2 = (i / segs) * math.pi * 2, ((i + 1) / segs) * math.pi * 2
        p1 = (math.cos(ang1) * rx * s_core, math.sin(ang1) * ry * s_core, 0.025)
        p2 = (math.cos(ang2) * rx * s_core, math.sin(ang2) * ry * s_core, 0.025)
        quads.append(([p1, p2, (0, 0, 0.025), (0, 0, 0.025)], (0.01, 0.01, 0.02, a_core)))
    sh = build_mesh(parent, 'soft_oval_shadow', quads, alpha=True)
    sh.setLightOff()
    sh.setBin('transparent', 10)
    return sh

def ensure_game_sounds(base_dir):
    snd_dir = os.path.join(base_dir, 'sounds')
    os.makedirs(snd_dir, exist_ok=True)
    rate = 22050

    # 1. Глубокий пульсирующий звук рядного 6-цилиндрового мотора (без писка)
    eng_path = os.path.join(snd_dir, 'engine.wav')
    if not os.path.exists(eng_path):
        rng = random.Random(3)
        with wave.open(eng_path, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
            buf = bytearray()
            lp1, lp2 = 0.0, 0.0
            for i in range(rate):
                t = i / rate
                # Пульсация вспышек цилиндров (28 Гц база)
                pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 28 * t)
                saw = ((t * 56.0) % 1.0) * 2.0 - 1.0
                sub = math.sin(2 * math.pi * 28 * t) * 0.75 + math.sin(2 * math.pi * 56 * t) * 0.45
                rumble = rng.uniform(-0.35, 0.35) * pulse
                raw = (sub + saw * 0.35 * pulse + rumble)
                # Двойной фильтр низких частот, убирающий любой писк
                lp1 = lp1 * 0.86 + raw * 0.14
                lp2 = lp2 * 0.82 + lp1 * 0.18
                v = math.tanh(lp2 * 2.6) * 0.65
                buf += struct.pack('<h', int(v * 32767))
            wf.writeframes(buf)

    # 2. Реалистичный шум трения резины об асфальт с модулированным визгом
    skid_path = os.path.join(snd_dir, 'screech.wav')
    if not os.path.exists(skid_path):
        rng = random.Random(11)
        with wave.open(skid_path, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
            buf = bytearray()
            bp = 0.0
            for i in range(rate):
                t = i / rate
                mod = math.sin(2 * math.pi * 19 * t) * 90 + math.sin(2 * math.pi * 7 * t) * 50
                tone = math.sin(2 * math.pi * (1180 + mod) * t) * 0.25
                noise = rng.uniform(-0.85, 0.85)
                bp = bp * 0.75 + (noise + tone) * 0.25
                v = max(-0.85, min(0.85, bp * 0.75))
                buf += struct.pack('<h', int(v * 32767))
            wf.writeframes(buf)

    # 3. Мягкий шум горного ветра и редкие короткие голоса птиц
    birds_path = os.path.join(snd_dir, 'forest_birds.wav')
    if not os.path.exists(birds_path):
        rng = random.Random(29)
        chirps = [(0.6, 0.12, 2200), (0.76, 0.10, 2450), (2.1, 0.14, 1950), (3.4, 0.11, 2300)]
        with wave.open(birds_path, 'w') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
            buf = bytearray()
            w1, w2 = 0.0, 0.0
            for i in range(rate * 5):
                t = i / rate
                n_val = rng.uniform(-0.25, 0.25)
                w1 = w1 * 0.96 + n_val * 0.04
                w2 = w2 * 0.94 + w1 * 0.06
                v = w2 * 1.4
                for st, dur, bf in chirps:
                    if st <= t <= st + dur:
                        lt = (t - st) / dur
                        env = math.sin(math.pi * lt) ** 2
                        freq = bf - lt * 450 + math.sin(2 * math.pi * 12 * lt) * 120
                        v += math.sin(2 * math.pi * freq * t) * env * 0.14
                v = max(-0.75, min(0.75, v))
                buf += struct.pack('<h', int(v * 32767))
            wf.writeframes(buf)

    return eng_path, skid_path, birds_path


def create_flying_birds(parent, count=4):
    birds = []
    b_col = (0.16, 0.18, 0.22, 1)
    w_col = (0.24, 0.27, 0.33, 1)
    for k in range(count):
        root = parent.attachNewNode(f'bird_{k}')
        make_prism(root, 'body', (0, 0, 0), (0.16, 0.55, 0.14), (0.10, 0.42, 0.10), 0.14, 0, b_col)
        lw = make_prism(root, 'lw', (-0.34, 0.02, 0.02), (0.58, 0.24, 0.03), (0.45, 0.18, 0.03), 0.03, 0, w_col)
        rw = make_prism(root, 'rw', (0.34, 0.02, 0.02), (0.58, 0.24, 0.03), (0.45, 0.18, 0.03), 0.03, 0, w_col)
        birds.append({
            'root': root, 'lw': lw, 'rw': rw,
            'phase': k * 1.6,
            'radius': 14.0 + k * 4.5,
            'height': 13.0 + k * 2.8,
            'speed': 0.55 + (k % 2) * 0.18
        })
    return birds
def add_box_to_quads(quads, cx, cy, cz, sx, sy, sz, col):
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    b0, b1, b2, b3 = (cx-hx, cy-hy, cz-hz), (cx+hx, cy-hy, cz-hz), (cx+hx, cy+hy, cz-hz), (cx-hx, cy+hy, cz-hz)
    t0, t1, t2, t3 = (cx-hx, cy-hy, cz+hz), (cx+hx, cy-hy, cz+hz), (cx+hx, cy+hy, cz+hz), (cx-hx, cy+hy, cz+hz)
    quads.extend([
        ([b0, b1, t1, t0], col), ([b2, b3, t3, t2], col),
        ([b3, b0, t0, t3], col), ([b1, b2, t2, t1], col),
        ([t0, t1, t2, t3], col)
    ])

def build_gas_station(parent, pos, heading_deg):
    root = parent.attachNewNode('gas_station')
    root.setPos(pos)
    root.setH(heading_deg)
    quads = []
    add_box_to_quads(quads, 1.5, 0, -9.0, 21.0, 30.0, 18.0, (0.32, 0.34, 0.38, 1))
    add_box_to_quads(quads, 0.5, 0, 0.04, 19.0, 28.0, 0.10, (0.18, 0.19, 0.22, 1))
    for px in (-4.5, 4.5):
        for py in (-6.0, 6.0):
            add_box_to_quads(quads, px, py, 2.6, 0.55, 0.55, 5.2, (0.85, 0.87, 0.90, 1))
    add_box_to_quads(quads, 0, 0, 5.5, 11.5, 16.5, 0.9, (0.12, 0.55, 0.28, 1))
    add_box_to_quads(quads, 0, 0, 5.98, 11.8, 16.8, 0.25, (0.95, 0.96, 0.98, 1))
    for py in (-3.2, 3.2):
        add_box_to_quads(quads, 0, py, 0.9, 1.1, 1.4, 1.8, (0.92, 0.22, 0.24, 1))
        add_box_to_quads(quads, 0, py, 1.4, 1.16, 1.1, 0.6, (0.95, 0.98, 1.0, 1))
    add_box_to_quads(quads, 6.8, 0, 2.1, 4.2, 11.0, 4.2, (0.88, 0.86, 0.82, 1))
    add_box_to_quads(quads, 4.65, 0, 1.8, 0.1, 8.0, 2.2, (0.55, 0.85, 1.0, 1))
    mesh = build_mesh(root, 'gas_mesh', quads)
    mesh.setShaderAuto()

    glow = make_prism(root, 'fuel_zone', (0, 0, 0.10), (11.5, 20.0, 0.02), (11.5, 20.0, 0.02), 0.02, 0, (0.15, 1.3, 0.45, 0.48), alpha=True)
    glow.setLightOff()
    lamp = make_prism(root, 'canopy_lamp', (0, 0, 5.02), (8.5, 13.0, 0.05), (8.5, 13.0, 0.05), 0.05, 0, (1.8, 1.9, 1.7, 1))
    lamp.setLightOff()
    root.flattenStrong()
    return root

def add_river_bridge_segment(quads, p0, p1, r1, r2, hw, is_center_span=False):
    arch_col = (0.82, 0.16, 0.14, 1)
    steel_col = (0.88, 0.90, 0.94, 1)
    pillar_col = (0.45, 0.47, 0.50, 1)
    water_col = (0.06, 0.38, 0.68, 1)
    foam_col = (0.65, 0.85, 0.96, 1)
    lamp_col = (1.6, 1.35, 0.65, 1)

    mid = (p0 + p1) * 0.5
    r_mid = (r1 + r2) * 0.5

    w_l0 = p0 - r1 * 160.0 - Vec3(0, 0, 9.5)
    w_r0 = p0 + r1 * 160.0 - Vec3(0, 0, 9.5)
    w_l1 = p1 - r2 * 160.0 - Vec3(0, 0, 9.5)
    w_r1 = p1 + r2 * 160.0 - Vec3(0, 0, 9.5)
    quads.append(([w_l0, w_r0, w_r1, w_l1], water_col))

    if is_center_span:
        f_l0 = p0 - r1 * 160.0 - Vec3(0, 0, 9.42) + Vec3(0, 2.2, 0)
        f_r0 = p0 + r1 * 160.0 - Vec3(0, 0, 9.42) + Vec3(0, 2.2, 0)
        f_l1 = p1 - r2 * 160.0 - Vec3(0, 0, 9.42) + Vec3(0, 3.8, 0)
        f_r1 = p1 + r2 * 160.0 - Vec3(0, 0, 9.42) + Vec3(0, 3.8, 0)
        quads.append(([f_l0, f_r0, f_r1, f_l1], foam_col))

    add_box_to_quads(quads, mid.x, mid.y, mid.z - 0.65, hw * 2.15, 6.8, 1.3, pillar_col)
    for side in (-1, 1):
        b0 = p0 + r1 * (side * (hw + 0.45))
        b1 = p1 + r2 * (side * (hw + 0.45))
        if is_center_span:
            p_water = mid + r_mid * (side * (hw - 0.6))
            add_box_to_quads(quads, p_water.x, p_water.y, mid.z - 5.5, 1.8, 2.4, 11.0, pillar_col)
        add_box_to_quads(quads, b0.x, b0.y, b0.z + 4.2, 0.95, 0.95, 8.4, arch_col)
        add_box_to_quads(quads, b1.x, b1.y, b1.z + 4.2, 0.95, 0.95, 8.4, arch_col)
        mid_side = (b0 + b1) * 0.5
        add_box_to_quads(quads, mid_side.x, mid_side.y, mid_side.z + 8.4, 0.85, 6.8, 0.85, steel_col)

    l_top = mid - r_mid * (hw + 0.45) + Vec3(0, 0, 8.4)
    r_top = mid + r_mid * (hw + 0.45) + Vec3(0, 0, 8.4)
    quads.append(([l_top - Vec3(0, 0.6, 0), r_top - Vec3(0, 0.6, 0), r_top + Vec3(0, 0.6, 0.8), l_top + Vec3(0, 0.6, 0.8)], arch_col))
    mid_top = (l_top + r_top) * 0.5
    add_box_to_quads(quads, mid_top.x, mid_top.y, mid_top.z - 0.15, 2.4, 0.4, 0.25, lamp_col)

def add_house_or_hostel(quads, hx, hy, hz, is_hostel=False):
    base_col = (0.34, 0.35, 0.38, 1)
    if is_hostel:
        w, d, h = random.uniform(7.5, 10.5), random.uniform(11.0, 15.0), random.uniform(7.5, 10.5)
        add_box_to_quads(quads, hx, hy, hz - 9.0, w + 0.6, d + 0.6, 18.0, base_col)
        wall_c = (0.86, 0.82, 0.74, 1)
        roof_c = (0.22, 0.25, 0.32, 1)
        add_box_to_quads(quads, hx, hy, hz + h * 0.5, w, d, h, wall_c)
        add_box_to_quads(quads, hx, hy, hz + h + 0.35, w + 1.0, d + 1.0, 0.7, roof_c)
        for floor_z in (2.2, 5.2):
            if floor_z < h - 1.0:
                add_box_to_quads(quads, hx, hy, hz + floor_z, w + 0.12, d * 0.65, 0.9, (1.4, 1.2, 0.75, 1))
    else:
        w, d, h = random.uniform(4.8, 6.8), random.uniform(5.2, 7.4), random.uniform(3.8, 5.0)
        add_box_to_quads(quads, hx, hy, hz - 9.0, w + 0.5, d + 0.5, 18.0, base_col)
        wall_c = (0.90, 0.88, 0.84, 1)
        roof_c = (0.28, 0.20, 0.18, 1)
        add_box_to_quads(quads, hx, hy, hz + h * 0.5, w, d, h, wall_c)
        add_box_to_quads(quads, hx, hy, hz + h + 0.3, w + 0.9, d + 0.9, 0.6, roof_c)
        add_box_to_quads(quads, hx, hy, hz + h * 0.5, w + 0.1, d * 0.45, 0.85, (1.3, 1.1, 0.7, 1))

def add_tree_with_shadow(quads, tx, ty, gz, w, h, c_base, c_tip, sh_dx, sh_dy):
    tw = 0.26
    z0, z1, zt = gz - 8.0, gz + 2.6, gz + 2.6 + h
    r = w * 0.5
    sh_col = (0.04, 0.08, 0.03, 1)
    sw = r * 1.15
    tip_x, tip_y = tx + sh_dx * (h * 0.65), ty + sh_dy * (h * 0.65)
    perp_x, perp_y = -sh_dy * sw, sh_dx * sw
    sh_pts = [(tx - perp_x, ty - perp_y, gz + 0.04), (tx + perp_x, ty + perp_y, gz + 0.04), (tip_x, tip_y, gz + 0.04), (tip_x, tip_y, gz + 0.04)]
    quads.append((sh_pts, sh_col))

    b = [(tx-tw, ty-tw, z0), (tx+tw, ty-tw, z0), (tx+tw, ty+tw, z0), (tx-tw, ty+tw, z0)]
    t = [(tx-tw*0.7, ty-tw*0.7, z1), (tx+tw*0.7, ty-tw*0.7, z1), (tx+tw*0.7, ty+tw*0.7, z1), (tx-tw*0.7, ty+tw*0.7, z1)]
    tr_col = (0.24, 0.15, 0.09, 1)
    for k in range(4):
        kn = (k + 1) % 4
        quads.append(([b[k], b[kn], t[kn], t[k]], tr_col))

    segs = 6
    top = (tx, ty, zt)
    for i in range(segs):
        a1, a2 = (i/segs)*math.pi*2, ((i+1)/segs)*math.pi*2
        p1 = (tx + math.cos(a1)*r, ty + math.sin(a1)*r, z1 - 0.35)
        p2 = (tx + math.cos(a2)*r, ty + math.sin(a2)*r, z1 - 0.35)
        quads.append(([p1, p2, top, top], c_base if i % 2 == 0 else c_tip))

def build_cozy_horizon(parent):
    root = parent.attachNewNode('cozy_horizon')
    quads = []
    fx, fy = -750.0, 2900.0
    segs = 24
    r_base, r_snow, h_snow, h_top, z_bot = 1550.0, 460.0, 680.0, 1020.0, -600.0
    for i in range(segs):
        a1, a2 = (i/segs)*math.pi*2, ((i+1)/segs)*math.pi*2
        b1, b2 = (fx + math.cos(a1)*r_base, fy + math.sin(a1)*r_base, z_bot), (fx + math.cos(a2)*r_base, fy + math.sin(a2)*r_base, z_bot)
        s1, s2 = (fx + math.cos(a1)*r_snow, fy + math.sin(a1)*r_snow, h_snow), (fx + math.cos(a2)*r_snow, fy + math.sin(a2)*r_snow, h_snow)
        t1, t2 = (fx + math.cos(a1)*95.0, fy + math.sin(a1)*95.0, h_top), (fx + math.cos(a2)*95.0, fy + math.sin(a2)*95.0, h_top)
        quads.append(([b1, b2, s2, s1], (0.24, 0.23, 0.34, 1)))
        quads.append(([s1, s2, t2, t1], (0.98, 0.94, 0.96, 1)))

    rng = random.Random(42)
    for k in range(36):
        ang = (k / 36.0) * math.pi * 2.0
        dist = rng.uniform(2000.0, 3100.0)
        mx, my = math.cos(ang) * dist, math.sin(ang) * dist
        mw, mh = rng.uniform(850.0, 1450.0), rng.uniform(420.0, 780.0)
        c_rock = (0.20, 0.24, 0.28, 1) if k % 2 == 0 else (0.25, 0.24, 0.32, 1)
        c_ridge = (0.32, 0.32, 0.40, 1) if mh < 590 else (0.94, 0.88, 0.90, 1)
        r_b, r_m, z_m = mw * 0.62, mw * 0.22, mh * 0.68
        for s in range(6):
            sa1, sa2 = (s/6.0)*math.pi*2, ((s+1)/6.0)*math.pi*2
            pb1, pb2 = (mx + math.cos(sa1)*r_b, my + math.sin(sa1)*r_b, z_bot), (mx + math.cos(sa2)*r_b, my + math.sin(sa2)*r_b, z_bot)
            pm1, pm2 = (mx + math.cos(sa1)*r_m, my + math.sin(sa1)*r_m, z_m), (mx + math.cos(sa2)*r_m, my + math.sin(sa2)*r_m, z_m)
            quads.append(([pb1, pb2, pm2, pm1], c_rock))
            quads.append(([pm1, pm2, (mx, my, mh), (mx, my, mh)], c_ridge))

    mesh = build_mesh(root, 'horizon_mountains', quads)
    mesh.setLightOff()
    mesh.flattenStrong()
    return root
def setup_centered_wheel_pivots(drift_pivot, model):
    wheel_pivots = []
    wheel_geoms = []

    for g_np in model.findAllMatches('**/+GeomNode'):
        full_path = str(g_np).lower()
        b_min, b_max = g_np.getTightBounds(drift_pivot)
        if b_min is None or b_max is None:
            continue
        sz = b_max - b_min
        is_named_wheel = any(k in full_path for k in ('tire', 'circle', 'wheel', 'rim'))
        is_wheel_sized = (0.22 < sz.y < 0.88 and 0.22 < sz.z < 0.88 and sz.x < 0.48 and b_min.z < 0.15)
        if is_named_wheel or is_wheel_sized:
            center = (b_min + b_max) * 0.5
            if abs(center.x) > 0.45 and 0.6 < abs(center.y) < 2.1 and center.z < 0.55:
                wheel_geoms.append((g_np, center))

    clusters = []
    for g_np, c in wheel_geoms:
        matched = None
        for cl in clusters:
            cl_pos = cl.get('pos')
            if (c - cl_pos).length() < 0.38:
                matched = cl
                break
        if matched is None:
            clusters.append({'pos': Vec3(c), 'items': [g_np]})
        else:
            items = matched.get('items')
            items.append(g_np)
            avg = Vec3(0, 0, 0)
            for it in items:
                bm1, bm2 = it.getTightBounds(drift_pivot)
                avg += (bm1 + bm2) * 0.5
            matched.update({'pos': avg / len(items)})

    for cl in clusters:
        c_pos = cl.get('pos')
        steer_piv = drift_pivot.attachNewNode('wheel_steer_piv')
        steer_piv.setPos(c_pos)
        spin_piv = steer_piv.attachNewNode('wheel_spin_piv')
        for g_np in cl.get('items'):
            g_np.wrtReparentTo(spin_piv)
        wheel_pivots.append({'spin': spin_piv, 'steer': steer_piv, 'is_front': c_pos.y > 0.0})

    return wheel_pivots

def load_car_model(loader, parent, model_path, tint_col, is_player=True):
    root = parent.attachNewNode('car_hq')
    drift_pivot = root.attachNewNode('drift_pivot')
    sus_pivot = drift_pivot.attachNewNode('suspension_pivot')
    wheels, body_nodes = [], []

    if model_path is not None and os.path.exists(model_path):
        fn_obj = Filename.fromOsSpecific(model_path)
        fn_obj.makeCanonical()
        model = loader.loadModel(fn_obj)
        model.reparentTo(sus_pivot)
        b_min, b_max = model.getTightBounds()
        size = b_max - b_min
        max_dim = max(size.x, size.y, size.z)
        if max_dim > 0.001:
            model.setScale(4.65 / max_dim)
            model.setH(270 if size.x > size.y * 1.3 else 180)
        b_min2, b_max2 = model.getTightBounds()
        center = (b_min2 + b_max2) * 0.5
        model.setPos(-center.x, -center.y, -b_min2.z)
        model.setShaderAuto()
        body_nodes.append(model)
        wheels = setup_centered_wheel_pivots(drift_pivot, model)
    else:
        hull = make_prism(sus_pivot, 'fallback', (0, 0, 0.55), (1.85, 4.7, 0.55), (1.75, 4.5, 0.55), 0.55, 0, tint_col)
        wing = make_prism(sus_pivot, 'wing', (0, -2.1, 1.08), (1.85, 0.3, 0.06), (1.8, 0.28, 0.06), 0.06, 0, tint_col)
        body_nodes.extend([hull, wing])

    taillights_list = []
    headlight_meshes = []

    b_car_min, b_car_max = sus_pivot.getTightBounds()
    if b_car_min is None or b_car_max is None:
        b_car_min, b_car_max = Vec3(-0.92, -2.32, 0.0), Vec3(0.92, 2.32, 1.35)

    car_half_w = max(abs(b_car_min.x), abs(b_car_max.x))
    car_h = b_car_max.z - b_car_min.z
    lamp_x = car_half_w * 0.64
    front_y = b_car_max.y - 0.11
    rear_y = b_car_min.y + 0.08
    front_z = b_car_min.z + car_h * 0.42
    rear_z = b_car_min.z + car_h * 0.51

    rear_glow_node = sus_pivot.attachNewNode('rear_glow_halos')
    for side_x in (-lamp_x, lamp_x):
        rl = make_glow_halo(rear_glow_node, f'rl_glow_{side_x}', (side_x, rear_y, rear_z), 0.27, 0.12, (2.4, 0.10, 0.08, 1.0), curve_y=0.06)
        rl.setH(-12 if side_x < 0 else 12)
    rear_glow_node.hide()
    taillights_list.append(rear_glow_node)

    ao = make_soft_car_shadow(drift_pivot, 0.96, 2.34)

    if not is_player:
        if model_path is not None:
            root.setColorScale(*tint_col)
        return root, wheels, taillights_list

    headlights = sus_pivot.attachNewNode('headlights')
    for side_x in (-lamp_x, lamp_x):
        hl = make_glow_halo(headlights, f'hl_glow_{side_x}', (side_x, front_y, front_z), 0.26, 0.11, (2.2, 2.5, 3.0, 1.0), curve_y=-0.07)
        hl.setH(15 if side_x < 0 else -15)

    spots = []
    for lx in (-0.58, 0.58):
        slight = Spotlight(f'car_hl_{lx}')
        slight.setColor(Vec4(3.8, 3.9, 4.2, 1))
        slight.setAttenuation((1.0, 0.004, 0.00015))
        lens = PerspectiveLens()
        lens.setFov(56)
        lens.setNearFar(0.5, 110.0)
        slight.setLens(lens)
        sp_np = headlights.attachNewNode(slight)
        sp_np.setPos(lx, 2.10, 0.75)
        sp_np.lookAt(lx * 1.4, 34.0, -1.8)
        spots.append(sp_np)

    headlights.hide()

    neon = make_prism(drift_pivot, 'neon', (0, 0, 0.04), (1.70, 4.10, 0.02), (1.70, 4.10, 0.02), 0.02, 0, (0.0, 0.9, 1.0, 0.85), alpha=True)
    neon.setLightOff()
    neon.hide()
    return root, drift_pivot, sus_pivot, body_nodes, wheels, neon, ao, headlights, spots, taillights_list, headlight_meshes
class ForzaHorizonInfinite(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.save_path = os.path.join(self.base_dir, 'save_data.json')
        self.save_data = self.load_progress()

        self.ru_font = None
        font_paths = (
            '/c/Windows/Fonts/segoeui.ttf',
            '/c/Windows/Fonts/arial.ttf',
            '/system/fonts/Roboto-Regular.ttf',
            '/system/fonts/NotoSans-Regular.ttf'
        )
        for fpath in font_paths:
            check_p = ('C:' + fpath[2:]) if fpath.startswith('/c/') else fpath
            if os.path.exists(check_p):
                try:
                    self.ru_font = self.loader.loadFont(fpath)
                    if self.ru_font is not None:
                        self.ru_font.setPixelsPerUnit(64)
                        break
                except Exception:
                    self.ru_font = None


        self.sky_configs = [
            {'name': 'УТРО', 'bg': (0.94, 0.72, 0.56, 1), 'sun': Vec4(1.12, 0.96, 0.82, 1), 'amb': Vec4(0.52, 0.50, 0.54, 1), 'sun_hpr': (72, -16, 0), 'sh_alpha': 0.85, 'night': False},
            {'name': 'ДЕНЬ', 'bg': (0.46, 0.74, 0.98, 1), 'sun': Vec4(1.18, 1.12, 1.02, 1), 'amb': Vec4(0.58, 0.60, 0.64, 1), 'sun_hpr': (15, -62, 0), 'sh_alpha': 0.95, 'night': False},
            {'name': 'ЗАКАТ', 'bg': (0.98, 0.52, 0.34, 1), 'sun': Vec4(1.15, 0.88, 0.72, 1), 'amb': Vec4(0.50, 0.46, 0.52, 1), 'sun_hpr': (-48, -22, 0), 'sh_alpha': 0.85, 'night': False},
            {'name': 'НОЧЬ', 'bg': (0.02, 0.03, 0.08, 1), 'sun': Vec4(0.14, 0.18, 0.32, 1), 'amb': Vec4(0.12, 0.14, 0.22, 1), 'sun_hpr': (-85, -45, 0), 'sh_alpha': 0.55, 'night': True}
        ]
        self.t_idx = int(self.save_data.get('t_idx', 2)) % len(self.sky_configs)
        self.day_cycle_enabled = bool(self.save_data.get('day_cycle', False))
        self.day_time_pos = float(self.t_idx)

        self.fog = Fog("Horizon6Fog")
        self.fog.setExpDensity(0.00060)
        self.render.setFog(self.fog)

        self.dlight = DirectionalLight('sun')
        self.sun_np = self.render.attachNewNode(self.dlight)
        self.render.setLight(self.sun_np)

        self.alight = AmbientLight('amb')
        self.render.setLight(self.render.attachNewNode(self.alight))
        self.render.setShaderAuto()

        self.filters = CommonFilters(self.win, self.cam)
        self.filters.setBloom(blend=(0.24, 0.24, 0.24, 0.0), mintrigger=0.72, maxtrigger=1.0, desat=0.2, intensity=1.15, size="medium")

        self.steppe = make_prism(self.render, 'steppe', (0, 0, -2.0), (16000, 16000, 2), (16000, 16000, 2), 2, 0, (0.14, 0.25, 0.11, 1))
        self.steppe.setLightOff()
        self.sun_disc = make_prism(self.render, 'sun', (350, 2400, 380), (280, 10, 280), (280, 10, 280), 280, 0, (1.4, 1.05, 0.65, 1))
        self.sun_disc.setLightOff()
        self.horizon_mtns = build_cozy_horizon(self.render)

        self.seg_len, self.road_w = 6.5, 15.0
        self.road_pts = [Vec3(0.0, 0.0, 35.0)]
        self.gen_heading = 0.0
        self.gen_cur_turn = 0.0
        self.gen_target_turn = 0.0
        self.gen_steps_left = 10
        self.road_data, self.next_idx = [], 0
        self.gas_stations = []
        self.next_bridge_idx = random.randint(150, 260)
        self.next_gs_idx = random.randint(230, 360)
        self.town_start_idx = random.randint(120, 220)
        self.town_end_idx = self.town_start_idx + random.randint(14, 24)
        for _ in range(95):
            self.spawn_next_segment()

        start_pt, next_pt = self.get_road_point(0), self.get_road_point(1)
        self.start_tunnel = build_start_tunnel(self.render, start_pt, next_pt, self.road_w)

        cars_dir = os.path.join(self.base_dir, 'cars')
        os.makedirs(cars_dir, exist_ok=True)

        self.available_cars = []
        seen_names = set()
        for folder in (cars_dir, self.base_dir):
            for fn in sorted(os.listdir(folder)):
                if fn.lower().endswith(('.glb', '.gltf')):
                    base_fn, _ = os.path.splitext(fn)
                    clean_name = base_fn.upper()
                    if clean_name not in seen_names:
                        seen_names.add(clean_name)
                        self.available_cars.append({'name': clean_name, 'path': os.path.join(folder, fn)})

        if not self.available_cars:
            self.available_cars.append({'name': 'HORIZON GT (БАЗОВАЯ)', 'path': None})

        self.car_idx = int(self.save_data.get('car_idx', 0)) % len(self.available_cars)
        self.paints = [(1, 1, 1, 1), (0.05, 0.36, 0.86, 1), (0.85, 0.87, 0.90, 1), (0.88, 0.08, 0.14, 1), (1.0, 0.72, 0.0, 1), (0.14, 0.15, 0.18, 1)]
        self.paint_names = ['БЕЛЫЙ', 'СИНИЙ', 'СЕРЕБРО', 'КРАСНЫЙ', 'ЗОЛОТОЙ', 'ЧЁРНЫЙ']
        self.p_idx = int(self.save_data.get('p_idx', 0)) % len(self.paints)

        self.stage = int(self.save_data.get('stage', 1))
        if self.stage not in (1, 2, 3):
            self.stage = 1
        self.stages = {
            1: (150.0 / 4.4, 20.0),
            2: (200.0 / 4.4, 27.0),
            3: (250.0 / 4.4, 35.0)
        }

        self.traffic_options = (0, 2, 4, 6, 8, 12)
        self.traffic_opt_idx = int(self.save_data.get('traffic_opt_idx', 2)) % len(self.traffic_options)
        self.traffic = []

        self.car_root = None
        self.lights_on = False
        self.spawn_player_car()
        self.rebuild_traffic()
        self.init_hud_and_menus()

    def load_progress(self):
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'car_idx': 0, 'p_idx': 0, 'stage': 1, 'traffic_opt_idx': 2, 't_idx': 2, 'day_cycle': False, 'sound_on': True, 'touch_ui': True, 'best_dist_km': 0.0, 'total_dist_km': 0.0}

    def save_progress(self):
        data = {
            'car_idx': self.car_idx,
            'p_idx': self.p_idx,
            'stage': self.stage,
            'traffic_opt_idx': self.traffic_opt_idx,
            't_idx': self.t_idx,
            'day_cycle': self.day_cycle_enabled,
            'sound_on': self.sound_on,
            'touch_ui': self.touch_ui,
            'best_dist_km': round(self.best_dist_km, 2),
            'total_dist_km': round(self.total_dist_km, 2)
        }
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return {'car_idx': 0, 'p_idx': 0, 'stage': 1, 'traffic_opt_idx': 2, 't_idx': 2, 'day_cycle': False, 'best_dist_km': 0.0, 'total_dist_km': 0.0}

    def save_progress(self):
        data = {
            'car_idx': self.car_idx,
            'p_idx': self.p_idx,
            'stage': self.stage,
            'traffic_opt_idx': self.traffic_opt_idx,
            't_idx': self.t_idx,
            'day_cycle': self.day_cycle_enabled,
            'best_dist_km': round(self.best_dist_km, 2),
            'total_dist_km': round(self.total_dist_km, 2)
        }
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    def init_hud_and_menus(self):
        self.smoke_pool = []
        for _ in range(36):
            sm = make_prism(self.render, 'sm_p', (0,0,-500), (0.45,0.45,0.45), (0.45,0.45,0.45), 0.45, 0, (0.95,0.96,0.98,0.5), alpha=True)
            sm.setLightOff(); sm.hide()
            self.smoke_pool.append({'np': sm, 'life': 0.0, 'vz': 1.5})
        self.smoke_ptr = 0

        self.skid_pool = []
        for _ in range(100):
            sk = make_prism(self.render, 'sk_p', (0,0,-500), (0.26,0.75,0.02), (0.26,0.75,0.02), 0.02, 0, (0.04,0.04,0.05,0.7), alpha=True)
            sk.setLightOff(); sk.hide()
            self.skid_pool.append(sk)
        self.skid_ptr = 0

        self.vel_vec = Vec3(0, 0, 0)
        self.smooth_steer = 0.0
        self.angular_vel = 0.0
        self.sus_roll = 0.0
        self.sus_pitch = 0.0
        self.smooth_dt = 0.016
        self.cam_look_smooth = self.car_root.getPos() + Vec3(0, 2, 1.1)
        self.drift_angle, self.drift_score, self.drift_combo, self.drift_timer = 0.0, 0.0, 1.0, 0.0

        self.fuel = 100.0
        self.rpm = 900.0
        self.gear = 1
        self.trip_dist_km = 0.0
        self.best_dist_km = float(self.save_data.get('best_dist_km', 0.0))
        self.total_dist_km = float(self.save_data.get('total_dist_km', 0.0))
        self.save_timer = 0.0

        font_kw = {'font': self.ru_font} if self.ru_font is not None else {}

        self.dash_frame = DirectFrame(
            frameColor=(0.05, 0.07, 0.12, 0.82),
            frameSize=(0.68, 1.32, -0.96, -0.56),
            pos=(0, 0, 0)
        )
        self.hud_spd = OnscreenText(text='0', pos=(0.94, -0.71), scale=0.13, fg=(1, 1, 1, 1), align=TextNode.ARight, parent=self.dash_frame, **font_kw)
        self.hud_unit = OnscreenText(text='КМ/Ч', pos=(0.97, -0.70), scale=0.036, fg=(0.65, 0.75, 0.90, 1), align=TextNode.ALeft, parent=self.dash_frame, **font_kw)
        self.hud_gear = OnscreenText(text='1', pos=(1.22, -0.71), scale=0.11, fg=(0.98, 0.36, 0.56, 1), align=TextNode.ACenter, parent=self.dash_frame, **font_kw)
        self.hud_rpm_txt = OnscreenText(text='900 RPM', pos=(0.72, -0.79), scale=0.034, fg=(0.85, 0.90, 1.0, 1), align=TextNode.ALeft, parent=self.dash_frame, **font_kw)
        self.hud_rpm_bar = OnscreenText(text='||||||||||..........', pos=(0.72, -0.84), scale=0.042, fg=(0.25, 0.95, 0.55, 1), align=TextNode.ALeft, parent=self.dash_frame)
        self.hud_fuel = OnscreenText(text='БАК: 100%', pos=(0.72, -0.92), scale=0.036, fg=(0.35, 0.95, 0.55, 1), align=TextNode.ALeft, parent=self.dash_frame, **font_kw)

        self.hud_dist = OnscreenText(text='ДИСТАНЦИЯ: 0.00 КМ  |  РЕКОРД: 0.00 КМ', pos=(-1.28, 0.88), scale=0.042, fg=(1, 1, 1, 1), align=TextNode.ALeft, **font_kw)
        self.hud_info = OnscreenText(text='[SPACE] Дрифт  [L] Фары  [N] Неон  [R] Заново  [ESC] Меню', pos=(-1.28, 0.81), scale=0.033, fg=(1.0, 0.88, 0.75, 1), align=TextNode.ALeft, **font_kw)
        self.hud_drift = OnscreenText(text='', pos=(0.0, 0.78), scale=0.075, fg=(1.0, 0.55, 0.85, 1), align=TextNode.ACenter, **font_kw)
        self.hud_alert = OnscreenText(text='', pos=(0.0, 0.35), scale=0.055, fg=(0.35, 1.0, 0.55, 1), align=TextNode.ACenter, **font_kw)

        self.dash_frame.hide(); self.hud_dist.hide(); self.hud_info.hide(); self.hud_drift.hide(); self.hud_alert.hide()
        self.touch_ui = bool(self.save_data.get('touch_ui', True))
        self.touch_layer = self.aspect2d.attachNewNode('touch_controls')
        t_style = {
            'text_scale': 0.055, 'text_fg': (1, 1, 1, 0.95),
            'frameColor': (0.08, 0.11, 0.18, 0.62),
            'relief': 1, 'pressEffect': 1
        }
        if self.ru_font is not None:
            t_style['text_font'] = self.ru_font

        def make_touch_btn(label, pos, size, key_name, col_override=None):
            st = dict(t_style)
            if col_override is not None:
                st['frameColor'] = col_override
            btn = DirectButton(text=label, pos=pos, frameSize=size, parent=self.touch_layer, **st)
            btn.bind(DGG.B1PRESS, lambda evt: self.set_key(key_name, True))
            btn.bind(DGG.B1RELEASE, lambda evt: self.set_key(key_name, False))
            btn.bind(DGG.WITHOUT, lambda evt: self.set_key(key_name, False))
            return btn

        make_touch_btn('<', (-1.12, 0, -0.74), (-0.16, 0.16, -0.16, 0.16), 'a')
        make_touch_btn('>', (-0.75, 0, -0.74), (-0.16, 0.16, -0.16, 0.16), 'd')

        make_touch_btn('ДРИФТ', (0.76, 0, -0.36), (-0.16, 0.16, -0.10, 0.10), 'space', (0.85, 0.22, 0.45, 0.68))
        make_touch_btn('ТОРМОЗ', (0.76, 0, -0.12), (-0.16, 0.16, -0.10, 0.10), 's', (0.75, 0.18, 0.18, 0.68))
        make_touch_btn('ГАЗ', (1.14, 0, -0.24), (-0.16, 0.16, -0.22, 0.22), 'w', (0.16, 0.68, 0.34, 0.75))

        DirectButton(text='МЕНЮ', pos=(1.15, 0, 0.86), frameSize=(-0.14, 0.14, -0.06, 0.06), command=self.open_menu, parent=self.touch_layer, **t_style)
        DirectButton(text='ФАРЫ', pos=(0.82, 0, 0.86), frameSize=(-0.14, 0.14, -0.06, 0.06), command=self.toggle_lights, parent=self.touch_layer, **t_style)

        self.touch_layer.hide()


        self.in_menu = True
        self.menu_orbit = 35.0
        self.build_all_menus()

        self.cam_yaw, self.cam_pitch, self.rmb_down, self.last_mouse = 0.0, 15.0, False, None
        self.accept('mouse3', self.on_rmb_down); self.accept('mouse3-up', self.on_rmb_up)

        self.speed = 0.0
        self.keys = {k: False for k in ['w', 's', 'a', 'd', 'space', 'arrow_up', 'arrow_down', 'arrow_left', 'arrow_right']}
        for k in self.keys:
            self.accept(k, self.set_key, [k, True])
            self.accept(f'{k}-up', self.set_key, [k, False])

        self.accept('n', self.tune_neon)
        self.accept('l', self.toggle_lights)
        self.accept('r', self.restart_run)
        self.accept('enter', self.start_game)
        self.accept('escape', self.open_menu)
        self.apply_environment_by_idx(self.t_idx)

        eng_p, skid_p, birds_p = ensure_game_sounds(self.base_dir)
        self.snd_engine = self.loader.loadSfx(Filename.fromOsSpecific(eng_p))
        self.snd_screech = self.loader.loadSfx(Filename.fromOsSpecific(skid_p))
        self.snd_birds = self.loader.loadSfx(Filename.fromOsSpecific(birds_p))

        for sfx in (self.snd_engine, self.snd_screech, self.snd_birds):
            if sfx is not None:
                sfx.setLoop(True)

        if self.snd_birds is not None:
            self.snd_birds.setVolume(0.45)
            self.snd_birds.play()
        if self.snd_engine is not None:
            self.snd_engine.setVolume(0.18)
            self.snd_engine.play()

        self.birds = create_flying_birds(self.render, count=4)
        self.bird_time = 0.0
        self.taskMgr.add(self.update_game, 'update_game')
    def spawn_player_car(self):
        prev_pos = self.car_root.getPos() if self.car_root is not None else (self.get_road_point(1.5) + Vec3(0, 0, 0.06))
        prev_hpr = self.car_root.getHpr() if self.car_root is not None else None
        if self.car_root is not None:
            self.car_root.removeNode()

        car_info = self.available_cars[self.car_idx]
        col = self.paints[self.p_idx]
        (self.car_root, self.car_visual, self.car_sus, self.body, self.wheels,
         self.neon, self.car_shadow, self.headlights, self.spot_nodes, self.taillights, self.hl_meshes) = load_car_model(
            self.loader, self.render, car_info.get('path'), col, True
        )
        for b in self.body:
            b.setColorScale(*col)

        self.car_root.setPos(prev_pos)
        if prev_hpr is not None:
            self.car_root.setHpr(prev_hpr)
        else:
            self.car_root.lookAt(self.get_road_point(2.5) + Vec3(0, 0, 0.06))
        self.set_lights(self.lights_on)

    def rebuild_traffic(self):
        for t in self.traffic:
            t.get('np').removeNode()
        self.traffic.clear()

        count = self.traffic_options[self.traffic_opt_idx]
        if count <= 0:
            return

        t_cols = [(0.92, 0.92, 0.95, 1), (0.25, 0.25, 0.28, 1), (0.88, 0.15, 0.18, 1), (0.95, 0.72, 0.15, 1), (0.12, 0.45, 0.85, 1)]
        base_idx = (self.car_root.getY() / self.seg_len) + 22.0 if self.car_root is not None else 22.0
        for k in range(count):
            rnd_car = random.choice(self.available_cars)
            t_col = random.choice(t_cols)
            t_car, t_wh, t_tl = load_car_model(self.loader, self.render, rnd_car.get('path'), t_col, False)
            for tl_m in t_tl:
                if self.lights_on:
                    tl_m.show(); tl_m.setLightOff(); tl_m.setColorScale(1.8, 0.25, 0.20, 1)
                else:
                    if 'glow' in tl_m.getName(): tl_m.hide()
                    else: tl_m.clearLight(); tl_m.clearColorScale()
            self.traffic.append({
                'np': t_car, 'wheels': t_wh, 'tl': t_tl,
                'idx': base_idx + k * 24.0,
                'lane': -3.8 if k % 2 == 0 else 3.8,
                'spd': random.uniform(16.0, 22.0)
            })

    def build_all_menus(self):
        self.menu_panel = DirectFrame(frameColor=(0.04, 0.05, 0.09, 0.76), frameSize=(-1.35, -0.26, -1.0, 1.0), pos=(0, 0, 0))
        self.menu_accent = DirectFrame(frameColor=(0.98, 0.36, 0.56, 0.95), frameSize=(-1.35, -1.325, -1.0, 1.0), pos=(0, 0, 0))
        font_kw = {'font': self.ru_font} if self.ru_font is not None else {}

        self.menu_sub = OnscreenText(text='JAPAN FESTIVAL EDITION', pos=(-1.25, 0.86), scale=0.036, fg=(1.0, 0.65, 0.78, 1), align=TextNode.ALeft, parent=self.menu_panel, **font_kw)
        self.menu_title = OnscreenText(text='FORZA\nHORIZON 6', pos=(-1.25, 0.72), scale=0.098, fg=(1, 1, 1, 1), align=TextNode.ALeft, parent=self.menu_panel, **font_kw)
        self.menu_stats = OnscreenText(text=f'РЕКОРД: {self.best_dist_km:.2f} КМ  |  ВСЕГО: {self.total_dist_km:.2f} КМ', pos=(-1.25, 0.50), scale=0.033, fg=(0.95, 0.85, 0.55, 1), align=TextNode.ALeft, parent=self.menu_panel, **font_kw)
        self.tab_label = OnscreenText(text='ГЛАВНОЕ МЕНЮ', pos=(-1.25, 0.41), scale=0.040, fg=(0.55, 0.85, 1.0, 1), align=TextNode.ALeft, parent=self.menu_panel, **font_kw)

        btn_style = {
            'text_scale': 0.041, 'text_fg': (1, 1, 1, 1), 'text_align': TextNode.ALeft,
            'text_pos': (-0.42, -0.014), 'frameColor': (0.14, 0.17, 0.25, 0.90),
            'frameSize': (-0.45, 0.48, -0.050, 0.050), 'relief': 1, 'pressEffect': 1
        }
        if self.ru_font is not None:
            btn_style['text_font'] = self.ru_font

        self.tab_main = self.menu_panel.attachNewNode('tab_main')
        DirectButton(text='>  ИГРАТЬ (ENTER)', pos=(-0.80, 0, 0.27), command=self.start_game, parent=self.tab_main, **{**btn_style, 'frameColor': (0.94, 0.24, 0.48, 0.95)})
        DirectButton(text='@  НАЧАТЬ ЗАНОВО (НОВЫЙ ЗАЕЗД)', pos=(-0.80, 0, 0.13), command=self.restart_from_menu, parent=self.tab_main, **btn_style)
        DirectButton(text='*  ГАРАЖ (АВТО И ТЮНИНГ)', pos=(-0.80, 0, -0.01), command=self.show_garage_tab, parent=self.tab_main, **btn_style)
        DirectButton(text='*  НАСТРОЙКИ (ТРАФИК И ПОГОДА)', pos=(-0.80, 0, -0.15), command=self.show_settings_tab, parent=self.tab_main, **btn_style)
        DirectButton(text='X  ВЫХОД (С СОХРАНЕНИЕМ)', pos=(-0.80, 0, -0.32), command=self.quit_with_save, parent=self.tab_main, **btn_style)

        self.tab_garage = self.menu_panel.attachNewNode('tab_garage')
        car_nm = self.available_cars[self.car_idx].get('name')
        spd_val, _ = self.stages.get(self.stage)
        max_kmh = int(spd_val * 4.4)
        self.btn_g_car = DirectButton(text=f'АВТО: {car_nm}', pos=(-0.80, 0, 0.26), command=self.garage_next_car, parent=self.tab_garage, **btn_style)
        self.btn_g_paint = DirectButton(text=f'ЦВЕТ: {self.paint_names[self.p_idx]}', pos=(-0.80, 0, 0.12), command=self.garage_next_paint, parent=self.tab_garage, **btn_style)
        self.btn_g_stage = DirectButton(text=f'ДВИГАТЕЛЬ: STAGE {self.stage} ({max_kmh} КМ/Ч)', pos=(-0.80, 0, -0.02), command=self.garage_next_stage, parent=self.tab_garage, **btn_style)
        self.btn_g_neon = DirectButton(text='НЕОН ПОДСВЕТКА: ВЫКЛ', pos=(-0.80, 0, -0.16), command=self.garage_toggle_neon, parent=self.tab_garage, **btn_style)
        DirectButton(text='<  НАЗАД В МЕНЮ', pos=(-0.80, 0, -0.32), command=self.show_main_tab, parent=self.tab_garage, **{**btn_style, 'frameColor': (0.22, 0.26, 0.36, 0.95)})

        tut_box = DirectFrame(frameColor=(0.08, 0.11, 0.18, 0.92), frameSize=(-0.45, 0.48, -0.44, -0.02), pos=(-0.80, 0, -0.41), parent=self.tab_garage)
        tut_text = (
            "КАК ДОБАВИТЬ СВОИ МАШИНЫ:\n"
            "1. Скачай 3D-модель в формате .GLB\n"
            "2. Положи в папку 'cars' рядом с игрой.\n"
            "3. Перезапусти — авто появится здесь!\n"
            "   Заправляйтесь на зелёных АЗС."
        )
        OnscreenText(text=tut_text, pos=(-0.41, -0.07), scale=0.030, fg=(0.82, 0.92, 1.0, 1), align=TextNode.ALeft, parent=tut_box, **font_kw)
        self.tab_garage.hide()

        self.tab_settings = self.menu_panel.attachNewNode('tab_settings')
        t_cnt = self.traffic_options[self.traffic_opt_idx]
        w_nm = self.sky_configs[self.t_idx].get('name')
        cyc_txt = 'ВКЛ' if self.day_cycle_enabled else 'ВЫКЛ'
        snd_txt = 'ВКЛ' if self.sound_on else 'ВЫКЛ'
        tch_txt = 'ВКЛ' if self.touch_ui else 'ВЫКЛ'
        self.btn_s_traffic = DirectButton(text=f'ТРАФИК НА ТРАССЕ: {t_cnt} МАШИН', pos=(-0.80, 0, 0.28), command=self.settings_next_traffic, parent=self.tab_settings, **btn_style)
        self.btn_s_weather = DirectButton(text=f'ВРЕМЯ СУТОК: {w_nm}', pos=(-0.80, 0, 0.15), command=self.settings_next_weather, parent=self.tab_settings, **btn_style)
        self.btn_s_cycle = DirectButton(text=f'СМЕНА ДНЯ И НОЧИ: {cyc_txt}', pos=(-0.80, 0, 0.02), command=self.settings_toggle_cycle, parent=self.tab_settings, **btn_style)
        self.btn_s_sound = DirectButton(text=f'ЗВУК В ИГРЕ: {snd_txt}', pos=(-0.80, 0, -0.11), command=self.settings_toggle_sound, parent=self.tab_settings, **btn_style)
        self.btn_s_touch = DirectButton(text=f'СЕНСОРНЫЕ КНОПКИ: {tch_txt}', pos=(-0.80, 0, -0.24), command=self.settings_toggle_touch, parent=self.tab_settings, **btn_style)
        DirectButton(text='<  НАЗАД В МЕНЮ', pos=(-0.80, 0, -0.39), command=self.show_main_tab, parent=self.tab_settings, **{**btn_style, 'frameColor': (0.22, 0.26, 0.36, 0.95)})
        self.tab_settings.hide()

    def restart_run(self):
        self.save_progress()
        self.speed = 0.0
        self.vel_vec = Vec3(0, 0, 0)
        self.angular_vel = 0.0
        self.drift_angle = 0.0
        self.drift_score = 0.0
        self.drift_combo = 1.0
        self.fuel = 100.0
        self.trip_dist_km = 0.0
        self.hud_drift.hide()
        self.hud_alert.hide()

        first_seg = next(iter(self.road_data))
        start_i = first_seg.get('idx') + 1.5
        sp = self.get_road_point(start_i) + Vec3(0, 0, 0.06)
        lp = self.get_road_point(start_i + 1.0) + Vec3(0, 0, 0.06)
        self.car_root.setPos(sp)
        self.car_root.lookAt(lp)
        self.cam_look_smooth = sp + Vec3(0, 2, 1.1)
        self.rebuild_traffic()

    def restart_from_menu(self):
        self.restart_run()
        self.start_game()

    def quit_with_save(self):
        self.save_progress()
        sys.exit()

    def show_main_tab(self):
        self.tab_label.setText('ГЛАВНОЕ МЕНЮ')
        self.menu_stats.setText(f'РЕКОРД: {self.best_dist_km:.2f} КМ  |  ВСЕГО: {self.total_dist_km:.2f} КМ')
        self.tab_garage.hide(); self.tab_settings.hide(); self.tab_main.show()

    def show_garage_tab(self):
        self.tab_label.setText(f'ГАРАЖ (НАЙДЕНО АВТО: {len(self.available_cars)})')
        self.tab_main.hide(); self.tab_settings.hide(); self.tab_garage.show()

    def show_settings_tab(self):
        self.tab_label.setText('НАСТРОЙКИ ИГРЫ')
        self.tab_main.hide(); self.tab_garage.hide(); self.tab_settings.show()

    def garage_next_car(self):
        self.car_idx = (self.car_idx + 1) % len(self.available_cars)
        self.spawn_player_car()
        nm = self.available_cars[self.car_idx].get('name')
        self.btn_g_car['text'] = f'АВТО: {nm}'
        self.save_progress()

    def garage_next_paint(self):
        self.tune_paint()
        self.btn_g_paint['text'] = f'ЦВЕТ: {self.paint_names[self.p_idx]}'
        self.save_progress()

    def garage_next_stage(self):
        self.stage = 1 if self.stage == 3 else self.stage + 1
        spd_val, _ = self.stages.get(self.stage)
        max_kmh = int(spd_val * 4.4)
        self.btn_g_stage['text'] = f'ДВИГАТЕЛЬ: STAGE {self.stage} ({max_kmh} КМ/Ч)'
        self.save_progress()

    def garage_toggle_neon(self):
        self.tune_neon()
        state_txt = 'ВКЛ' if not self.neon.isHidden() else 'ВЫКЛ'
        self.btn_g_neon['text'] = f'НЕОН ПОДСВЕТКА: {state_txt}'

    def settings_next_traffic(self):
        self.traffic_opt_idx = (self.traffic_opt_idx + 1) % len(self.traffic_options)
        cnt = self.traffic_options[self.traffic_opt_idx]
        self.btn_s_traffic['text'] = f'ТРАФИК НА ТРАССЕ: {cnt} МАШИН'
        self.rebuild_traffic()
        self.save_progress()

    def settings_next_weather(self):
        self.day_cycle_enabled = False
        self.btn_s_cycle['text'] = 'СМЕНА ДНЯ И НОЧИ: ВЫКЛ'
        self.t_idx = (self.t_idx + 1) % len(self.sky_configs)
        self.day_time_pos = float(self.t_idx)
        self.apply_environment_by_idx(self.t_idx)
        self.btn_s_weather['text'] = f"ВРЕМЯ СУТОК: {self.sky_configs[self.t_idx].get('name')}"
        self.save_progress()

    def settings_toggle_cycle(self):
        self.day_cycle_enabled = not self.day_cycle_enabled
        self.btn_s_cycle['text'] = f"СМЕНА ДНЯ И НОЧИ: {'ВКЛ' if self.day_cycle_enabled else 'ВЫКЛ'}"
        self.save_progress()

    def settings_toggle_touch(self):
        self.touch_ui = not self.touch_ui
        self.btn_s_touch['text'] = f"СЕНСОРНЫЕ КНОПКИ: {'ВКЛ' if self.touch_ui else 'ВЫКЛ'}"
        self.save_progress()

    def start_game(self):
        if not self.in_menu: return
        self.in_menu = False
        self.menu_panel.hide(); self.menu_accent.hide()
        self.dash_frame.show(); self.hud_dist.show(); self.hud_info.show()
        if self.touch_ui:
            self.touch_layer.show()
        self.cam_yaw = 0.0; self.cam_pitch = 14.5

    def open_menu(self):
        if self.in_menu: return
        self.in_menu = True
        self.speed = 0.0; self.vel_vec = Vec3(0, 0, 0)
        self.touch_layer.hide()
        for k in self.keys:
            self.keys[k] = False
        if self.snd_screech is not None:
            self.snd_screech.stop()
        if self.sound_on and self.snd_engine is not None:
            self.snd_engine.setPlayRate(0.68)
            self.snd_engine.setVolume(0.16)
        self.save_progress()
        self.dash_frame.hide(); self.hud_dist.hide(); self.hud_info.hide(); self.hud_drift.hide(); self.hud_alert.hide()
        self.show_main_tab()
        self.menu_panel.show(); self.menu_accent.show()


    def apply_environment_by_idx(self, idx):
        cfg = self.sky_configs[idx]
        r, g, b, a = cfg.get('bg')
        self.setBackgroundColor(r, g, b, a)
        self.fog.setColor(r, g, b)
        self.dlight.setColor(cfg.get('sun'))
        self.alight.setColor(cfg.get('amb'))
        self.sun_np.setHpr(*cfg.get('sun_hpr'))
        self.car_shadow.setAlphaScale(cfg.get('sh_alpha'))
        self.sun_disc.setColorScale((0.75, 0.85, 1.15, 1) if cfg.get('night') else (1.0, 1.0, 1.0, 1))
        self.set_lights(cfg.get('night'))
        if cfg.get('night'): self.neon.show()

    def update_dynamic_day_cycle(self, dt):
        self.day_time_pos = (self.day_time_pos + dt * 0.045) % 4.0
        i0 = int(self.day_time_pos)
        i1 = (i0 + 1) % 4
        frac = self.day_time_pos - i0

        c0, c1 = self.sky_configs[i0], self.sky_configs[i1]
        r0, g0, b0, _ = c0.get('bg')
        r1, g1, b1, _ = c1.get('bg')
        r, g, b = r0 + (r1 - r0) * frac, g0 + (g1 - g0) * frac, b0 + (b1 - b0) * frac
        self.setBackgroundColor(r, g, b, 1.0)
        self.fog.setColor(r, g, b)

        s0, s1 = c0.get('sun'), c1.get('sun')
        self.dlight.setColor(s0 * (1.0 - frac) + s1 * frac)

        a0, a1 = c0.get('amb'), c1.get('amb')
        self.alight.setColor(a0 * (1.0 - frac) + a1 * frac)

        h0, p0, _ = c0.get('sun_hpr')
        h1, p1, _ = c1.get('sun_hpr')
        self.sun_np.setHpr(h0 + (h1 - h0) * frac, p0 + (p1 - p0) * frac, 0)

        sh0, sh1 = c0.get('sh_alpha'), c1.get('sh_alpha')
        self.car_shadow.setAlphaScale(sh0 + (sh1 - sh0) * frac)

        is_dark = (2.55 < self.day_time_pos < 3.85)
        if is_dark != self.lights_on:
            self.set_lights(is_dark)
            if is_dark: self.neon.show()
            else: self.neon.hide()
    def set_lights(self, state):
        self.lights_on = state
        if state:
            self.headlights.show()
            for sp in self.spot_nodes:
                self.render.setLight(sp)
            for hm in self.hl_meshes:
                hm.setLightOff(); hm.setColorScale(2.8, 3.0, 3.4, 1)
            for tl in self.taillights:
                tl.show(); tl.setLightOff(); tl.setColorScale(1.8, 0.25, 0.20, 1)
            for t in self.traffic:
                for tl in t.get('tl'):
                    tl.show(); tl.setLightOff(); tl.setColorScale(1.8, 0.25, 0.20, 1)
        else:
            self.headlights.hide()
            for sp in self.spot_nodes:
                self.render.clearLight(sp)
            for hm in self.hl_meshes:
                hm.clearLight(); hm.clearColorScale()
            for tl in self.taillights:
                if 'glow' in tl.getName(): tl.hide()
                else: tl.clearLight(); tl.clearColorScale()
            for t in self.traffic:
                for tl in t.get('tl'):
                    if 'glow' in tl.getName(): tl.hide()
                    else: tl.clearLight(); tl.clearColorScale()

    def toggle_lights(self): self.set_lights(not self.lights_on)
    def on_rmb_down(self):
        self.rmb_down = True
        if self.mouseWatcherNode.hasMouse():
            m = self.mouseWatcherNode.getMouse()
            self.last_mouse = (m.getX(), m.getY())
    def on_rmb_up(self): self.rmb_down = False; self.last_mouse = None

    def ensure_road_points(self, target_idx):
        while len(self.road_pts) <= target_idx + 4:
            if self.gen_steps_left <= 0:
                roll = random.random()
                if roll < 0.26:
                    self.gen_target_turn = 0.0
                    self.gen_steps_left = random.randint(6, 16)
                elif roll < 0.63:
                    self.gen_target_turn = random.uniform(0.032, 0.075)
                    self.gen_steps_left = random.randint(7, 17)
                else:
                    self.gen_target_turn = -random.uniform(0.032, 0.075)
                    self.gen_steps_left = random.randint(7, 17)
                if self.gen_heading > 0.78:
                    self.gen_target_turn = -random.uniform(0.045, 0.075)
                    self.gen_steps_left = random.randint(9, 15)
                elif self.gen_heading < -0.78:
                    self.gen_target_turn = random.uniform(0.045, 0.075)
                    self.gen_steps_left = random.randint(9, 15)

            self.gen_cur_turn += (self.gen_target_turn - self.gen_cur_turn) * 0.25
            self.gen_heading = max(-1.05, min(1.05, self.gen_heading + self.gen_cur_turn))
            self.gen_steps_left -= 1

            last_p = next(reversed(self.road_pts))
            dx = math.sin(self.gen_heading) * self.seg_len
            dy = math.cos(self.gen_heading) * self.seg_len
            dz = 0.36 + math.sin(len(self.road_pts) * 0.08) * 0.28
            self.road_pts.append(Vec3(last_p.x + dx, last_p.y + dy, last_p.z + dz))

    def get_road_point(self, idx_f):
        i0 = max(0, int(idx_f))
        frac = idx_f - i0
        self.ensure_road_points(i0 + 2)
        p0, p1 = None, None
        for idx_p, pt in enumerate(self.road_pts):
            if idx_p == i0: p0 = pt
            elif idx_p == i0 + 1:
                p1 = pt; break
        return p0 * (1.0 - frac) + p1 * frac

    def spawn_next_segment(self):
        i = self.next_idx
        self.ensure_road_points(i + 3)
        p0, p1, p2 = self.get_road_point(i), self.get_road_point(i + 1), self.get_road_point(i + 2)
        node = self.render.attachNewNode(f'chunk_{i}')

        f1 = Vec3(p1.x - p0.x, p1.y - p0.y, 0); f1.normalize()
        r1 = Vec3(f1.y, -f1.x, 0)
        f2 = Vec3(p2.x - p1.x, p2.y - p1.y, 0); f2.normalize()
        r2 = Vec3(f2.y, -f2.x, 0)

        hw, sw, drop = self.road_w * 0.5, self.road_w * 0.5 + 150.0, 95.0
        l_in1, r_in1, l_in2, r_in2 = p0 - r1 * hw, p0 + r1 * hw, p1 - r2 * hw, p1 + r2 * hw
        l_out1, r_out1 = p0 - r1 * sw - Vec3(0,0,drop), p0 + r1 * sw - Vec3(0,0,drop)
        l_out2, r_out2 = p1 - r2 * sw - Vec3(0,0,drop), p1 + r2 * sw - Vec3(0,0,drop)

        road_col, grass_col, line_col = (0.19, 0.21, 0.25, 1), (0.14, 0.26, 0.11, 1), (0.95, 0.97, 1.0, 1)
        wall_col = (0.68, 0.70, 0.72, 1) if i % 2 == 0 else (0.50, 0.52, 0.55, 1)

        road_quads = []
        sub_steps = 3
        for s in range(sub_steps):
            t0, t1 = s / sub_steps, (s + 1) / sub_steps
            p_a = p0 * (1.0 - t0) + p1 * t0
            p_b = p0 * (1.0 - t1) + p1 * t1
            r_a = r1 * (1.0 - t0) + r2 * t0
            r_b = r1 * (1.0 - t1) + r2 * t1
            road_quads.append(([p_a - r_a*hw, p_a, p_b, p_b - r_b*hw], road_col))
            road_quads.append(([p_a, p_a + r_a*hw, p_b + r_b*hw, p_b], road_col))

        if i > self.next_bridge_idx + 5:
            self.next_bridge_idx = i + random.randint(210, 360)
        if i > self.next_gs_idx + 3:
            self.next_gs_idx = i + random.randint(260, 420)
            if abs(self.next_gs_idx - self.next_bridge_idx) < 25:
                self.next_gs_idx += 35
        if i > self.town_end_idx:
            self.town_start_idx = i + random.randint(180, 320)
            self.town_end_idx = self.town_start_idx + random.randint(14, 24)

        near_gs_seg = (self.next_gs_idx - 2 <= i <= self.next_gs_idx + 2)
        is_bridge_seg = (self.next_bridge_idx <= i <= self.next_bridge_idx + 4)

        quads = road_quads + [
            ([l_in1, l_in1 + Vec3(0,0,0.75), l_in2 + Vec3(0,0,0.75), l_in2], wall_col),
            ([p0 - r1*(hw-0.7) + Vec3(0,0,0.03), p0 - r1*(hw-1.0) + Vec3(0,0,0.03), p1 - r2*(hw-1.0) + Vec3(0,0,0.03), p1 - r2*(hw-0.7) + Vec3(0,0,0.03)], line_col),
            ([p0 + r1*(hw-1.0) + Vec3(0,0,0.03), p0 + r1*(hw-0.7) + Vec3(0,0,0.03), p1 + r2*(hw-0.7) + Vec3(0,0,0.03), p1 + r2*(hw-1.0) + Vec3(0,0,0.03)], line_col)
        ]

        if not is_bridge_seg:
            quads.append(([l_out1, l_in1, l_in2, l_out2], grass_col))
            quads.append(([r_in1, r_out1, r_out2, r_in2], grass_col))
        else:
            canyon_l1 = l_in1 - Vec3(0, 0, 10.5)
            canyon_l2 = l_in2 - Vec3(0, 0, 10.5)
            canyon_r1 = r_in1 - Vec3(0, 0, 10.5)
            canyon_r2 = r_in2 - Vec3(0, 0, 10.5)
            quads.append(([l_out1, canyon_l1, canyon_l2, l_out2], (0.24, 0.25, 0.26, 1)))
            quads.append(([canyon_r1, r_out1, r_out2, canyon_r2], (0.24, 0.25, 0.26, 1)))
            add_river_bridge_segment(quads, p0, p1, r1, r2, hw, is_center_span=(i == self.next_bridge_idx + 2))

        if not near_gs_seg:
            quads.append(([r_in1 + Vec3(0,0,0.75), r_in1, r_in2, r_in2 + Vec3(0,0,0.75)], wall_col))

        if i % 2 == 0:
            quads.append(([p0 - r1*0.16 + Vec3(0,0,0.03), p0 + r1*0.16 + Vec3(0,0,0.03), p1 + r2*0.16 + Vec3(0,0,0.03), p1 - r2*0.16 + Vec3(0,0,0.03)], line_col))

        if i == self.next_gs_idx:
            gs_pos = (p0 + p1) * 0.5 + r1 * (hw + 6.2)
            gs_heading = math.degrees(math.atan2(-f1.x, f1.y))
            gs_node = build_gas_station(self.render, gs_pos, gs_heading)
            self.gas_stations.append({'pos': gs_pos, 'node': gs_node, 'idx': i})

        is_town_zone = (self.town_start_idx <= i <= self.town_end_idx) and not near_gs_seg and not is_bridge_seg
        if is_town_zone and i % 2 == 0:
            side = -1 if (i % 4 == 0) else 1
            h_pos = (p0 + p1) * 0.5 + r1 * (side * (hw + random.uniform(8.0, 18.0)))
            add_house_or_hostel(quads, h_pos.x, h_pos.y, h_pos.z, is_hostel=(i % 6 == 0))

        tree_count = 0 if is_bridge_seg else (10 if is_town_zone else 20)
        for tree_i in range(tree_count):
            side = -1 if tree_i % 2 == 0 else 1
            u = random.uniform(0.14 if is_town_zone else 0.04, 0.94)
            th = random.uniform(8.0, 16.5)
            v = random.uniform(0.05, 0.95)
            if side == -1:
                pt_start, pt_end = l_in1 * (1.0 - u) + l_out1 * u, l_in2 * (1.0 - u) + l_out2 * u
            else:
                pt_start, pt_end = r_in1 * (1.0 - u) + r_out1 * u, r_in2 * (1.0 - u) + r_out2 * u
            t_pos = pt_start * (1.0 - v) + pt_end * v

            too_close = False
            for chk in range(max(0, i - 24), i + 24, 2):
                if abs(chk - i) > 3:
                    rp = self.get_road_point(chk)
                    if math.hypot(t_pos.x - rp.x, t_pos.y - rp.y) < hw + 5.5:
                        too_close = True; break

            if not too_close:
                rnd = random.random()
                if rnd < 0.22: c_dark, c_tip = (0.95, 0.58, 0.76, 1), (1.0, 0.78, 0.88, 1)
                elif rnd < 0.48: c_dark, c_tip = (0.88, 0.45, 0.10, 1), (0.98, 0.72, 0.16, 1)
                elif rnd < 0.78: c_dark, c_tip = (0.05, 0.24, 0.09, 1), (0.09, 0.33, 0.13, 1)
                else: c_dark, c_tip = (0.03, 0.17, 0.06, 1), (0.06, 0.25, 0.09, 1)
                add_tree_with_shadow(quads, t_pos.x, t_pos.y, t_pos.z - 0.15, th * 0.72, th, c_dark, c_tip, -0.8, -0.5)

        chunk_mesh = build_mesh(node, 'batched_chunk', quads)
        chunk_mesh.setTwoSided(True)
        chunk_mesh.setShaderAuto()
        node.flattenStrong()
        self.road_data.append({'idx': i, 'p1': p0, 'p2': p1, 'mid': (p0+p1)*0.5, 'node': node})
        self.next_idx += 1

    def set_key(self, k, val): self.keys[k] = val
    def tune_paint(self):
        self.p_idx = (self.p_idx + 1) % len(self.paints)
        col = self.paints[self.p_idx]
        for b in self.body:
            b.setColorScale(*col)
    def tune_neon(self):
        if self.neon.isHidden(): self.neon.show()
        else: self.neon.hide()
    def spawn_drift_fx(self):
        for side in (-0.85, 0.85):
            wheel_world = self.car_root.getRelativePoint(self.car_visual, Vec3(side, -1.55, 0.15))
            w_pos = self.render.getRelativePoint(self.car_root, wheel_world)

            sk = self.skid_pool[self.skid_ptr]
            sk.setPos(w_pos.x, w_pos.y, w_pos.z - 0.11)
            sk.setH(self.car_root.getH() + self.drift_angle)
            sk.show()
            self.skid_ptr = (self.skid_ptr + 1) % len(self.skid_pool)

            p = self.smoke_pool[self.smoke_ptr]
            np_s = p.get('np')
            np_s.setPos(w_pos.x + random.uniform(-0.2, 0.2), w_pos.y + random.uniform(-0.2, 0.2), w_pos.z + 0.15)
            np_s.setScale(0.45); np_s.setAlphaScale(0.6); np_s.show()
            p.update({'life': 0.50, 'vz': random.uniform(1.2, 2.0)})
            self.smoke_ptr = (self.smoke_ptr + 1) % len(self.smoke_pool)

    def update_game(self, task):
        raw_dt = max(0.001, min(0.05, globalClock.getDt()))
        self.smooth_dt += (raw_dt - self.smooth_dt) * 0.25
        dt = self.smooth_dt

        if self.day_cycle_enabled:
            self.update_dynamic_day_cycle(dt)

        cx, cy = self.car_root.getX(), self.car_root.getY()
        cz = self.car_root.getZ()

        self.bird_time += dt
        for b in self.birds:
            ang = self.bird_time * b.get('speed') + b.get('phase')
            rad = b.get('radius')
            bx = cx + math.cos(ang) * rad
            by = cy + 28.0 + math.sin(ang) * rad
            bz = cz + b.get('height') + math.sin(ang * 2.0) * 1.4
            b_root = b.get('root')
            b_root.setPos(bx, by, bz)
            b_root.setH(math.degrees(ang) + 180.0)
            flap = math.sin(self.bird_time * 9.5 + b.get('phase') * 2.0) * 32.0
            b.get('lw').setR(flap)
            b.get('rw').setR(-flap)

        if self.in_menu:
            self.menu_orbit += dt * 11.0
            ang = math.radians(self.car_root.getH() + self.menu_orbit)
            cam_pos = self.car_root.getPos() + Vec3(math.sin(ang) * 6.4, -math.cos(ang) * 6.4, 1.65)
            self.camera.setPos(self.camera.getPos() + (cam_pos - self.camera.getPos()) * min(1.0, dt * 4.0))
            right_off = Vec3(math.cos(ang) * 1.15, math.sin(ang) * 1.15, 0.85)
            look_pt = self.car_root.getPos() + right_off
            self.cam_look_smooth += (look_pt - self.cam_look_smooth) * min(1.0, dt * 5.0)
            self.camera.lookAt(self.cam_look_smooth)
            self.steppe.setPos(cx, cy, cz - 78.0)
            self.sun_disc.setPos(cx * 0.25 + 350, cy + 2400, cz + 340.0)
            self.horizon_mtns.setPos(cx * 0.65, cy * 0.85, cz - 55.0)
            return task.cont

        max_s, acc = self.stages.get(self.stage)
        throttle = (self.keys.get('w') or self.keys.get('arrow_up')) and self.fuel > 0.0
        braking = self.keys.get('s') or self.keys.get('arrow_down')
        space_held = self.keys.get('space')
        raw_steer = (1.0 if (self.keys.get('a') or self.keys.get('arrow_left')) else 0.0) - (1.0 if (self.keys.get('d') or self.keys.get('arrow_right')) else 0.0)

        if throttle:
            self.fuel = max(0.0, self.fuel - dt * (0.14 + (abs(self.speed) / max_s) * 0.22))

        speed_factor = max(0.38, 1.0 - (abs(self.speed) / max_s) * 0.55)
        steer_speed = 6.2 if abs(raw_steer) > 0.1 else 8.5
        self.smooth_steer += (raw_steer - self.smooth_steer) * min(1.0, dt * steer_speed)

        target_pitch = 0.0
        if throttle:
            torque = acc * (1.15 - 0.45 * (max(0.0, self.speed) / max_s))
            self.speed += torque * dt
            target_pitch = -1.8
        elif braking:
            if self.speed > 1.0:
                self.speed -= acc * 1.45 * dt
                target_pitch = 2.4
            else:
                self.speed -= acc * 0.75 * dt
                target_pitch = 1.0
        else:
            drag = 4.5 + abs(self.speed) * 0.12
            if abs(self.speed) > 0.15:
                self.speed -= (drag if self.speed > 0 else -drag) * dt
            else:
                self.speed = 0.0

        if braking or space_held:
            for tl in self.taillights:
                tl.show(); tl.setLightOff(); tl.setColorScale(3.2, 0.22, 0.18, 1)
        elif self.lights_on:
            for tl in self.taillights:
                tl.show(); tl.setLightOff(); tl.setColorScale(1.7, 0.25, 0.20, 1)
        else:
            for tl in self.taillights:
                if 'glow' in tl.getName(): tl.hide()
                else: tl.clearLight(); tl.clearColorScale()

        is_drifting = space_held and self.speed > 13.0 and (abs(self.smooth_steer) > 0.08 or abs(self.drift_angle) > 6.0)
        if is_drifting:
            self.speed -= 2.2 * dt if throttle else 5.5 * dt
            target_slip = self.smooth_steer * 38.0
            self.drift_angle += (target_slip - self.drift_angle) * min(1.0, dt * 4.2)
            target_yaw_rate = self.smooth_steer * 96.0
            self.drift_timer = 1.8
            self.drift_combo = min(5.0, self.drift_combo + dt * 0.40)
            self.drift_score += abs(self.speed) * (abs(self.drift_angle) / 18.0) * 14.0 * self.drift_combo * dt
            self.hud_drift.show()
            self.hud_drift.setText(f'DRIFT: {int(self.drift_score)}  (x{self.drift_combo:.1f})')
            self.spawn_drift_fx()
        else:
            self.drift_angle += (0.0 - self.drift_angle) * min(1.0, dt * 4.8)
            d_sign = 1.0 if self.speed >= 0 else -1.0
            grip_scale = min(1.0, abs(self.speed) / 8.0)
            target_yaw_rate = self.smooth_steer * 68.0 * speed_factor * grip_scale * d_sign
            if self.drift_timer > 0:
                self.drift_timer -= dt
                if self.drift_timer <= 0:
                    self.drift_score = 0.0; self.drift_combo = 1.0; self.hud_drift.setText(''); self.hud_drift.hide()

        self.speed = max(-18.0, min(max_s, self.speed))
        self.angular_vel += (target_yaw_rate - self.angular_vel) * min(1.0, dt * 7.5)
        self.car_root.setH(self.car_root.getH() + self.angular_vel * dt)

        heading_rad = math.radians(self.car_root.getH() - self.drift_angle * 0.35)
        target_vel = Vec3(-math.sin(heading_rad) * self.speed, math.cos(heading_rad) * self.speed, 0)
        grip_align = 3.2 if is_drifting else 9.5
        self.vel_vec += (target_vel - self.vel_vec) * min(1.0, dt * grip_align)

        self.car_root.setX(self.car_root.getX() + self.vel_vec.x * dt)
        self.car_root.setY(self.car_root.getY() + self.vel_vec.y * dt)

        kmh_now = abs(self.speed) * 4.4
        dist_step_km = (kmh_now / 3600.0) * dt
        self.trip_dist_km += dist_step_km
        self.total_dist_km += dist_step_km
        if self.trip_dist_km > self.best_dist_km:
            self.best_dist_km = self.trip_dist_km

        self.save_timer += dt
        if self.save_timer >= 10.0:
            self.save_timer = 0.0
            self.save_progress()

        target_roll = -self.smooth_steer * min(4.2, (abs(self.speed) / max_s) * 4.5 + abs(self.drift_angle) * 0.05)
        self.sus_roll += (target_roll - self.sus_roll) * min(1.0, dt * 6.5)
        self.sus_pitch += (target_pitch - self.sus_pitch) * min(1.0, dt * 6.0)

        self.car_visual.setH(self.drift_angle)
        self.car_sus.setR(self.sus_roll)
        self.car_sus.setP(self.sus_pitch)

        for p in self.smoke_pool:
            life = p.get('life')
            if life > 0:
                life -= dt
                np_s = p.get('np')
                if life > 0:
                    np_s.setZ(np_s.getZ() + p.get('vz') * dt)
                    np_s.setScale(np_s.getScale().x + dt * 2.2)
                    np_s.setAlphaScale(max(0.0, life * 1.2))
                else:
                    np_s.hide()
                p.update({'life': life})

        cx, cy = self.car_root.getX(), self.car_root.getY()

        near_gas = False
        refueling = False
        for gs in self.gas_stations:
            gp = gs.get('pos')
            d_gs = math.hypot(cx - gp.x, cy - gp.y)
            if d_gs < 11.5:
                near_gas = True
                if kmh_now < 45.0 and self.fuel < 99.8:
                    refueling = True
                    self.fuel = min(100.0, self.fuel + dt * 32.0)

        if refueling:
            self.hud_alert.show()
            self.hud_alert.setFg((0.25, 1.0, 0.45, 1))
            self.hud_alert.setText(f'ЗАПРАВКА ТОПЛИВА... {int(self.fuel)}%')
        elif near_gas and self.fuel < 95.0:
            self.hud_alert.show()
            self.hud_alert.setFg((0.95, 0.90, 0.35, 1))
            self.hud_alert.setText('ВЫ НА АЗС — ПРИТОРМОЗИТЕ ДЛЯ ЗАПРАВКИ')
        elif self.fuel <= 0.1:
            self.hud_alert.show()
            self.hud_alert.setFg((1.0, 0.25, 0.25, 1))
            self.hud_alert.setText('КОНЧИЛСЯ БЕНЗИН! НАЖМИТЕ [R] ИЛИ НАЧНИТЕ ЗАНОВО В МЕНЮ')
        elif self.fuel < 20.0:
            self.hud_alert.show()
            self.hud_alert.setFg((1.0, 0.65, 0.20, 1))
            self.hud_alert.setText(f'МАЛО ТОПЛИВА ({int(self.fuel)}%) — ИЩИТЕ АЗС СПРАВА')
        else:
            self.hud_alert.hide()

        last_seg = next(reversed(self.road_data))
        while last_seg.get('mid').y < cy + 450:
            self.spawn_next_segment()
            last_seg = next(reversed(self.road_data))

        while len(self.road_data) > 105:
            first_seg = next(iter(self.road_data))
            if first_seg.get('mid').y < cy - 90:
                first_seg.get('node').removeNode()
                self.road_data.pop(0)
            else:
                break

        while self.gas_stations and next(iter(self.gas_stations)).get('pos').y < cy - 120:
            old_gs = self.gas_stations.pop(0)
            old_gs.get('node').removeNode()
        best_seg, min_d2 = None, 1e9
        for seg in self.road_data:
            mid = seg.get('mid')
            d2 = (cx - mid.x)**2 + (cy - mid.y)**2
            if d2 < min_d2:
                min_d2, best_seg = d2, seg

        if best_seg is not None:
            p1, p2 = best_seg.get('p1'), best_seg.get('p2')
            seg_vec = p2 - p1
            seg_len_sq = seg_vec.x**2 + seg_vec.y**2
            t_proj = max(0.0, min(1.0, ((cx - p1.x)*seg_vec.x + (cy - p1.y)*seg_vec.y) / seg_len_sq))
            closest = p1 + seg_vec * t_proj
            self.car_root.setZ(closest.z + 0.06)
            slope_deg = math.degrees(math.atan2(seg_vec.z, math.hypot(seg_vec.x, seg_vec.y)))
            self.car_root.setP(slope_deg)

            right_vec = Vec3(seg_vec.y, -seg_vec.x, 0); right_vec.normalize()
            total_car_rad = math.radians(self.car_root.getH() + self.drift_angle)
            car_fwd = Vec3(-math.sin(total_car_rad), math.cos(total_car_rad), 0)
            car_right = Vec3(math.cos(total_car_rad), math.sin(total_car_rad), 0)

            half_w, half_l = 0.96, 2.32
            max_left_wall = (self.road_w * 0.5) - 0.15
            max_right_wall = (self.road_w * 0.5 + 11.5) if near_gas else ((self.road_w * 0.5) - 0.15)
            max_penetration = 0.0
            hit_sign = 0.0

            for sx in (-half_w, half_w):
                for sy in (-half_l, half_l):
                    corner_x = cx + car_right.x * sx + car_fwd.x * sy
                    corner_y = cy + car_right.y * sx + car_fwd.y * sy
                    lat = (corner_x - closest.x) * right_vec.x + (corner_y - closest.y) * right_vec.y
                    limit = max_right_wall if lat > 0 else max_left_wall
                    if abs(lat) > limit:
                        pen = abs(lat) - limit
                        if pen > max_penetration:
                            max_penetration = pen
                            hit_sign = 1.0 if lat > 0 else -1.0

            if max_penetration > 0.0:
                self.car_root.setX(cx - right_vec.x * hit_sign * max_penetration)
                self.car_root.setY(cy - right_vec.y * hit_sign * max_penetration)
                vn = self.vel_vec.x * right_vec.x + self.vel_vec.y * right_vec.y
                if vn * hit_sign > 0:
                    self.vel_vec -= right_vec * (vn * 1.15)
                self.speed *= 0.90

        if self.traffic:
            max_t_idx = max(t.get('idx') for t in self.traffic)
            for t in self.traffic:
                t_idx = t.get('idx') + (t.get('spd') / self.seg_len) * dt
                if t_idx * self.seg_len < cy - 80:
                    t_idx = max(max_t_idx + 24.0, (cy + 360.0) / self.seg_len)
                    max_t_idx = t_idx
                t.update({'idx': t_idx})
                p_curr, p_next = self.get_road_point(t_idx), self.get_road_point(t_idx + 0.5)
                fwd = p_next - p_curr
                right = Vec3(fwd.y, -fwd.x, 0); right.normalize()
                lane = t.get('lane')
                t_pos = p_curr + right * lane + Vec3(0, 0, 0.06)
                t_np = t.get('np')
                t_np.setPos(t_pos); t_np.lookAt(p_next + right * lane + Vec3(0, 0, 0.06))
                for w in t.get('wheels'):
                    w.get('spin').setP(w.get('spin').getP() - t.get('spd') * 35 * dt)

                dx, dy = self.car_root.getX() - t_pos.x, self.car_root.getY() - t_pos.y
                dist_2d = math.hypot(dx, dy)
                if 0.01 < dist_2d < 2.8:
                    push = (2.85 - dist_2d)
                    self.car_root.setX(self.car_root.getX() + (dx / dist_2d) * push)
                    self.car_root.setY(self.car_root.getY() + (dy / dist_2d) * push)
                    self.vel_vec *= 0.65
                    self.speed *= 0.65

        cz = self.car_root.getZ()
        self.steppe.setPos(cx, cy, cz - 78.0)
        self.sun_disc.setPos(cx * 0.25 + 350, cy + 2400, cz + 340.0)
        self.horizon_mtns.setPos(cx * 0.65, cy * 0.85, cz - 55.0)

        for w in self.wheels:
            sp = w.get('spin')
            sp.setP(sp.getP() - self.speed * 42.0 * dt)
            if w.get('is_front'):
                w.get('steer').setH(self.smooth_steer * 28.0 - self.drift_angle * 0.55)

        speed_ratio = abs(self.speed) / max_s
        target_fov = 56.0 + speed_ratio * 15.0
        cur_fov = self.camLens.getHfov()
        self.camLens.setFov(cur_fov + (target_fov - cur_fov) * min(1.0, dt * 4.5))

        if self.rmb_down and self.mouseWatcherNode.hasMouse():
            m = self.mouseWatcherNode.getMouse()
            mx, my = m.getX(), m.getY()
            if self.last_mouse is not None:
                lx, ly = self.last_mouse
                self.cam_yaw -= (mx - lx) * 140.0
                self.cam_pitch = max(4.0, min(65.0, self.cam_pitch - (my - ly) * 90.0))
            self.last_mouse = (mx, my)
        elif abs(self.speed) > 1.5:
            self.cam_yaw *= max(0.0, 1.0 - dt * 2.5)
            self.cam_pitch += (14.5 - self.cam_pitch) * min(1.0, dt * 2.5)

        cam_dist = 9.4 + speed_ratio * 2.6
        total_yaw = math.radians(self.car_root.getH() + self.cam_yaw + self.drift_angle * 0.45)
        pitch_rad = math.radians(self.cam_pitch)
        horiz_d, vert_d = cam_dist * math.cos(pitch_rad), cam_dist * math.sin(pitch_rad)

        offset = Vec3(math.sin(total_yaw) * horiz_d, -math.cos(total_yaw) * horiz_d, vert_d + 0.95)
        target_pos = self.car_root.getPos() + offset
        cam_lerp = 1.0 - math.exp(-dt * 8.5)
        self.camera.setPos(self.camera.getPos() + (target_pos - self.camera.getPos()) * cam_lerp)

        raw_look = self.car_root.getPos() + Vec3(-math.sin(total_yaw) * 1.5, math.cos(total_yaw) * 1.5, 1.1)
        look_lerp = 1.0 - math.exp(-dt * 12.0)
        self.cam_look_smooth += (raw_look - self.cam_look_smooth) * look_lerp
        self.camera.lookAt(self.cam_look_smooth)

        max_kmh = max_s * 4.4
        gear_span = max_kmh / 6.0
        self.gear = max(1, min(6, int(kmh_now / max(1.0, gear_span)) + 1)) if self.speed >= 0 else 0
        gear_in_ratio = (kmh_now % max(1.0, gear_span)) / max(1.0, gear_span)
        target_rpm = 950.0 + (gear_in_ratio * 6600.0 if kmh_now > 2.0 else (1800.0 if throttle else 0.0))
        self.rpm += (target_rpm - self.rpm) * min(1.0, dt * 12.0)

        bars = int((self.rpm / 8000.0) * 20)
        self.hud_spd.setText(f'{int(kmh_now)}')
        self.hud_gear.setText('R' if self.speed < -0.5 else str(self.gear))
        self.hud_rpm_txt.setText(f'{int(self.rpm)} RPM')
        self.hud_rpm_bar.setText('|' * bars + '.' * (20 - bars))
        self.hud_rpm_bar.setFg((1.0, 0.22, 0.25, 1) if self.rpm > 6600 else (0.25, 0.95, 0.55, 1))
        self.hud_fuel.setText(f'БАК: {int(self.fuel)}%')
        self.hud_fuel.setFg((1.0, 0.25, 0.25, 1) if self.fuel < 20.0 else (0.35, 0.95, 0.55, 1))
        self.hud_dist.setText(f'ДИСТАНЦИЯ: {self.trip_dist_km:.2f} КМ  |  РЕКОРД: {self.best_dist_km:.2f} КМ')

        if self.snd_engine is not None:
            rpm_ratio = max(0.0, min(1.0, (self.rpm - 900.0) / 6800.0))
            self.snd_engine.setPlayRate(0.68 + rpm_ratio * 1.45)
            self.snd_engine.setVolume(0.24 + (0.28 if throttle else 0.08) + rpm_ratio * 0.22)

        if self.snd_screech is not None:
            if is_drifting and abs(self.drift_angle) > 8.0:
                if self.snd_screech.status() != self.snd_screech.PLAYING:
                    self.snd_screech.play()
                drift_int = min(1.0, abs(self.drift_angle) / 34.0)
                self.snd_screech.setVolume(0.18 + drift_int * 0.45)
                self.snd_screech.setPlayRate(0.92 + drift_int * 0.22)
            else:
                if self.snd_screech.status() == self.snd_screech.PLAYING:
                    self.snd_screech.stop()

        if self.snd_birds is not None:
            bird_vol = max(0.08, 0.48 - (kmh_now / 220.0) * 0.35)
            self.snd_birds.setVolume(bird_vol)

        return task.cont

app = ForzaHorizonInfinite()
app.run()
