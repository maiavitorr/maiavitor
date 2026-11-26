#!/usr/bin/env python3
"""
Placa de sinalização da garagem da clínica — 2 módulos de 210 x 210 mm.

  Módulo 1: GARAGEM + ícone de ambulância + ENTRADA DE AMBULÂNCIAS
  Módulo 2: símbolo "proibido estacionar" (E cortado) + PROIBIDO ESTACIONAR

Cada módulo é impresso à parte, de frente para cima, em 3 corpos (um por cor):
  amarelo  -> chapa-base (3,0 mm)
  preto    -> moldura + textos + ícones em relevo (1,6 mm)
  vermelho -> anel/tarja do símbolo e cruz da ambulância em relevo (1,6 mm)

Uso:   python3 gerar_placa.py            (gera stl/, 3mf/ e preview/)
Requer: numpy shapely trimesh mapbox_earcut matplotlib  (pip install ...)
Todas as medidas em milímetros. Edite as constantes abaixo para ajustar.
"""
import os
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# --------------------------------------------------------------------------
# PARÂMETROS
# --------------------------------------------------------------------------
TILE = 210.0            # lado do módulo (mm). X2D: 256x256 (235,5x256 com 2 bicos)
CORNER_R = 12.0         # raio dos cantos da chapa
BASE_T = 3.0            # espessura da chapa amarela (15 camadas de 0,2)
RELIEF_T = 1.6          # altura do relevo preto/vermelho (8 camadas de 0,2)
FRAME_OFFSET = 4.0      # distância da borda até a moldura preta
FRAME_W = 9.0           # largura da moldura preta
HOLE_D = 5.0            # furo de fixação (parafuso até 4,5 mm), 4 cantos
CONTENT_MARGIN = 5.0    # folga entre moldura e conteúdo
GAP_MODULES = 4.0       # folga prevista entre módulos na parede (só no preview)

FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
XSCALE = 0.90           # leve condensação das letras (mais altura por largura)

OUT = os.path.dirname(os.path.abspath(__file__))
COLORS = {"amarelo": "#FFC400", "preto": "#141414", "vermelho": "#D8231C"}

# --------------------------------------------------------------------------
# TEXTO -> GEOMETRIA 2D
# --------------------------------------------------------------------------
_fp = FontProperties(fname=FONT)


def _glyphs(txt):
    """Contorno do texto em unidades de 'em' (1 = tamanho da fonte)."""
    tp = TextPath((0, 0), txt, size=1000, prop=_fp)
    rings = [r for r in tp.to_polygons(closed_only=True) if len(r) >= 4]
    polys = [Polygon(r).buffer(0) for r in rings]
    polys = [p for p in polys if not p.is_empty]
    # a maior área define o sentido "externo"; o oposto são os furos (A, B, D, O, P, R...)
    from shapely.geometry.polygon import LinearRing
    signs = []
    for r in rings:
        signs.append(1 if LinearRing(r).is_ccw else -1)
    big = max(range(len(polys)), key=lambda i: polys[i].area)
    outer_sign = signs[big]
    outers = unary_union([p for p, s in zip(polys, signs) if s == outer_sign])
    holes = [p for p, s in zip(polys, signs) if s != outer_sign]
    g = outers.difference(unary_union(holes)) if holes else outers
    return affinity.scale(g, xfact=XSCALE * 0.001, yfact=0.001, origin=(0, 0))


CAP_EM = _glyphs("H").bounds[3]          # altura de maiúscula em 'em'


def cap_for_width(txt, width):
    b = _glyphs(txt).bounds
    return width / (b[2] - b[0]) * CAP_EM


def text_line(txt, cap, baseline=0.0, cx=0.0):
    g = _glyphs(txt)
    s = cap / CAP_EM
    g = affinity.scale(g, s, s, origin=(0, 0))
    b = g.bounds
    return affinity.translate(g, cx - (b[0] + b[2]) / 2, baseline)


def text_block(lines, cap, leading=1.42):
    parts = [text_line(t, cap, baseline=-i * cap * leading) for i, t in enumerate(lines)]
    return unary_union(parts)


