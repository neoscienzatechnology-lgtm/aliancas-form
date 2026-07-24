# Kit de captura — placa de calibração FootScan

Este documento especifica o kit físico usado nas capturas 2D calibradas e o
protocolo de posicionamento do pé e do celular. Seguir esta especificação é
condição para atingir a meta de erro linear ≤ 3 mm
(ver [protocolo-validacao.md](protocolo-validacao.md)).

## 1. Especificação física da placa

### Base

- **Material:** acrílico ou vidro **transparente ou branco fosco**, espessura
  **≥ 6 mm** (rigidez suficiente para não flexionar com o peso do paciente).
- **Dimensões externas:** aproximadamente **300 × 450 mm** (largura × altura).
- **Superfície:** plana, sem relevo; bordas lixadas/protegidas para segurança.
- A placa deve apoiar em piso plano e firme, sem balanço.

### Marcadores ArUco

- Dicionário: **ArUco DICT_4X4_50**, IDs **0, 1, 2 e 3**.
- Lado de cada marcador (área preta): **40 mm**.
- Posições (sentido horário, vistos por quem olha a placa de cima, com a altura
  na vertical):

| ID | Canto |
|---|---|
| 0 | superior-esquerdo |
| 1 | superior-direito |
| 2 | inferior-direito |
| 3 | inferior-esquerdo |

- Os **centros** dos 4 marcadores formam um retângulo de exatamente
  **250 mm (largura) × 380 mm (altura)**. São essas as constantes usadas pelo
  software (`PLATE_WIDTH_MM = 250.0`, `PLATE_HEIGHT_MM = 380.0`,
  `MARKER_SIZE_MM = 40.0`).
- **Área útil para o pé:** a região interna ao retângulo dos marcadores, sem
  sobrepor os próprios marcadores. Comporta pés de até ~300 mm de comprimento.

### Impressão e fixação

1. Gere o PDF da placa:

   ```bash
   python3 server/tools/generate_markers.py --out placa_palmilha_inteligente.pdf
   ```

2. **Imprima em escala 100% (tamanho real)** — desative qualquer opção
   "ajustar à página" do driver de impressão. O PDF contém cruzes de referência
   e as instruções de impressão.
3. **Verifique com régua:** o lado de cada marcador deve medir **40 mm** e a
   distância entre os centros dos marcadores 0→1 deve medir **250 mm**
   (0→3: **380 mm**). Tolerância: ± 0,5 mm. Se não bater, reimprima — não use a
   placa fora de escala.
4. Fixe a folha **sob a placa** de acrílico/vidro (impressão voltada para cima,
   vista através da placa), colando pelas bordas com fita, bem esticada e sem
   bolhas. Assim o pé pisa na superfície lisa e os marcadores não desgastam.
   - Alternativa durável: impressão em vinil adesivo aplicado no verso, ou
     serigrafia/UV direto na placa.

## 2. Montagem do ambiente

- Posicione a placa no chão, encostada em uma parede clara se possível, com a
  **parte superior (IDs 0 e 1) para longe do operador**.
- **Iluminação difusa e uniforme:** luz ambiente de teto ou janela indireta.
  Evite:
  - luz direta do sol ou spot criando sombras duras do pé;
  - reflexos especulares na placa (ajuste o ângulo da luz ou use base fosca);
  - flash do celular (cria reflexo no acrílico).
- Fundo da placa claro e sem estampas; o contraste pé × placa é o que permite a
  segmentação automática.
- Limpe a placa entre pacientes (álcool 70%).

## 3. Posicionamento do pé

- Paciente **descalço** (sem meia, sem curativo cobrindo a planta, se possível).
- **Apoio total do pé** na placa, em carga (em pé), peso distribuído nos dois
  pés — o pé fotografado dentro da placa e o outro apoiado fora, ao lado, na
  mesma altura, para não inclinar a pelve.
- O pé inteiro deve ficar **dentro da área útil** (retângulo interno aos
  marcadores), sem tocar nem sombrear os marcadores.
- Alinhe o pé aproximadamente com o eixo vertical da placa (calcanhar para a
  borda inferior, dedos para a superior). O software tolera pequenas rotações e
  reporta o ângulo (`axis_angle_deg`), mas evite ângulos maiores que ~15°.
- Dedos relaxados e apoiados (não em garra por tensão).

## 4. Posicionamento do celular

- Câmera **paralela à placa** (celular na horizontal sobre a placa, tela para
  cima do operador), apontando para baixo.
- Distância: **40–60 cm** da placa.
- **Os 4 marcadores devem aparecer inteiros na foto** — este é o critério
  principal. Sem os 4 marcadores o processamento falha com
  `markers_not_found`.
- Enquadre com folga; a retificação por homografia corrige perspectiva leve,
  mas quanto mais perpendicular, melhor.
- Foco travado na planta do pé/placa, imagem nítida (sem tremido), sem flash.
- No app Android, a tela de **captura guiada** mostra a moldura e as instruções;
  no painel web, qualquer foto que cumpra os critérios acima pode ser enviada.

## 5. Identificação do pé (D/E)

- Cada captura é registrada como **pé esquerdo (`left`)** ou
  **pé direito (`right`)** — selecione corretamente antes de fotografar/enviar.
- Convenção de conferência: na foto com a parte superior da placa para cima, o
  **hálux do pé direito fica à esquerda** da imagem e vice-versa. Confira o
  overlay processado antes de concluir o exame.
- Enviar nova foto do mesmo pé/vista **substitui** a captura anterior do exame.

## 6. Fotos complementares (opcionais)

Além da vista **plantar** (a única processada no MVP), o sistema aceita anexar
fotos **laterais** (`lateral`) e **dorsais** (`dorsal`) para documentação
qualitativa (formato do arco, calosidades, deformidades visíveis). Elas não
geram medidas no MVP — servem de registro e serão insumo da Fase 3D
(ver [roadmap-3d.md](roadmap-3d.md)).

## 7. Checklist de captura

Antes de enviar cada foto, confirme:

- [ ] Placa apoiada em piso plano, sem balanço.
- [ ] Impressão conferida com régua (marcador 40 mm; centros 250 × 380 mm).
- [ ] Placa limpa, sem reflexos fortes nem sombras duras.
- [ ] Paciente descalço, em pé, apoio total do pé na placa.
- [ ] Pé inteiro dentro da área útil, sem cobrir os marcadores.
- [ ] Pé aproximadamente alinhado ao eixo vertical da placa.
- [ ] Celular paralelo à placa, a 40–60 cm.
- [ ] **Os 4 marcadores ArUco visíveis e nítidos na foto.**
- [ ] Lado do pé (D/E) selecionado corretamente no app/painel.
- [ ] Foto nítida (sem tremido), sem flash.

Após o processamento, confira no overlay se o contorno acompanha a borda do pé
e se os pontos de medida fazem sentido; ajuste manualmente se necessário.
