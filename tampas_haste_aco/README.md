# Tampas e buchas das hastes de aço — placa de TESTE v2

Data de referência: 26/11/2026 · Impressora no projeto: Bambu Lab A1 0,4 mm (perfil copiado do projeto do dachshund)
Cada peça tem **só um número gravado**; a tabela número → medida está abaixo.

## O que aconteceu (projeto antigo × fotos)
| Item | Projeto antigo | Real (paquímetro) | Efeito |
|---|---|---|---|
| Haste, Ø externo | 18,08 | **19,10** (foto 2) | bucha com furo Ø 18,40 não deixa a haste entrar (−0,70 mm) |
| Haste, Ø interno | 14,45 | **16,26** (foto 3) | pino Ø 14,20 fica solto: folga de 1,03 mm por lado no modelo |
| Pino da tampa impresso | 14,20 (modelo) | 13,68 (foto 4) | impressão 0,52 mm menor que o modelo |
| Anel impresso (corpo da bucha) | 20,75 (modelo) | 20,45 (foto 1) | impressão 0,30 mm menor que o modelo |
| Furo do rack | 21,05 (nome do arquivo; modelo do rack = 21,32) | não aparece nas fotos | **confirmar com o paquímetro** |

Ø 19,10 é compatível com tubo de ¾" (19,05); o rack original é para conduíte EMT ½" (≈ 17,9). Com as duas medidas
de impressão subdimensionada (−0,3 e −0,5), a faixa da placa cobre de 0 a −0,6 mm.

## TAMPAS — número → Ø do pino (modelo)
Folga nominal = 16,26 − Ø. Flange Ø 34 × 3,1 e pino de 20,5 mm iguais ao projeto antigo; só o Ø do pino muda.

| nº | Ø pino | Folga nominal | Ø impresso medido | Entra? | Aperto (solta / justa / dura) | Segura? |
|---|---|---|---|---|---|---|
| 1 | 16,00 | +0,26 | | | | |
| 2 | 16,10 | +0,16 | | | | |
| 3 | 16,20 | +0,06 | | | | |
| 4 | 16,30 | −0,04 | | | | |
| 5 | 16,40 | −0,14 | | | | |
| 6 | 16,50 | −0,24 | | | | |
| 7 | 16,60 | −0,34 | | | | |
| 8 | 16,70 | −0,44 | | | | |
| 9 | 16,80 | −0,54 | | | | |
| 10 | 16,90 | −0,64 | | | | |

## BUCHAS — número → Ø externo do corpo / Ø do furo (modelo)
Os dois diâmetros sobem juntos (parede fixa de 0,825 mm), então cada peça testa o corpo no furo do rack **e** o furo na
haste; escolha o corpo de uma peça e o furo de outra, se for o caso. Flange de teste Ø 32 (só para caber o número);
na produção volta a 23,4. Corpo de 9 mm + flange de 1,5 mm, como no projeto antigo.

| nº | Ø corpo | Ø furo | Corpo impresso | Furo impresso | Entra no rack? | Haste passa? | Obs. |
|---|---|---|---|---|---|---|---|
| 1 | 20,65 | 19,00 | | | | | |
| 2 | 20,75 | 19,10 | | | | | |
| 3 | 20,85 | 19,20 | | | | | |
| 4 | 20,95 | 19,30 | | | | | |
| 5 | 21,05 | 19,40 | | | | | |
| 6 | 21,15 | 19,50 | | | | | |
| 7 | 21,25 | 19,60 | | | | | |
| 8 | 21,35 | 19,70 | | | | | |

## Quantidades (informadas em 26/11/2026)
- 24 tampas (6 hastes × 2 pontas × 2 móveis) e 24 buchas (2 móveis → 12 por móvel).
- Produção: placa 1 = 24 buchas (3 × 8); placas 2 a 5 = 6 tampas cada (como no projeto antigo).