# --------------------------------------------------------------------------
# ELEMENTOS GRÁFICOS
# --------------------------------------------------------------------------
def rounded_box(x0, y0, x1, y1, r):
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=24)


def circle(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=48)


def ambulance(width):
    """Ambulância de lado, virada para a direita. Retorna (preto, vermelho)
    com origem no centro da caixa delimitadora e largura = `width`."""
    box_body = rounded_box(0, 10, 78, 50, 4)
    cab = Polygon([(76, 10), (76, 40), (97, 40), (111, 27), (122, 25), (124, 22), (124, 10)])
    beacon = rounded_box(58, 48.5, 70, 56, 1.5)
    body = unary_union([box_body, cab, beacon])
    body = body.buffer(2.0).buffer(-2.0)          # arredonda cantos côncavos
    body = body.buffer(-1.2).buffer(1.2)          # arredonda cantos convexos
    window = Polygon([(81, 36.5), (94.5, 36.5), (104.5, 28.5), (81, 28.5)]).buffer(1.0).buffer(-1.0)
    wheel_c = [(22, 11), (98, 11)]
    for cx, cy in wheel_c:
        body = body.difference(circle(cx, cy, 14.5))
    body = body.difference(window)
    cross = unary_union([box(39 - 13, 30 - 4, 39 + 13, 30 + 4), box(39 - 4, 30 - 13, 39 + 4, 30 + 13)])
    body = body.difference(cross.buffer(2.2, join_style="mitre"))
    wheels = unary_union([circle(cx, cy, 10.5).difference(circle(cx, cy, 4.2)) for cx, cy in wheel_c])
    black = unary_union([body, wheels])
    red = cross
    b = unary_union([black, red]).bounds
    k = width / (b[2] - b[0])
    tr = lambda g: affinity.translate(
        affinity.scale(g, k, k, origin=(0, 0)), -k * (b[0] + b[2]) / 2, -k * (b[1] + b[3]) / 2)
    return tr(black), tr(red)


def no_parking(diameter, ring_w):
    """Símbolo de proibido estacionar: anel + tarja vermelhos, 'E' de Estacionar em preto."""
    R = diameter / 2
    ring = circle(0, 0, R).difference(circle(0, 0, R - ring_w))
    slash_w = ring_w * 0.82
    bar = LineString([(-R, R), (R, -R)]).buffer(slash_w / 2, cap_style="flat")
    slash = bar.intersection(circle(0, 0, R - 0.01))
    red = unary_union([ring, slash])
    letter = text_line("E", cap=diameter * 0.56, baseline=0)
    b = letter.bounds
    letter = affinity.translate(letter, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)
    black = letter.difference(bar.buffer(1.5))
    return black, red


# --------------------------------------------------------------------------
# MÓDULOS
# --------------------------------------------------------------------------
H = TILE / 2


def base_and_frame():
    base = rounded_box(-H, -H, H, H, CORNER_R)
    o = FRAME_OFFSET
    outer = rounded_box(-H + o, -H + o, H - o, H - o, CORNER_R - o)
    inner = rounded_box(-H + o + FRAME_W, -H + o + FRAME_W, H - o - FRAME_W, H - o - FRAME_W, 2.0)
    c = H - o - FRAME_W / 2
    holes = unary_union([circle(sx * c, sy * c, HOLE_D / 2) for sx in (-1, 1) for sy in (-1, 1)])
    return base.difference(holes), outer.difference(inner).difference(holes)


def stack(items, gaps):
    """Empilha geometrias de cima p/ baixo (por caixa delimitadora) e centraliza em y=0."""
    heights = [g.bounds[3] - g.bounds[1] for g in items]
    total = sum(heights) + sum(gaps)
    y = total / 2
    out = []
    for g, h, gap in zip(items, heights, list(gaps) + [0]):
        b = g.bounds
        out.append(affinity.translate(g, -(b[0] + b[2]) / 2, y - b[3]))
        y -= h + gap
    return out, total


