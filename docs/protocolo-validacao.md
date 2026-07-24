# Protocolo de validação metrológica — FootScan (MVP 2D)

Antes do uso clínico rotineiro, cada instalação (placa impressa + celulares da
equipe) deve passar por esta validação. O objetivo é demonstrar que o erro das
medidas lineares do FootScan em relação a instrumentos de referência é
**≤ 3 mm** e que os resultados são repetíveis.

> O FootScan não faz diagnóstico; a validação cobre exclusivamente a exatidão e
> a precisão das **medidas**.

## 1. Instrumentos de referência

- **Paquímetro** (analógico ou digital, capacidade ≥ 150 mm) — larguras de
  antepé, mediopé e calcanhar.
- **Régua antropométrica de pé** (ou paquímetro de haste longa / medidor tipo
  Brannock em mm) — comprimento do pé.
- Régua metálica de 500 mm — conferência da placa (marcadores e retângulo
  250 × 380 mm) antes de qualquer sessão.

## 2. Procedimento de comparação

Para cada voluntário e cada pé:

1. Registrar o voluntário como paciente de teste (com consentimento) e criar um
   exame.
2. **Medida de referência** (em carga, mesma postura da foto):
   - comprimento: do ponto mais posterior do calcanhar à ponta do dedo mais
     longo, ao longo do eixo do pé;
   - largura do antepé: na região das cabeças metatarsais (largura máxima);
   - largura do calcanhar: largura máxima da região posterior;
   - (opcional) largura do mediopé: menor largura do istmo.
   Cada medida de referência é tomada **duas vezes**; usar a média. Se as duas
   leituras diferirem mais de 2 mm, repetir.
3. **Captura FootScan** conforme o [kit-de-captura.md](kit-de-captura.md)
   (vista plantar, 4 marcadores visíveis) e registro dos valores
   `length_mm`, `forefoot_width_mm`, `midfoot_width_mm`, `heel_width_mm`
   retornados pelo sistema **sem ajuste manual**.
4. Calcular o erro = valor FootScan − valor de referência, por medida.

### Amostra mínima

- **n ≥ 10 voluntários (20 pés)**, cobrindo:
  - comprimentos variados (idealmente de ~200 a ~290 mm);
  - ambos os sexos;
  - ao menos 2 tipos visuais de pé (ex.: arco aparente alto/baixo).

### Tabela de registro

Uma linha por pé (duplicar a tabela por sessão/celular):

| Data | Voluntário | Pé (D/E) | Celular | Iluminação | Compr. ref (mm) | Compr. FS (mm) | Erro (mm) | Antepé ref | Antepé FS | Erro | Mediopé ref | Mediopé FS | Erro | Calcanhar ref | Calcanhar FS | Erro | Obs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

Registrar também, por captura: `markers_found` (deve ser 4) e eventuais
`warnings` do campo `quality`.

## 3. Repetibilidade

### Intra-profissional (mesmo operador)

- O mesmo profissional captura **3 fotos consecutivas** do mesmo pé, com o
  paciente saindo e voltando à placa entre as fotos.
- Repetir para **≥ 5 pés**.
- Métrica: amplitude (máx − mín) e desvio padrão de cada medida nas 3 capturas.
- **Meta:** amplitude ≤ 3 mm por medida linear.

### Inter-profissional (operadores diferentes)

- **2 ou mais profissionais** capturam o mesmo pé, cada um seguindo o checklist,
  sem ver o resultado do outro.
- Repetir para **≥ 5 pés**.
- Métrica: diferença absoluta entre operadores por medida.
- **Meta:** diferença ≤ 3 mm por medida linear.

## 4. Robustez a celular e iluminação

- Repetir a captura do mesmo pé (mesma sessão) com **≥ 3 modelos de celular**
  diferentes (câmeras/resoluções distintas, incluindo o aparelho mais simples
  da equipe).
- Repetir com **≥ 2 condições de iluminação** (ex.: luz de teto difusa e luz
  natural de janela), sempre dentro do recomendado no kit (sem sol direto, sem
  flash).
- **Meta:** todas as combinações detectam os 4 marcadores e mantêm as medidas
  lineares dentro de ± 3 mm em relação à condição de referência.
- Registrar combinações que falharem (marcadores não detectados, segmentação
  ruim) para restringir o protocolo local.

## 5. Metas de erro e critérios de aceite do MVP

O MVP é considerado **aceito para uso** na instalação quando, com a placa
conferida por régua:

1. **Exatidão:** erro absoluto médio ≤ 2 mm e **erro absoluto ≤ 3 mm em ≥ 95%**
   das medidas lineares (comprimento e larguras) na amostra do item 2, sem
   ajuste manual.
2. **Repetibilidade intra-profissional:** amplitude ≤ 3 mm (item 3).
3. **Reprodutibilidade inter-profissional:** diferença ≤ 3 mm (item 3).
4. **Robustez:** critérios do item 4 atendidos nos celulares e iluminações que a
   equipe usará de fato.
5. **Confiabilidade de detecção:** ≥ 95% das capturas feitas conforme o
   checklist processam sem erro (`markers_found = 4`, sem `foot_not_found`).
6. Casos fora da meta investigados e documentados (placa fora de escala, foto
   fora do protocolo, pé fora da área útil etc.).

> Observação: a área plantar (`plantar_area_cm2`) e o ângulo do eixo
> (`axis_angle_deg`) não têm instrumento simples de referência neste protocolo;
> monitore apenas a repetibilidade de ambos (variação relativa da área ≤ 5%
> entre capturas consecutivas é um bom indicador).

## 6. Reverificação periódica

- Conferir a placa com régua **mensalmente** e após transporte.
- Repetir o item 3 (repetibilidade) com 2 pés sempre que: a placa for
  reimpressa/substituída, um novo modelo de celular entrar em uso ou o app for
  atualizado.
- Arquivar as planilhas preenchidas junto à documentação da clínica (elas também
  respaldam auditorias de qualidade).