## Resultado do teste (27/11/2026)
- **Bucha nº 6** (corpo 21,15 / furo 19,50) e **tampa nº 7** (pino 16,60): encaixe perfeito em 12 furos/pontas.
- Nas outras 12 pontas da haste há uma **aba de metal do corte de fábrica dobrada para dentro** (~2–3 mm, estimativa
  pelas fotos); nenhum pino passa por ela, independente do tamanho.
- A medir (peças impressas, paquímetro): Ø do pino da tampa 7 e Ø do furo da bucha 6 — mostra o desvio real da impressora.

## Pontas com aba: solução
1. **Rebarbar a ponta (recomendado, não precisa reimprimir):** afastar/arrancar a aba com alicate de bico fino ou chave de
   fenda, nivelar com lima redonda (meia-cana) ou escareador cônico 90° e quebrar a aresta interna ~0,5 mm; limpar a limalha;
   testar a tampa 7 (deve entrar sem forçar). Luvas e óculos — a aba corta.
2. **Plano B (se não for viável rebarbar):** tampa externa (luva) que cobre a ponta por fora, com o mesmo furo Ø 19,50 da
   bucha nº 6 — não depende do interior da haste. Exige novo modelo e um teste curto.

## Como testar (placa de teste)
1. Abrir `TAMPAS_BUCHAS_HASTE_ACO_teste_v2.3mf` no Bambu Studio e imprimir com o **mesmo filamento** do lote final
   (o projeto vem com o filamento 1 do projeto do dachshund — troque pelo seu).
2. Medir cada peça impressa com o paquímetro (colunas "impresso") — isso mostra quanto a impressora desvia do modelo.
3. Tampas na haste; buchas no furo do rack e depois a haste dentro da bucha. Anotar na tabela.
4. Passar os números escolhidos (tampa e bucha) e as quantidades; as placas de produção saem desses números.

## Premissas e pontos a confirmar
- Impressora A1 e perfil do projeto do dachshund (3 paredes, 0,20 mm). Por objeto: sem suporte, sem brim, sem ironing.
- Furo real do rack = 21,05 vem do nome do arquivo antigo, não das fotos.
- Chanfros novos na bucha: 0,5 mm na entrada da haste e 0,3 × 0,6 mm na ponta do corpo.
- A parede de 0,825 mm da bucha fatia em duas linhas de ~0,43 mm (conferido no PrusaSlicer).
- Não foi aberto no Bambu Studio: estrutura copiada dos seus 3MF e geometria fatiada no PrusaSlicer
  (~55 g no total: tampas ≈ 42 g, buchas ≈ 13 g). Tempo real: ver no Studio.
- Se o `.3mf` não abrir, usar o `_placa.stl`.

## Arquivos
- `TAMPAS_BUCHAS_HASTE_ACO_teste_v2.3mf` — projeto completo, 1 placa, 18 objetos nomeados (`TAMPA_01_P16.00`, `BUCHA_1_OD20.65_F19.00`…)
- `TAMPAS_BUCHAS_HASTE_ACO_producao_v1.3mf` — **produção**: tampa nº 7 × 24 + bucha nº 6 × 24, 5 placas, sem números
  (`python3 gerar_projeto.py --producao --tampa 7 --bucha 6`). ≈ 124 g no total (PrusaSlicer, 3 paredes, 5 % de preenchimento).
  Posições das placas 2–5 seguem o que se sabe do formato do Bambu Studio (não testado no Studio): se as peças
  aparecerem fora da placa, usar "Arrange all" (A) ou abrir placa por placa.
- `TAMPAS_BUCHAS_HASTE_ACO_teste_v2_placa.stl` — mesma placa em um único STL
- `TAMPAS_BUCHAS_HASTE_ACO_teste_v2_preview.png` / `_3d.png` — conferência visual
- `gerar_projeto.py` (gerador) · `verificar_projeto.py` (confere o .3mf: malhas, diâmetros, números gravados)
- `projeto_original/` — tampas e buchas antigas · `v1_obsoleto/` — primeira tentativa (já substituída)
