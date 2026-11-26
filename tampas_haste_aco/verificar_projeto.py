#!/usr/bin/env python3
"""
Verifica o projeto .3mf gerado por gerar_projeto.py, lendo o arquivo "do zero":
estrutura do pacote, consistência de ids/arquivos, malhas fechadas, diâmetros medidos
na malha (cortes) contra o nominal, colisões entre peças e limites da mesa.

Uso: python3 verificar_projeto.py TAMPAS_BUCHAS_HASTE_ACO_teste_v2.3mf
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh
from shapely.geometry import Polygon

NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
      "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
ok = True
LACOS = {"0": 2, "1": 1, "2": 1, "3": 1, "4": 2, "5": 1, "6": 2, "7": 1, "8": 3, "9": 2}   # contornos por dígito


def check(cond, msg):
    global ok
    ok &= bool(cond)
    print(("  OK   " if cond else "  FALHA ") + msg)


def malha(root):
    o = root.find("m:resources", NS).find("m:object", NS)
    me = o.find("m:mesh", NS)
    v = np.array([[float(x.get(k)) for k in "xyz"] for x in me.find("m:vertices", NS)])
    t = np.array([[int(x.get(k)) for k in ("v1", "v2", "v3")] for x in me.find("m:triangles", NS)])
    return o.get("id"), trimesh.Trimesh(v, t, process=False)


def diam_corte(m, z, interno=None):
    """Ø equivalente (pela área) dos contornos do corte em z: devolve [(Ø externo, [Ø furos])]."""
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, _ = sec.to_2D()
    res = []
    for pg in p2.polygons_full:
        de = 2 * np.sqrt(Polygon(pg.exterior).area / np.pi)
        fu = [2 * np.sqrt(Polygon(r).area / np.pi) for r in pg.interiors]
        res.append((de, fu))
    return res


def main(caminho):
    z = zipfile.ZipFile(caminho)
    nomes = set(z.namelist())
    print("== pacote")
    for obrig in ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model", "Metadata/model_settings.config",
                  "Metadata/project_settings.config", "Metadata/plate_1.png"):
        check(obrig in nomes, f"contém {obrig}")
    for n in nomes:
        if n.endswith((".xml", ".model", ".rels", ".config")) and n != "Metadata/project_settings.config":
            ET.fromstring(z.read(n))                       # XML bem formado
    import json
    ps = json.loads(z.read("Metadata/project_settings.config"))
    check(ps.get("printer_settings_id") == "Bambu Lab A1 0.4 nozzle", f"perfil de impressora: {ps.get('printer_settings_id')}")
    check(z.read("3D/3dmodel.model").decode().count("BambuStudio-02.09.01.70") == 1, "Application = BambuStudio-02.09.01.70")

    root = ET.fromstring(z.read("3D/3dmodel.model"))
    topo = root.find("m:resources", NS).findall("m:object", NS)
    itens = {i.get("objectid"): i for i in root.find("m:build", NS).findall("m:item", NS)}
    cfg = ET.fromstring(z.read("Metadata/model_settings.config"))
    nome_cfg = {o.get("id"): next(md.get("value") for md in o.findall("metadata") if md.get("key") == "name")
                for o in cfg.findall("object")}
    na_placa = {mi.find("metadata[@key='object_id']").get("value") for mi in cfg.find("plate").findall("model_instance")}
    print(f"\n== {len(topo)} objetos no 3dmodel.model · {len(itens)} itens de build · {len(nome_cfg)} no model_settings · {len(na_placa)} na placa 1")
    check(len(topo) == len(itens) == len(nome_cfg) == len(na_placa), "contagens iguais")
    check(set(nome_cfg) == na_placa == {o.get("id") for o in topo}, "ids de objeto consistentes entre os 3 arquivos")

    pos, rows = {}, []
    for o in topo:
        oid = o.get("id")
        comp = o.find("m:components/m:component", NS)
        caminho_obj = comp.get("{%s}path" % NS["p"]).lstrip("/")
        assert caminho_obj in nomes, caminho_obj
        inner_id, m = malha(ET.fromstring(z.read(caminho_obj)))
        assert inner_id == comp.get("objectid"), (inner_id, comp.get("objectid"))
        T = np.array(itens[oid].get("transform").split(), float)
        t = T[9:12]
        m.apply_translation(t)                              # para coordenadas da mesa
        pos[oid] = (nome_cfg[oid], m)
    check(True, "todos os componentes existem e os ids internos batem")
    check(all(m.is_watertight for _, m in pos.values()), "todas as malhas fechadas (watertight)")
    check(all(m.is_winding_consistent and m.volume > 0 for _, m in pos.values()), "orientação das faces consistente, volume > 0")
    check(all(abs(m.bounds[0][2]) < 1e-4 for _, m in pos.values()), "todas as peças apoiadas em z = 0")
    b = np.array([m.bounds for _, m in pos.values()])
    check(b[:, 0, :2].min() >= 0 and b[:, 1, :2].max() <= 256, f"dentro da mesa 256×256 (X {b[:,0,0].min():.1f}…{b[:,1,0].max():.1f}, Y {b[:,0,1].min():.1f}…{b[:,1,1].max():.1f})")

    # colisão: distância mínima entre contornos em XY (círculos) ≥ 2 mm
    cent = {k: ((m.bounds[0] + m.bounds[1]) / 2)[:2] for k, (_, m) in pos.items()}
    raio = {k: max(m.extents[:2]) / 2 for k, (_, m) in pos.items()}
    folga = min(np.linalg.norm(cent[a] - cent[c]) - raio[a] - raio[c] for a in pos for c in pos if a < c)
    check(folga >= 2.0, f"menor distância entre peças (borda a borda) = {folga:.1f} mm")

    print("\n== Diâmetros medidos NA MALHA (nominal entre parênteses)")
    for k, (nome, m) in pos.items():
        m0 = m.copy(); m0.apply_translation(-np.array([*cent[k], 0]))
        if nome.startswith("TAMPA"):
            nom = float(re.search(r"P([\d.]+)", nome).group(1))
            (de, _), = [r for r in diam_corte(m0, 12.0) if r[0] > 5]
            fl = diam_corte(m0, 2.5)[0][0]            # acima do chanfro da base (0–1,6 mm)
            check(abs(de - nom) < 0.005 and abs(fl - 34.0) < 0.05,
                  f"{nome:<24} pino Ø {de:.3f} ({nom:.2f})  flange Ø {fl:.2f} (34,00)  h={m.extents[2]:.2f} (25,60)")
        else:
            od, fu = map(float, re.search(r"OD([\d.]+)_F([\d.]+)", nome).groups())
            (de, fo), = diam_corte(m0, 6.0)
            nn = int(re.search(r"BUCHA_(\d)", nome).group(1))
            fl = max(diam_corte(m0, 0.75), key=lambda r: r[0])[0]          # flange (contorno externo)
            lacos = m0.section(plane_origin=[0, 0, 1.3], plane_normal=[0, 0, 1]).discrete
            rr = [np.hypot(l[:, 0], l[:, 1]) for l in lacos]
            gl = [r for r in rr if r.min() > 10.5 and r.max() < 15.95]
            check(abs(de - od) < 0.005 and abs(fo[0] - fu) < 0.005 and abs(fl - 32.0) < 0.05 and len(gl) == LACOS[str(nn)]
                  and min(r.min() for r in gl) > od / 2 + 0.5 and max(r.max() for r in gl) < 15.6,
                  f"{nome:<24} corpo Ø {de:.3f} ({od:.2f})  furo Ø {fo[0]:.3f} ({fu:.2f})  parede {(de-fo[0])/2:.3f}  "
                  f"flange Ø {fl:.2f}  dígito '{nn}': {len(gl)} contornos (esp. {LACOS[str(nn)]}) em r={min(r.min() for r in gl):.1f}…{max(r.max() for r in gl):.1f}  h={m.extents[2]:.2f}")

    print("\n== número gravado na face superior do flange das tampas (corte raso em z = 2,9)")
    for k, (nome, m) in pos.items():
        if not nome.startswith("TAMPA"):
            continue
        nn = re.search(r"TAMPA_(\d+)_P", nome).group(1)
        rp = float(re.search(r"P([\d.]+)", nome).group(1)) / 2
        m0 = m.copy(); m0.apply_translation(-np.array([*cent[k], 0]))
        lacos = m0.section(plane_origin=[0, 0, 2.9], plane_normal=[0, 0, 1]).discrete
        glifos = [l for l in lacos if np.hypot(l[:, 0], l[:, 1]).max() < 17.0 - 0.05]
        esp = sum(LACOS[c] for c in str(int(nn)))
        rmin = min(np.hypot(l[:, 0], l[:, 1]).min() for l in glifos)
        rmax = max(np.hypot(l[:, 0], l[:, 1]).max() for l in glifos)
        ponta = len(m0.section(plane_origin=[0, 0, 25.4], plane_normal=[0, 0, 1]).discrete)
        mesa = len(m0.section(plane_origin=[0, 0, 0.2], plane_normal=[0, 0, 1]).discrete)
        check(len(glifos) == esp and rmin >= rp + 1.0 and rmax <= 17.0 - 1.0 and ponta == 1 and mesa == 1,
              f"{nome:<16} nº {int(nn):>2}: {len(glifos)} contornos (esperado {esp}) · r = {rmin:.1f}…{rmax:.1f} mm "
              f"(pino r={rp:.2f}, borda 17,0) · ponta lisa={ponta == 1} · face da mesa lisa={mesa == 1}")

    vol = sum(m.volume for _, m in pos.values())
    print(f"\nVolume sólido total: {vol/1000:.1f} cm³ → limite superior ≈ {vol/1000*1.27:.0f} g (PETG) / {vol/1000*1.24:.0f} g (PLA); com paredes+5% de preenchimento bem menos")
    print("\nRESULTADO:", "TUDO OK" if ok else "HÁ FALHAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
