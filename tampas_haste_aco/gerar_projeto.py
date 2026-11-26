#!/usr/bin/env python3
"""
Gerador do projeto Bambu Studio (.3mf) com TAMPAS + BUCHAS das hastes de aço do
rack de filamento.  Refaz o projeto antigo com as medidas REAIS (fotos de 26/11/2026)
e monta uma placa de TESTE com vários tamanhos parecidos, cada peça identificável.

  Tampas : 10 diâmetros de pino (16,00 → 16,90) — Ø interno real da haste = 16,26
  Buchas :  8 pares (Ø externo do corpo, Ø do furo) em "diagonal"  — haste Ø 19,10,
            furo real do rack = 21,05.
  Cada peça leva APENAS um número gravado (a tabela número → medida fica no README).

Saídas (pasta --saida):
  <nome>.3mf           projeto completo (perfil da A1 copiado do seu projeto do dachshund)
  <nome>_placa.stl     alternativa: mesma placa em um único STL (qualquer fatiador abre)
  <nome>_3d.png        render de conferência
  <nome>_preview.png   conferência visual (layout, cortes, tabela)

Dependências: numpy, scipy, networkx, shapely, rtree, trimesh, manifold3d, matplotlib, pillow
"""
from __future__ import annotations

import argparse
import uuid
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
BASE_3MF = AQUI.parent / "AMS_DOG_CANDLE_dachshund_dapple.3mf"   # fonte do perfil da A1
DATA = "2026-11-26"
SEGMENTOS = 360          # facetas por círculo (erro de diâmetro < 0,001 mm)

# ───────────────────── Medidas reais (paquímetro, fotos 26/11/2026) ──────────────────
TUBO_DE = 19.10          # foto 2 — Ø externo da haste
TUBO_DI = 16.26          # foto 3 — Ø interno da haste (parede ≈ 1,42)
FURO_RACK = 21.05        # furo do rack IMPRESSO (nome do arquivo antigo; modelo = 21,32) — confirmar

# ───────────────────────── Tampa (geometria do projeto antigo) ────────────────────────
T_FLANGE_D, T_FLANGE_H = 34.0, 3.1
T_CH_R, T_CH_H = 1.36, 1.6       # chanfro na base do flange (pé de elefante)
T_PINO_L = 20.5                  # comprimento do pino
T_PONTA_R, T_PONTA_H = 0.75, 2.0 # afilamento da ponta
T_PINOS = [round(16.00 + 0.10 * i, 2) for i in range(10)]            # Ø do pino (teste)

# ───────────────────────── Bucha (geometria do projeto antigo) ────────────────────────
B_FLANGE_D, B_FLANGE_H, B_CORPO_L = 23.4, 1.5, 9.0   # B_FLANGE_D = flange de produção (projeto antigo)
B_FLANGE_TESTE = 32.0            # flange só da placa de TESTE: precisa de espaço para gravar o número
B_CH_FURO = 0.5                  # chanfro de entrada da haste (lado do flange)  [NOVO]
B_PONTA_R, B_PONTA_H = 0.3, 0.6  # chanfro externo na ponta do corpo             [NOVO]
B_OD = [round(20.65 + 0.10 * i, 2) for i in range(8)]                # Ø externo do corpo
B_FURO = [round(19.00 + 0.10 * i, 2) for i in range(8)]              # Ø do furo (haste)

TEXTO_PROF = 0.4                 # gravação do rótulo (2 camadas de 0,2 mm)
CENTRO = (128.0, 128.0)          # centro da mesa 256 × 256 (A1)


# ─────────────────────────────────── Modelagem ───────────────────────────────────────
def revolver(pts) -> Manifold:
    return Manifold.revolve(CrossSection([np.array(pts, dtype=float)]), SEGMENTOS)


def _poligonos_texto(txt, larg_max, alt_max, espelhar):
    polys = TextPath((0, 0), txt, size=100,
                     prop=FontProperties(family="DejaVu Sans", weight="bold")).to_polygons()
    (x0, y0), (x1, y1) = np.vstack(polys).min(0), np.vstack(polys).max(0)
    s = min(larg_max / (x1 - x0), alt_max / (y1 - y0))
    out = []
    for p in polys:
        q = (p - ((x0 + x1) / 2, (y0 + y1) / 2)) * s
        if espelhar:
            q[:, 0] *= -1
        out.append(q)
    return out