def module1():
    base, frame = base_and_frame()
    inner_w = TILE - 2 * (FRAME_OFFSET + FRAME_W + CONTENT_MARGIN)
    cap_title = min(cap_for_width("GARAGEM", inner_w), 36)
    cap_body = min(cap_for_width("AMBULÂNCIAS", inner_w), cap_for_width("ENTRADA DE", inner_w), 25)
    title = text_line("GARAGEM", cap_title)
    amb_black, amb_red = ambulance(width=124)
    body = text_block(["ENTRADA DE", "AMBULÂNCIAS"], cap_body)
    # empilha usando o ícone completo como referência de altura
    icon_all = unary_union([amb_black, amb_red])
    (t, ic, bd), total = stack([title, icon_all, body], [10, 11])
    ib = icon_all.bounds
    iy = ic.bounds
    dx, dy = (iy[0] + iy[2]) / 2 - (ib[0] + ib[2]) / 2, (iy[1] + iy[3]) / 2 - (ib[1] + ib[3]) / 2
    amb_black = affinity.translate(amb_black, dx, dy)
    amb_red = affinity.translate(amb_red, dx, dy)
    black = unary_union([frame, t, amb_black, bd])
    return {"amarelo": base, "preto": black, "vermelho": amb_red}, dict(cap_title=cap_title, cap_body=cap_body, content_h=total, inner=inner_w)


def module2():
    base, frame = base_and_frame()
    inner_w = TILE - 2 * (FRAME_OFFSET + FRAME_W + CONTENT_MARGIN)
    cap = min(cap_for_width("ESTACIONAR", inner_w), cap_for_width("PROIBIDO", inner_w), 25)
    sym_black, sym_red = no_parking(diameter=100, ring_w=11)
    sym_all = unary_union([sym_black, sym_red])
    text = text_block(["PROIBIDO", "ESTACIONAR"], cap, leading=1.38)
    (s, tx), total = stack([sym_all, text], [11])
    sb, ss = sym_all.bounds, s.bounds
    dx, dy = (ss[0] + ss[2]) / 2 - (sb[0] + sb[2]) / 2, (ss[1] + ss[3]) / 2 - (sb[1] + sb[3]) / 2
    sym_black = affinity.translate(sym_black, dx, dy)
    sym_red = affinity.translate(sym_red, dx, dy)
    black = unary_union([frame, sym_black, tx])
    return {"amarelo": base, "preto": black, "vermelho": sym_red}, dict(cap_body=cap, content_h=total, inner=inner_w)


# --------------------------------------------------------------------------
# MALHAS 3D / EXPORTAÇÃO
# --------------------------------------------------------------------------
def clean(g, min_area=0.05):
    g = g.buffer(0)
    polys = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    return [orient(p, 1.0) for p in polys if p.geom_type == "Polygon" and p.area > min_area]


def extrude(g, height, z0):
    meshes = []
    for p in clean(g):
        m = trimesh.creation.extrude_polygon(p.simplify(0.01), height)
        m.apply_translation([0, 0, z0])
        meshes.append(m)
    return trimesh.util.concatenate(meshes)


def build_meshes(layers):
    return {
        "amarelo": extrude(layers["amarelo"], BASE_T, 0.0),
        "preto": extrude(layers["preto"], RELIEF_T, BASE_T),
        "vermelho": extrude(layers["vermelho"], RELIEF_T, BASE_T),
    }


