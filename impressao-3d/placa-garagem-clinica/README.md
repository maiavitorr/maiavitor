# Placa da garagem da clínica — Entrada de ambulâncias / Proibido estacionar

**Data de referência:** 26/11/2026 · **Status:** proposta v1 (modelo gerado e verificado geometricamente; **ainda não fatiado nem impresso**)

## O que é

Placa amarela de alerta em **2 módulos quadrados de 210 × 210 mm**, cada um impresso à parte e montado lado a lado ou empilhado.

| Módulo | Conteúdo |
|---|---|
| 1 | **GARAGEM** · ícone de ambulância com cruz vermelha · **ENTRADA DE AMBULÂNCIAS** |
| 2 | Símbolo de proibido estacionar (letra **E** cortada por tarja vermelha) · **PROIBIDO ESTACIONAR** |

Pré-visualizações: `preview/placa_lado_a_lado.png` (424 × 210 mm) e `preview/placa_empilhada.png` (210 × 424 mm).

## Por que 2 módulos

A área de impressão da X2D é de **256 × 256 × 260 mm** (bico único) e **235,5 × 256 × 256 mm** com os dois bicos. Uma peça única não passaria de ~235 mm. Com 210 mm sobram ~46 mm no eixo Y (~25 mm no X com dois bicos) para brim/torre de limpeza.

Fontes (consultadas em 26/11/2026; há divergência de 256 vs. 260 mm na altura entre fontes, irrelevante aqui):
[ficha técnica Bambu Lab X2D](https://www.solidprint3d.co.uk/wp-content/uploads/2026/04/Bambu-Lab-X2D-3d-printer-specification.pdf) ·
[engineering.com](https://www.engineering.com/?p=147752) · [All3DP](https://all3dp.com/4/bambu-lab-x2d/)

## Decisões assumidas (confirmar)

| Item | Assumido | Observação |
|---|---|---|
| Tamanho final | 424 × 210 mm (ou 210 × 424 mm) | **Não consegui medir o local pela foto.** Meça o espaço livre e me diga largura × altura. |
| Idioma/texto | GARAGEM · ENTRADA DE AMBULÂNCIAS · PROIBIDO ESTACIONAR | Nenhum texto extra além do pedido. |
| Símbolo | "E" de Estacionar com tarja vermelha | Troca por "P" é trivial no script. |
| Cores | amarelo (chapa), preto (moldura/texto/ícone), vermelho (símbolo/cruz) | Versão 2 cores: atribuir o filamento preto também à parte "vermelho". |
| Espessura | chapa 3,0 mm + relevo 1,6 mm = **4,6 mm** | 15 + 8 camadas de 0,2 mm. |
| Fixação | 4 furos Ø 5,0 mm nos cantos, dentro da moldura preta | Parafuso até 4,5 mm + arruela + bucha. |

## Arquivos

```
gerar_placa.py                      gerador paramétrico (textos, medidas, espessuras no topo do arquivo)
stl/<modulo>_{amarelo,preto,vermelho}.stl   1 STL por cor (alinhados na mesma origem)
3mf/<modulo>.3mf                    objeto único com as 3 partes nomeadas por cor
preview/                            imagens
```

## Como imprimir (Bambu Studio)

1. **Importar o módulo.**
   - *Opção A:* abrir `3mf/<modulo>.3mf` (1 objeto, 3 partes). **Não testei esse 3MF no Bambu Studio**; se aparecer como 3 objetos soltos ou fora da mesa, use a opção B.
   - *Opção B (padrão):* importar os 3 STL do módulo de uma vez e responder **Sim** a "carregar como um único objeto com várias partes".
2. **Atribuir filamentos às partes:** `amarelo` → amarelo · `preto` → preto · `vermelho` → vermelho.
3. **Orientação:** face para cima, como veio. **Sem suportes.**
4. As camadas 1–15 (chapa) são só amarelas; as trocas de cor ocorrem apenas nas 8 camadas de relevo (preto/vermelho). Se o fatiador deixar, prefira preto e vermelho em bicos diferentes para reduzir purga.
5. Deixe espaço para a torre de limpeza (ver margem acima) e confira o tempo e o peso no fatiador — **não tenho o Bambu Studio aqui, então não estimei tempo.**

### Sugestões de ajuste (a validar na primeira peça)

- **Material:** **ASA** (resiste a sol/calor) ou **PETG**. Evitar PLA em área externa: amolece com calor e sol.
- Bico 0,4 mm · camada 0,2 mm · 3 paredes · topo/base ≥ 5/4 camadas · preenchimento 15%.
- **Brim** de ~5–8 mm e porta fechada: chapas planas grandes de ASA tendem a empenar.
- Massa máxima por módulo (100% maciço, ASA ≈ 1,07 g/cm³; o fatiador dará o valor real, e há purga/torre além disso):

| Módulo | Amarelo | Preto | Vermelho |
|---|---|---|---|
| 1 | ~141 g | ~29 g | ~0,6 g |
| 2 | ~141 g | ~20 g | ~6,5 g |

## Fixação

Os furos de Ø 5,0 mm ficam nos 4 cantos de cada módulo (centro a 8,5 mm das bordas). Deixe ~4 mm entre módulos. O pilar verde da foto *parece* ser painel de alumínio composto: confirme o material antes de furar; fita dupla-face estrutural é alternativa a parafusos.

## Verificações feitas

- Todos os 6 corpos são fechados (watertight); preto e vermelho não se sobrepõem (0,000 mm²).
- Furos livres nas duas camadas; detalhes mais finos que 1,2 mm representam ~0,15% da área do relevo (pontas de letras).
- Os 3MF foram relidos e conferem: 210 × 210 × 4,6 mm.

## Pendências

- [ ] Medir o local e escolher arranjo (lado a lado ou empilhado) e tamanho final.
- [ ] Confirmar filamentos disponíveis (ASA/PETG amarelo, preto, vermelho).
- [ ] Imprimir 1 módulo de teste (ou só o canto/trecho) antes de imprimir os dois.
- [ ] Decidir fixação (parafuso × fita).

## Regerar

```
pip install numpy shapely trimesh mapbox_earcut matplotlib networkx
python3 gerar_placa.py
```