def gravura(txt, z0, larg_max, alt_max, centro=(0.0, 0.0)) -> Manifold:
    cs = CrossSection(_poligonos_texto(txt, larg_max, alt_max, False), FillRule.EvenOdd)
    return Manifold.extrude(cs, TEXTO_PROF + 0.5).translate((centro[0], centro[1], z0))


def tampa(d_pino: float, numero: int) -> Manifold:
    rf, rp, h = T_FLANGE_D / 2, d_pino / 2, T_FLANGE_H
    topo = h + T_PINO_L + T_PONTA_H
    peca = revolver([(0, 0), (rf - T_CH_R, 0), (rf, T_CH_H), (rf, h), (rp, h),
                     (rp, h + T_PINO_L), (rp - T_PONTA_R, topo), (0, topo)])
    # Número gravado na face superior do flange (anel entre o pino e a borda), à frente (−Y).
    # Superfície voltada para cima → imprime limpo, sem ponte (texto na face da mesa gerava aviso de ponte longa).
    return peca - gravura(str(numero), h - TEXTO_PROF, 9.0, 5.0, centro=(0.0, -(rp + rf) / 2))


def bucha(od: float, furo: float, numero: int, flange_d: float = B_FLANGE_TESTE) -> Manifold:
    rf, rb, ri, hf = flange_d / 2, od / 2, furo / 2, B_FLANGE_H
    topo = hf + B_CORPO_L
    peca = revolver([(ri + B_CH_FURO, 0), (rf, 0), (rf, hf), (rb, hf), (rb, topo - B_PONTA_H),
                     (rb - B_PONTA_R, topo), (ri, topo), (ri, B_CH_FURO)])
    if numero:   # número gravado na face superior do flange (anel entre o corpo e a borda), à frente (−Y)
        rc = (max(B_OD) / 2 + rf) / 2
        peca = peca - gravura(str(numero), hf - TEXTO_PROF, 4.5, 4.0, centro=(0.0, -rc))
    return peca


def para_trimesh(m: Manifold) -> trimesh.Trimesh:
    msh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(msh.vert_properties)[:, :3], np.asarray(msh.tri_verts), process=True)


def montar_pecas():
    """Peças do teste com posição (x, y) na mesa (centro do flange).
    Tampas: 2 fileiras × 5 (passo 38). Buchas: 2 fileiras × 4 (passo 35), à frente."""
    pecas = []
    gap, pc, pb = 10.0, 38.0, 35.0
    alt_b = pb + B_FLANGE_TESTE
    alt = (pc + T_FLANGE_D) + gap + alt_b
    y_base = CENTRO[1] - alt / 2
    y_b0 = y_base + B_FLANGE_TESTE / 2                       # fileira da frente das buchas
    y_t0 = y_base + alt_b + gap + T_FLANGE_D / 2             # fileira da frente das tampas
    for i, d in enumerate(T_PINOS):
        r, c = divmod(i, 5)
        pecas.append(dict(nome=f"TAMPA_{i + 1:02d}_P{d:.2f}", tipo="tampa", n=i + 1, d_pino=d,
                          mesh=para_trimesh(tampa(d, i + 1)),
                          pos=(CENTRO[0] + (c - 2) * pc, y_t0 + (1 - r) * pc)))
    for i, (od, fu) in enumerate(zip(B_OD, B_FURO)):
        r, c = divmod(i, 4)
        pecas.append(dict(nome=f"BUCHA_{i + 1}_OD{od:.2f}_F{fu:.2f}", tipo="bucha", n=i + 1, od=od, furo=fu,
                          mesh=para_trimesh(bucha(od, fu, i + 1)),
                          pos=(CENTRO[0] + (c - 1.5) * pb, y_b0 + (1 - r) * pb)))
    return pecas


