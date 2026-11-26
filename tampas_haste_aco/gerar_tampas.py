#!/usr/bin/env python3
"""
Gerador paramétrico das tampas (plugs) que entram nas hastes de aço do suporte
de filamento.  Gera uma placa de TESTE com vários diâmetros de pino parecidos,
cada peça identificada (texto gravado), para descobrir qual encaixa melhor.

Saídas (na pasta --saida):
  <nome>.3mf          peças como objetos separados e nomeados (abrir no Bambu Studio)
  <nome>.stl          mesma placa em um único STL (alternativa)
  <nome>_preview.png  conferência visual (layout, perfil e textos)

Uso:
  python3 gerar_tampas.py                                  # placa de teste v1
  python3 gerar_tampas.py --tamanhos 16.15 --copias 24 --colunas 6 --sem-texto \
                          --nome TAMPA_HASTE_ACO_producao_v1   # lote final (24 un.)

Dependências: numpy, scipy, networkx, shapely, trimesh, manifold3d, matplotlib
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

# ──────────────────────── Medidas (paquímetro digital) ────────────────────────
TUBO_DE = 19.10   # Ø externo da haste de aço
TUBO_DI = 16.26   # Ø interno da haste de aço (parede ≈ 1,42 mm)

# ──────────────────────────── Geometria da tampa ─────────────────────────────
FLANGE_D = 22.0        # Ø do flange (cobre o topo da haste: 19,10 + ~1,45 por lado)
FLANGE_H = 2.0         # espessura do flange
FLANGE_CH_BASE = 0.4   # chanfro na base do flange (compensa "pé de elefante")
FLANGE_CH_TOPO = 0.3   # chanfro na borda superior do flange
PINO_L = 10.0          # comprimento do pino (profundidade de inserção)
PINO_CH = 0.8          # chanfro 45° na ponta do pino (guia de entrada)
TEXTO_PROF = 0.4       # profundidade da gravação do texto (2 camadas de 0,2 mm)
SEGMENTOS = 360        # facetas do círculo (erro de diâmetro < 0,001 mm)

# ───────────────────────────── Placa (Bambu Lab A1) ──────────────────────────
CENTRO_MESA = (128.0, 128.0)   # centro da mesa 256 × 256 mm
PASSO = 27.0                   # distância entre centros das peças

TAMANHOS_PADRAO = [round(15.95 + 0.05 * i, 2) for i in range(10)]  # 15,95 … 16,40


# ─────────────────────────────── Modelagem ───────────────────────────────────
def corpo(d_pino: float) -> Manifold:
    """Sólido de revolução: flange na base (z=0) e pino para cima (eixo Z)."""
    rf, rp = FLANGE_D / 2, d_pino / 2
    h, l = FLANGE_H, PINO_L
    pts = np.array([
        (0.0, 0.0),
        (rf - FLANGE_CH_BASE, 0.0),
        (rf, FLANGE_CH_BASE),
        (rf, h - FLANGE_CH_TOPO),
        (rf - FLANGE_CH_TOPO, h),
        (rp, h),
        (rp, h + l - PINO_CH),
        (rp - PINO_CH, h + l),
        (0.0, h + l),
    ])
    return Manifold.revolve(CrossSection([pts]), SEGMENTOS)


def poligonos_texto(txt: str, larg_max: float, alt_max: float, espelhar: bool):
    """Contornos do texto (DejaVu Sans Bold) centralizados e ajustados ao espaço."""
    fonte = FontProperties(family="DejaVu Sans", weight="bold")
    polys = TextPath((0, 0), txt, size=100, prop=fonte).to_polygons()
    todos = np.vstack(polys)
    (x0, y0), (x1, y1) = todos.min(0), todos.max(0)
    s = min(larg_max / (x1 - x0), alt_max / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    saida = []
    for p in polys:
        q = (p - (cx, cy)) * s
        if espelhar:
            q[:, 0] *= -1
        saida.append(q)
    return saida


def gravura(txt: str, z0: float, altura: float, larg_max: float, alt_max: float,
            espelhar: bool) -> Manifold:
    cs = CrossSection(poligonos_texto(txt, larg_max, alt_max, espelhar), FillRule.EvenOdd)
    return Manifold.extrude(cs, altura).translate((0, 0, z0))


def tampa(d_pino: float, com_texto: bool = True) -> Manifold:
    peca = corpo(d_pino)
    if com_texto:
        rotulo = f"{d_pino:.2f}"
        topo = FLANGE_H + PINO_L
        # Ponta do pino (face plana, impressa por último → gravação nítida)
        peca = peca - gravura(rotulo, topo - TEXTO_PROF, TEXTO_PROF + 0.5, 12.0, 4.0, False)
        # Face externa do flange (a que fica na mesa; espelhado para ler por baixo)
        peca = peca - gravura(rotulo, -0.5, TEXTO_PROF + 0.5, 16.0, 5.0, True)
    return peca


def para_trimesh(m: Manifold) -> trimesh.Trimesh:
    msh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(msh.vert_properties)[:, :3],
                           np.asarray(msh.tri_verts), process=True)


# ───────────────────────────────── Saídas ────────────────────────────────────
def salvar_3mf(caminho: Path, objetos, titulo: str) -> None:
    """3MF padrão (mm): um <object> por peça + <item> com a posição na mesa."""
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<model unit="millimeter" xml:lang="pt-BR" xmlns="{ns}">',
         f'<metadata name="Title">{titulo}</metadata>',
         '<metadata name="Application">gerar_tampas.py</metadata>',
         "<resources>"]
    for i, (nome, mesh, _) in enumerate(objetos, 1):
        x.append(f'<object id="{i}" name="{nome}" type="model"><mesh><vertices>')
        x += [f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in mesh.vertices]
        x.append("</vertices><triangles>")
        x += [f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in mesh.faces]
        x.append("</triangles></mesh></object>")
    x.append("</resources><build>")
    for i, (_, _, (px, py)) in enumerate(objetos, 1):
        x.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {px:.4f} {py:.4f} 0"/>')
    x.append("</build></model>")
    tipos = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
             'package/2006/content-types"><Default Extension="rels" ContentType="application/'
             'vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" '
             'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.'
            'org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(x))


def posicoes(n: int, colunas: int):
    """Grade centralizada na mesa; 1ª linha no fundo (Y alto) → lê-se de cima p/ baixo."""
    linhas = -(-n // colunas)
    pos = []
    for k in range(n):
        r, c = divmod(k, colunas)
        px = CENTRO_MESA[0] + (c - (colunas - 1) / 2) * PASSO
        py = CENTRO_MESA[1] + ((linhas - 1) / 2 - r) * PASSO
        pos.append((px, py))
    return pos


def preview(png: Path, objetos, tamanhos) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def contornos(mesh, z):
        sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        return [] if sec is None else sec.discrete

    fig = plt.figure(figsize=(17, 9.5), dpi=110)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.7, 1, 1], height_ratios=[1, 1])
    topo = FLANGE_H + PINO_L

    # A) Layout da placa (vista de cima) — contornos reais cortados da malha
    ax = fig.add_subplot(gs[:, 0])
    for (nome, mesh, (px, py)), d in zip(objetos, tamanhos):
        for z, cor, lw in ((1.0, "#9aa0a6", 1.0), (6.0, "#1a73e8", 1.4)):
            for seg in contornos(mesh, z):
                ax.plot(seg[:, 0] + px, seg[:, 1] + py, color=cor, lw=lw)
        ax.text(px, py - FLANGE_D / 2 - 1.6, f"Ø {d:.2f}", ha="center", va="top", fontsize=10,
                weight="bold")
    ax.add_patch(plt.Rectangle((0, 0), 256, 256, fill=False, ec="#34a853", ls="--"))
    ax.set_xlim(CENTRO_MESA[0] - 85, CENTRO_MESA[0] + 85)
    ax.set_ylim(CENTRO_MESA[1] - 40, CENTRO_MESA[1] + 40)
    ax.set_aspect("equal")
    ax.set_title("Placa de teste — vista de cima (cinza = flange Ø%.0f · azul = pino)" % FLANGE_D)
    ax.set_xlabel("X (mm) — mesa A1 256 × 256, centro em 128,128")
    ax.set_ylabel("Y (mm)")

    # B) Perfil em corte com a haste de aço
    ax = fig.add_subplot(gs[0, 1:])
    di, de = TUBO_DI / 2, TUBO_DE / 2
    # A haste assenta sobre o flange (z = FLANGE_H) e envolve o pino
    ax.add_patch(plt.Rectangle((di, FLANGE_H), de - di, 13, fc="#c0c4c8", ec="#555",
                               hatch="///", label="parede da haste de aço"))
    for d, ls, cor in ((min(tamanhos), ":", "#d93025"), (tamanhos[len(tamanhos) // 2], "-", "#1a73e8"),
                       (max(tamanhos), "--", "#e37400")):
        rp, h = d / 2, FLANGE_H
        rf = FLANGE_D / 2
        perf = [(0, 0), (rf - FLANGE_CH_BASE, 0), (rf, FLANGE_CH_BASE), (rf, h - FLANGE_CH_TOPO),
                (rf - FLANGE_CH_TOPO, h), (rp, h), (rp, topo - PINO_CH), (rp - PINO_CH, topo), (0, topo)]
        px_, py_ = zip(*perf)
        ax.plot(px_, py_, ls=ls, color=cor, lw=1.6, label=f"pino Ø {d:.2f}")
    ax.text(de + 0.5, FLANGE_H + 9,
            f"haste: Ø ext {TUBO_DE:.2f}\nØ int {TUBO_DI:.2f}\nparede {(TUBO_DE - TUBO_DI) / 2:.2f}",
            fontsize=8, va="center")
    ax.text(FLANGE_D / 2 + 0.3, FLANGE_H / 2, f"flange Ø{FLANGE_D:.0f} × {FLANGE_H:.1f}", fontsize=8)
    ax.text(1, topo / 2 + FLANGE_H / 2, f"pino {PINO_L:.0f} mm\nchanfro {PINO_CH} × 45°", fontsize=8)
    ax.set_xlim(-1, FLANGE_D / 2 + 9)
    ax.set_ylim(-1.5, FLANGE_H + 14)
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Meia-seção (raio × altura, mm) — imprime com o flange na mesa, pino para cima")

    # C/D) Gravações (corte raso) para conferir legibilidade e sentido de leitura
    ref = objetos[len(objetos) // 2]
    for col, (z, titulo, inverter) in enumerate((
            (topo - 0.2, "Ponta do pino (vista de cima)", False),
            (0.2, "Face externa do flange (vista de baixo)", True))):
        ax = fig.add_subplot(gs[1, 1 + col])
        for seg in contornos(ref[1], z):
            ax.plot(seg[:, 0], seg[:, 1], color="k", lw=1.2)
        ax.set_aspect("equal")
        ax.set_xlim((12, -12) if inverter else (-12, 12))
        ax.set_ylim(-12, 12)
        ax.set_title(titulo, fontsize=10)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tamanhos", default=",".join(f"{t:.2f}" for t in TAMANHOS_PADRAO),
                    help="Ø do pino em mm, separados por vírgula")
    ap.add_argument("--copias", type=int, default=1, help="cópias de cada tamanho")
    ap.add_argument("--colunas", type=int, default=5)
    ap.add_argument("--sem-texto", action="store_true", help="não grava os rótulos (lote final)")
    ap.add_argument("--nome", default="TAMPA_HASTE_ACO_teste_v1")
    ap.add_argument("--saida", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--sem-preview", action="store_true")
    a = ap.parse_args()

    tamanhos = [float(t) for t in a.tamanhos.split(",")]
    lista = [d for d in tamanhos for _ in range(a.copias)]
    pos = posicoes(len(lista), a.colunas)
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)

    cache, objetos, contagem = {}, [], {}
    for d, p in zip(lista, pos):
        if d not in cache:
            cache[d] = para_trimesh(tampa(d, not a.sem_texto))
        contagem[d] = contagem.get(d, 0) + 1
        sufixo = f"_{contagem[d]:02d}" if a.copias > 1 else ""
        objetos.append((f"TAMPA_D{d:.2f}{sufixo}", cache[d], p))

    salvar_3mf(saida / f"{a.nome}.3mf", objetos, a.nome)
    placa = trimesh.util.concatenate([m.copy().apply_translation((*p, 0)) for _, m, p in objetos])
    placa.export(saida / f"{a.nome}.stl")
    if not a.sem_preview:
        preview(saida / f"{a.nome}_preview.png", objetos, [d for d in lista])
    print(f"{len(objetos)} peças → {saida / a.nome}.3mf / .stl")


if __name__ == "__main__":
    main()