def write_3mf(path, title, parts, center=(128.0, 128.0)):
    """3MF padrão (spec core): 1 objeto com 3 componentes nomeados (um por cor)."""
    ids, xml = [], []
    for i, (name, m) in enumerate(parts, start=1):
        v = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        xml.append(f'<object id="{i}" name="{escape(name)}" type="model"><mesh><vertices>{v}</vertices>'
                   f'<triangles>{t}</triangles></mesh></object>')
        ids.append(i)
    parent = len(parts) + 1
    comps = "".join(f'<component objectid="{i}"/>' for i in ids)
    xml.append(f'<object id="{parent}" name="{escape(title)}" type="model"><components>{comps}</components></object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="pt-BR" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{escape(title)}</metadata>'
             f'<resources>{"".join(xml)}</resources>'
             f'<build><item objectid="{parent}" transform="1 0 0 0 1 0 0 0 1 {center[0]} {center[1]} 0"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


# --------------------------------------------------------------------------
# PREVIEW
# --------------------------------------------------------------------------
def draw(ax, g, color, dx=0.0, dy=0.0, shadow=False, z=1):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    for p in clean(g):
        verts, codes = [], []
        for ring in [p.exterior, *p.interiors]:
            xy = np.asarray(ring.coords)
            verts.extend(xy + [dx, dy])
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY])
        path = Path(verts, codes)
        if shadow:
            sv = np.asarray(verts) + [1.1, -1.1]
            ax.add_patch(PathPatch(Path(sv, codes), fc="black", ec="none", alpha=0.28, zorder=z))
        ax.add_patch(PathPatch(path, fc=color, ec="none", zorder=z + 1))


def render_preview(mods, path_png, stacked=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    n = len(mods)
    step = TILE + GAP_MODULES
    if stacked:
        W, Hh = TILE, n * TILE + (n - 1) * GAP_MODULES
    else:
        W, Hh = n * TILE + (n - 1) * GAP_MODULES, TILE
    fig, ax = plt.subplots(figsize=(W / 55 + 1, Hh / 55 + 1.2), dpi=170)
    for i, layers in enumerate(mods):
        dx = 0 if stacked else i * step
        dy = -i * step if stacked else 0
        if stacked:
            dy = (Hh - TILE) / 2 - i * step
        else:
            dx = i * step - (W - TILE) / 2
        draw(ax, layers["amarelo"], COLORS["amarelo"], dx, dy, shadow=True, z=1)
        # a base não tem relevo, mas o contorno dá noção de espessura
        draw(ax, layers["preto"], COLORS["preto"], dx, dy, shadow=True, z=10)
        draw(ax, layers["vermelho"], COLORS["vermelho"], dx, dy, shadow=True, z=20)
    ax.set_xlim(-W / 2 - 6, W / 2 + 6)
    ax.set_ylim(-Hh / 2 - 6, Hh / 2 + 6)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#DDDDDD")
    lbl = f"{int(W)} x {int(Hh)} mm (L x A)"
    if n == 1:
        ax.set_title(f"Placa da garagem — módulo de {int(TILE)} x {int(TILE)} mm", fontsize=8)
    else:
        ax.set_title(f"Placa da garagem — {n} módulos de {int(TILE)} x {int(TILE)} mm — {lbl}, com {GAP_MODULES:g} mm de folga", fontsize=8)
    fig.savefig(path_png, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


# --------------------------------------------------------------------------
def main():
    specs = [("modulo1_garagem_ambulancia", module1), ("modulo2_proibido_estacionar", module2)]
    mods = []
    report = []
    for slug, fn in specs:
        layers, info = fn()
        mods.append(layers)
        meshes = build_meshes(layers)
        for color, m in meshes.items():
            m.export(os.path.join(OUT, "stl", f"{slug}_{color}.stl"))
            report.append((slug, color, m))
        write_3mf(os.path.join(OUT, "3mf", f"{slug}.3mf"), slug, list(meshes.items()))
        render_preview([layers], os.path.join(OUT, "preview", f"{slug}.png"))
        print(slug, {k: round(v, 1) for k, v in info.items()})
    render_preview(mods, os.path.join(OUT, "preview", "placa_lado_a_lado.png"))
    render_preview(mods, os.path.join(OUT, "preview", "placa_empilhada.png"), stacked=True)
    print()
    for slug, color, m in report:
        print(f"{slug:32s} {color:9s} wt={m.is_watertight!s:5s} vol={m.volume/1000:7.2f} cm3 "
              f"bounds={np.round(m.bounds[1]-m.bounds[0],1)}")


if __name__ == "__main__":
    main()