# ─────────────────────────────────── Miniaturas ──────────────────────────────────────
def renderizar(pecas, w, h, modo="iso", cores=None, yaw=-32.0, pitch=48.0):
    """Renderização simples (painter's algorithm) para as miniaturas do projeto."""
    s = 2  # supersampling
    V, F, C = [], [], []
    off = 0
    for k, p in enumerate(pecas):
        v = p["mesh"].vertices + (*p["pos"], 0)
        V.append(v); F.append(p["mesh"].faces + off); off += len(v)
        C += [k] * len(p["mesh"].faces)
    V, F, C = np.vstack(V), np.vstack(F), np.array(C)
    cam = np.array([[0, 0, 0], [256, 0, 0], [256, 256, 0], [0, 256, 0]], dtype=float)
    ya, ph = np.radians(yaw), np.radians(pitch if modo == "iso" else 90.0)
    cx, cy = np.cos(ya), np.sin(ya)
    if modo != "iso":
        cx, cy = 1.0, 0.0
    Rz = np.array([[cx, -cy, 0], [cy, cx, 0], [0, 0, 1]])

    def proj(P):
        Q = (P - (128, 128, 0)) @ Rz.T
        return np.c_[Q[:, 0], Q[:, 2] * np.cos(ph) + Q[:, 1] * np.sin(ph),
                     Q[:, 1] * np.cos(ph) - Q[:, 2] * np.sin(ph)]
    pv, pcm = proj(V), proj(cam)
    xs = np.r_[pv[:, 0], pcm[:, 0]]; ys = np.r_[pv[:, 1], pcm[:, 1]]
    sc = min(w * s * 0.9 / (xs.max() - xs.min()), h * s * 0.9 / (ys.max() - ys.min()))
    ox, oy = (xs.max() + xs.min()) / 2, (ys.max() + ys.min()) / 2
    T = lambda q: np.c_[w * s / 2 + (q[:, 0] - ox) * sc, h * s / 2 - (q[:, 1] - oy) * sc]
    img = Image.new("RGBA", (w * s, h * s), (233, 236, 239, 255))
    dr = ImageDraw.Draw(img)
    dr.polygon([tuple(p) for p in T(pcm)], fill=(208, 213, 219, 255), outline=(150, 156, 164, 255))
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    nr = n @ Rz.T
    vis = np.array([0, -np.cos(ph), np.sin(ph)])
    front = nr @ vis > 0
    luz = np.array([-0.35, -0.55, 0.75]); luz /= np.linalg.norm(luz)
    lam = np.clip(nr @ luz, 0, 1)
    depth = pv[F][:, :, 2].mean(1)
    P2 = T(pv)
    zmax = V[:, 2].max()
    for i in np.argsort(-depth):
        if not front[i]:
            continue
        if cores is not None:
            col = cores[C[i] % len(cores)]
        else:
            g = int(34 + 150 * lam[i] + (28 * V[F[i]][:, 2].mean() / zmax if modo != "iso" else 0))
            col = (g, g, min(255, g + 6))
        dr.polygon([tuple(P2[j]) for j in F[i]], fill=col + (255,) if len(col) == 3 else col)
    return img.resize((w, h), Image.LANCZOS)


# ──────────────────────────────── Escrita do projeto .3mf ────────────────────────────
def _uuid(chave: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "tampas_haste_aco/" + chave))


