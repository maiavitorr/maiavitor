# Tampas das hastes de aço — suporte de filamento

Data de referência: 26/11/2026 · Versão: teste v1 · Impressora: Bambu Lab A1 (bico 0,4 mm)

## Objetivo
24 tampas (6 hastes × 2 pontas × 2 suportes) que entram na haste de aço. A primeira
versão não encaixou direito; esta placa testa 10 diâmetros de pino parecidos para achar o ajuste.

## Medidas (paquímetro digital, lidas das fotos de 26/11/2026)
| Peça | Medida | Observação |
|---|---|---|
| Haste de aço — Ø externo | 19,10 mm | foto 2 |
| Haste de aço — Ø interno | **16,26 mm** | foto 3 (referência do ajuste); parede ≈ 1,42 mm |
| Tampa antiga — Ø do pino | 13,68 mm | foto 4 (≈ 2,6 mm menor que o furo da haste) |
| Anel impresso | 20,45 mm | foto 1 — função não confirmada, **não usado no modelo** |

## Geometria da tampa (parametrizada em `gerar_tampas.py`)
- Flange Ø 22,0 × 2,0 mm (cobre o topo da haste Ø 19,10), chanfro 0,4 na base (pé de elefante) e 0,3 na borda.
- Pino de 10 mm com chanfro de 0,8 × 45° na ponta (guia de entrada).
- Imprime **com o flange na mesa e o pino para cima**, sem suporte.
- Rótulo do Ø gravado (0,4 mm) na ponta do pino e na face externa do flange.

## Placa de teste v1 — `TAMPA_HASTE_ACO_teste_v1.3mf`
Folga nominal = 16,26 − Ø do pino (negativa = interferência). Fileira de trás: 15,95 → 16,15; fileira da frente: 16,20 → 16,40.

| # | Ø pino (mm) | Folga nominal (mm) | Entra? | Aperto (solta / justa / dura) | Segura? | Observações |
|---|---|---|---|---|---|---|
| 1 | 15,95 | +0,31 | | | | |
| 2 | 16,00 | +0,26 | | | | |
| 3 | 16,05 | +0,21 | | | | |
| 4 | 16,10 | +0,16 | | | | |
| 5 | 16,15 | +0,11 | | | | |
| 6 | 16,20 | +0,06 | | | | |
| 7 | 16,25 | +0,01 | | | | |
| 8 | 16,30 | −0,04 | | | | |
| 9 | 16,35 | −0,09 | | | | |
| 10 | 16,40 | −0,14 | | | | |

**Resultado do teste:** _(preencher: Ø escolhido e data)_

## Sugestão de impressão (ajustar ao seu perfil)
PETG, camada 0,20 mm, 3 paredes, preenchimento ~15 %, sem suporte, sem brim. Costura (seam) alinhada
ou scarf para não criar calombo no pino. Peças pequenas e distantes — o fatiador mostra o tempo real.

## Próximo passo — lote de 24
Depois de escolher o Ø:

```bash
python3 gerar_tampas.py --tamanhos 16.15 --copias 24 --colunas 6 --sem-texto \
        --nome TAMPA_HASTE_ACO_producao_v1
```
(troque `16.15` pelo Ø vencedor). Se nenhum ficar bom, informe o que sentiu (tudo solto / tudo duro)
que eu desloco a faixa de tamanhos — ou mudo o desenho (nervuras de crush, pino mais curto etc.).

## Arquivos
- `TAMPA_HASTE_ACO_teste_v1.3mf` — 10 objetos nomeados (`TAMPA_D16.10` …) já posicionados na mesa 256 × 256
- `TAMPA_HASTE_ACO_teste_v1.stl` — mesma placa em um único STL (alternativa)
- `TAMPA_HASTE_ACO_teste_v1_preview.png` — conferência visual
- `gerar_tampas.py` — gerador paramétrico (numpy, scipy, networkx, shapely, trimesh, manifold3d, matplotlib)