def escrever_projeto(caminho: Path, pecas, titulo: str):
    with zipfile.ZipFile(BASE_3MF) as z:
        project_settings = z.read("Metadata/project_settings.config")

    ns = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
          'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
          'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
    arqs = {}
    res, build, cfg_obj, plate_inst, bbox_obj, rels_obj = [], [], [], [], [], []
    for i, p in enumerate(pecas, 1):
        m = p["mesh"]
        c = m.bounds.mean(0)                      # Bambu: malha centrada no centro da caixa
        v = m.vertices - c
        alt = m.bounds[1][2] - m.bounds[0][2]
        top_id, in_id = 2 * i, 2 * i - 1
        px, py = p["pos"]
        tx, ty, tz = px + c[0], py + c[1], c[2]
        x = [f'<?xml version="1.0" encoding="UTF-8"?>',
             f'<model unit="millimeter" xml:lang="en-US" {ns}>',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>', " <resources>",
             f'  <object id="{in_id}" p:UUID="{i:04x}0000-81cb-4c03-9d28-80fed5dfa1dc" type="model">',
             "   <mesh>", "    <vertices>"]
        x += [f'     <vertex x="{a:.6f}" y="{b:.6f}" z="{cc:.6f}"/>' for a, b, cc in v]
        x += ["    </vertices>", "    <triangles>"]
        x += [f'     <triangle v1="{a}" v2="{b}" v3="{cc}"/>' for a, b, cc in m.faces]
        x += ["    </triangles>", "   </mesh>", "  </object>", " </resources>", " <build/>", "</model>"]
        arqs[f"3D/Objects/object_{i}.model"] = "\n".join(x)
        rels_obj.append(f' <Relationship Target="/3D/Objects/object_{i}.model" Id="rel-{i}" '
                        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
        res.append(f'  <object id="{top_id}" p:UUID="{i:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                   f'   <components>\n    <component p:path="/3D/Objects/object_{i}.model" objectid="{in_id}" '
                   f'p:UUID="{i:04x}0000-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
                   '   </components>\n  </object>')
        build.append(f'  <item objectid="{top_id}" p:UUID="{i:08x}-b1ec-4553-aec9-835e5b724bb4" '
                     f'transform="1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}" printable="1"/>')
        nf = len(m.faces)
        cfg_obj.append(
            f'  <object id="{top_id}">\n'
            f'    <metadata key="name" value="{p["nome"]}"/>\n'
            '    <metadata key="extruder" value="1"/>\n'
            '    <metadata key="enable_support" value="0"/>\n'
            '    <metadata key="brim_type" value="no_brim"/>\n'
            '    <metadata key="ironing_type" value="no ironing"/>\n'
            f'    <metadata face_count="{nf}"/>\n'
            f'    <part id="{in_id}" subtype="normal_part" uuid="{_uuid("part" + str(i))}">\n'
            f'      <metadata key="name" value="{p["nome"]}"/>\n'
            '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
            '      <metadata key="source_object_id" value="0"/>\n'
            '      <metadata key="source_volume_id" value="0"/>\n'
            f'      <metadata key="source_offset_x" value="{c[0]:.6f}"/>\n'
            f'      <metadata key="source_offset_y" value="{c[1]:.6f}"/>\n'
            f'      <metadata key="source_offset_z" value="{c[2]:.6f}"/>\n'
            f'      <mesh_stat face_count="{nf}" edges_fixed="0" degenerate_facets="0" facets_removed="0" '
            'facets_reversed="0" backwards_edges="0"/>\n    </part>\n  </object>')
        plate_inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{top_id}"/>\n'
                          f'      <metadata key="instance_id" value="0"/>\n'
                          f'      <metadata key="identify_id" value="{100 + i}"/>\n    </model_instance>')
        lo, hi = m.bounds[0] + (px - 0, py - 0, 0), m.bounds[1] + (px - 0, py - 0, 0)
        bbox_obj.append({"area": float(m.area / 2), "bbox": [round(lo[0], 3), round(lo[1], 3), round(hi[0], 3), round(hi[1], 3)],
                         "id": 100 + i, "layer_height": 0.2, "name": p["nome"]})

    allx = [b["bbox"] for b in bbox_obj]
    bbox_all = [min(b[0] for b in allx), min(b[1] for b in allx), max(b[2] for b in allx), max(b[3] for b in allx)]
    descr = ("Tampas (pino) e buchas para as hastes de aço do rack de filamento - placa de TESTE v2, "
             f"gerada em {DATA}. Haste real: Ø ext 19,10 / Ø int 16,26. Furo do rack: 21,05.")
    arqs["3D/3dmodel.model"] = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>', f'<model unit="millimeter" xml:lang="en-US" {ns}>',
        ' <metadata name="Application">BambuStudio-02.09.01.70</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>', ' <metadata name="Copyright"></metadata>',
        f' <metadata name="CreationDate">{DATA}</metadata>', f' <metadata name="Description">{descr}</metadata>',
        f' <metadata name="ModificationDate">{DATA}</metadata>', f' <metadata name="Title">{titulo}</metadata>',
        " <resources>", *res, " </resources>", f' <build p:UUID="{_uuid("build")}">', *build, " </build>", "</model>"])
    arqs["3D/_rels/3dmodel.model.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.'
                                           'openxmlformats.org/package/2006/relationships">\n' + "\n".join(rels_obj)
                                           + "\n</Relationships>")
    arqs["Metadata/model_settings.config"] = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>', "<config>", *cfg_obj, "  <plate>",
        '    <metadata key="plater_id" value="1"/>',
        '    <metadata key="plater_name" value="TESTE v2 - tampas e buchas"/>',
        '    <metadata key="locked" value="false"/>',
        '    <metadata key="filament_map_mode" value="Auto For Flush"/>',
        '    <metadata key="filament_maps" value="1 1 1 1"/>',
        '    <metadata key="filament_volume_maps" value="0 0 0 0"/>',
        '    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>',
        '    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_1.png"/>',
        '    <metadata key="top_file" value="Metadata/top_1.png"/>',
        '    <metadata key="pick_file" value="Metadata/pick_1.png"/>', *plate_inst, "  </plate>", "</config>"])
    import json
    arqs["Metadata/plate_1.json"] = json.dumps({
        "bbox_all": bbox_all, "bbox_objects": bbox_obj, "bed_type": "textured_plate", "filament_colors": [],
        "filament_ids": [], "first_extruder": 0, "first_layer_time": 600.0, "is_seq_print": False,
        "nozzle_diameter": 0.4, "version": 2})
    arqs["Metadata/cut_information.xml"] = ('<?xml version="1.0" encoding="utf-8"?>\n<objects>\n' + "\n".join(
        f' <object id="{i}">\n  <cut_id id="0" check_sum="1" connectors_cnt="0"/>\n </object>'
        for i in range(1, len(pecas) + 1)) + "\n</objects>")
    arqs["Metadata/filament_sequence.json"] = '{"plate_1":{"nozzle_sequence":[],"optimal_assignment":[],"sequence":[]}}'
    arqs["Metadata/slice_info.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
                                          '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
                                          '    <header_item key="X-BBL-Client-Version" value="02.09.01.70"/>\n'
                                          '  </header>\n</config>')
    arqs["[Content_Types].xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/'
                                   'package/2006/content-types">\n <Default Extension="rels" ContentType="application/'
                                   'vnd.openxmlformats-package.relationships+xml"/>\n <Default Extension="model" ContentType="'
                                   'application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n <Default Extension="png" '
                                   'ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>')
    arqs["_rels/.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/'
                           'package/2006/relationships">\n <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://'
                           'schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n <Relationship Target="/Auxiliaries/'
                           '.thumbnails/thumbnail_3mf.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/'
                           'relationships/metadata/thumbnail"/>\n <Relationship Target="/Auxiliaries/.thumbnails/'
                           'thumbnail_middle.png" Id="rel-4" Type="http://schemas.bambulab.com/package/2021/'
                           'cover-thumbnail-middle"/>\n <Relationship Target="/Auxiliaries/.thumbnails/thumbnail_small.png" '
                           'Id="rel-5" Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-small"/>\n</Relationships>')

    # miniaturas
    import io
    def png(img):
        b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()
    iso = renderizar(pecas, 512, 512, "iso")
    topo = renderizar(pecas, 512, 512, "top")
    paleta = [(40 + (37 * k) % 200, 60 + (91 * k) % 180, 80 + (53 * k) % 170) for k in range(len(pecas))]
    pick = renderizar(pecas, 512, 512, "top", cores=paleta)
    bin_ = {"Metadata/plate_1.png": png(iso), "Metadata/plate_no_light_1.png": png(iso),
            "Metadata/top_1.png": png(topo), "Metadata/pick_1.png": png(pick),
            "Metadata/plate_1_small.png": png(iso.resize((128, 128), Image.LANCZOS)),
            "Auxiliaries/.thumbnails/thumbnail_3mf.png": png(renderizar(pecas, 215, 240, "iso").convert("RGB")),
            "Auxiliaries/.thumbnails/thumbnail_middle.png": png(renderizar(pecas, 608, 680, "iso").convert("RGB")),
            "Auxiliaries/.thumbnails/thumbnail_small.png": png(renderizar(pecas, 168, 188, "iso").convert("RGB"))}
    iso.save(caminho.with_name(caminho.stem + "_3d.png"))

    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", arqs.pop("[Content_Types].xml"))
        z.writestr("_rels/.rels", arqs.pop("_rels/.rels"))
        for nome, conteudo in arqs.items():
            z.writestr(nome, conteudo)
        z.writestr("Metadata/project_settings.config", project_settings)
        for nome, b in bin_.items():
            z.writestr(nome, b)


# ───────────────────────────────────── Preview ───────────────────────────────────────
def preview(png: Path, pecas):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def corte(mesh, z):
        s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        return [] if s is None else s.discrete

    di, de = TUBO_DI / 2, TUBO_DE / 2
    topo = T_FLANGE_H + T_PINO_L + T_PONTA_H
    hf, L = B_FLANGE_H, B_FLANGE_H + B_CORPO_L
    fig = plt.figure(figsize=(18, 11.5), dpi=105)
    gs = fig.add_gridspec(3, 3, height_ratios=[1.25, 1, 0.9], width_ratios=[1.5, 1, 1])

    ax = fig.add_subplot(gs[0, :2])                                     # layout da placa
    for p in pecas:
        x0, y0 = p["pos"]
        fl = T_FLANGE_D if p["tipo"] == "tampa" else B_FLANGE_TESTE
        for seg in corte(p["mesh"], 1.0 if p["tipo"] == "tampa" else 0.75):
            ax.plot(seg[:, 0] + x0, seg[:, 1] + y0, color="#9aa0a6", lw=0.9)
        for seg in corte(p["mesh"], 12.0 if p["tipo"] == "tampa" else 6.0):
            ax.plot(seg[:, 0] + x0, seg[:, 1] + y0, color="#1a73e8", lw=1.3)
        for seg in corte(p["mesh"], (T_FLANGE_H if p["tipo"] == "tampa" else hf) - 0.2):
            r = np.hypot(seg[:, 0], seg[:, 1])
            # laços dos dígitos: dentro do flange (exclui o disco externo) e, na bucha, fora do furo central
            if r.max() < fl / 2 - 0.3 and (p["tipo"] == "tampa" or r.min() > 10.5):
                ax.plot(seg[:, 0] + x0, seg[:, 1] + y0, color="k", lw=0.8)
        ax.text(x0, y0 - fl / 2 - 1.0, f"{'T' if p['tipo'] == 'tampa' else 'B'}{p['n']}", ha="center", va="top",
                fontsize=9, weight="bold", color="#555")
    ax.add_patch(plt.Rectangle((0, 0), 256, 256, fill=False, ec="#34a853", ls="--"))
    ax.set_xlim(8, 248); ax.set_ylim(45, 211); ax.set_aspect("equal")
    ax.set_title("Placa de teste v2 — vista de cima · T = tampas (nº 1–10) · B = buchas (nº 1–8) · mesa A1 256×256")

    ax = fig.add_subplot(gs[0, 2])                                      # tampa: corte + haste
    ax.add_patch(plt.Rectangle((di, T_FLANGE_H), de - di, 21, fc="#c0c4c8", ec="#555", hatch="///", label="parede da haste"))
    for d, ls, cor in ((T_PINOS[0], ":", "#d93025"), (T_PINOS[len(T_PINOS) // 2], "-", "#1a73e8"), (T_PINOS[-1], "--", "#e37400")):
        rp, rf, h = d / 2, T_FLANGE_D / 2, T_FLANGE_H
        pts = [(0, 0), (rf - T_CH_R, 0), (rf, T_CH_H), (rf, h), (rp, h), (rp, h + T_PINO_L), (rp - T_PONTA_R, topo), (0, topo)]
        ax.plot(*zip(*pts), ls=ls, color=cor, lw=1.5, label=f"pino Ø {d:.2f}")
    ax.set_xlim(-1, 19); ax.set_ylim(-1, 29); ax.set_aspect("equal"); ax.legend(fontsize=7, loc="upper right")
    ax.set_title("Tampa: meia-seção + haste (Ø int 16,26)", fontsize=10)

    rt = [p for p in pecas if p["tipo"] == "tampa"][6]                  # número gravado (tampa nº 7)
    rb_ = [p for p in pecas if p["tipo"] == "bucha"][2]                 # número gravado (bucha nº 3)
    for col, (pc, z, tit, lim) in enumerate(((rt, T_FLANGE_H - 0.2, "Tampa — número no flange (corte raso, de cima)", 19),
                                             (rb_, hf - 0.2, "Bucha (flange de teste Ø32) — número no flange", 17.5))):
        ax = fig.add_subplot(gs[1, col])
        for seg in corte(pc["mesh"], z):
            ax.plot(seg[:, 0], seg[:, 1], color="k", lw=1.0)
        ax.set_aspect("equal"); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_title(tit, fontsize=10)

    ax = fig.add_subplot(gs[1, 2])                                      # bucha: corte entre haste e rack
    ax.add_patch(plt.Rectangle((FURO_RACK / 2, hf), 6, 9, fc="#d7ccc8", ec="#555", hatch="\\\\\\", label=f"rack (furo {FURO_RACK:.2f})"))
    ax.add_patch(plt.Rectangle((TUBO_DE / 2 - 1.42, -1), 1.42, L + 3, fc="#c0c4c8", ec="#555", hatch="///", label=f"haste (Ø ext {TUBO_DE:.2f})"))
    for i, ls, cor in ((0, ":", "#d93025"), (3, "-", "#1a73e8"), (7, "--", "#e37400")):
        rb, ri, rf = B_OD[i] / 2, B_FURO[i] / 2, B_FLANGE_TESTE / 2
        pts = [(ri + B_CH_FURO, 0), (rf, 0), (rf, hf), (rb, hf), (rb, L - B_PONTA_H), (rb - B_PONTA_R, L), (ri, L), (ri, B_CH_FURO), (ri + B_CH_FURO, 0)]
        ax.plot(*zip(*pts), ls=ls, color=cor, lw=1.5, label=f"nº {i + 1}: OD {B_OD[i]:.2f} / furo {B_FURO[i]:.2f}")
    ax.set_xlim(7.5, 17); ax.set_ylim(-1, 12.5); ax.set_aspect("equal"); ax.legend(fontsize=7, loc="upper left")
    ax.set_title("Bucha: meia-seção entre haste e furo do rack", fontsize=10)

    ax = fig.add_subplot(gs[2, 0]); ax.axis("off")                      # tabela das tampas
    lin = [[i + 1, f"{d:.2f}", f"{TUBO_DI - d:+.2f}"] for i, d in enumerate(T_PINOS)]
    tb = ax.table(cellText=lin, colLabels=["nº", "Ø pino (modelo)", "folga nominal p/ haste Ø int 16,26"], loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.1); ax.set_title("TAMPAS — número → medida", fontsize=10)
    ax = fig.add_subplot(gs[2, 1:]); ax.axis("off")                     # tabela das buchas
    lin = [[i + 1, f"{o:.2f}", f"{f:.2f}", f"{(o - f) / 2:.3f}", f"{FURO_RACK - o:+.2f}", f"{f - TUBO_DE:+.2f}"]
           for i, (o, f) in enumerate(zip(B_OD, B_FURO))]
    tb = ax.table(cellText=lin, colLabels=["nº", "Ø externo do corpo", "Ø do furo", "parede", "folga p/ furo do rack 21,05", "folga p/ haste 19,10"],
                  loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.25); ax.set_title("BUCHAS — número → medida (modelo)", fontsize=10)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nome", default="TAMPAS_BUCHAS_HASTE_ACO_teste_v2")
    ap.add_argument("--saida", default=str(AQUI))
    ap.add_argument("--sem-preview", action="store_true")
    a = ap.parse_args()
    saida = Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    pecas = montar_pecas()
    escrever_projeto(saida / f"{a.nome}.3mf", pecas, a.nome)
    # alternativa universal (qualquer fatiador abre): a mesma placa em um STL único
    placa = trimesh.util.concatenate([p["mesh"].copy().apply_translation((*p["pos"], 0)) for p in pecas])
    placa.export(saida / f"{a.nome}_placa.stl")
    if not a.sem_preview:
        preview(saida / f"{a.nome}_preview.png", pecas)
    print(f"{len(pecas)} peças → {saida / a.nome}.3mf")


if __name__ == "__main__":
    main()
