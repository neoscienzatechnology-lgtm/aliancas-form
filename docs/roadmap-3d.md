# Roadmap 3D — Fases 2 e 3 do FootScan

O MVP (Fase 1) entrega a medição 2D calibrada da vista plantar. Este documento
descreve a evolução prevista para escaneamento 3D do pé com o próprio celular,
conforme o infográfico do produto. Nada aqui altera o contrato do MVP
([SPEC.md](../SPEC.md)); são extensões planejadas.

## Visão geral

| Fase | Entrega | Saída principal |
|---|---|---|
| 1 (MVP, atual) | Foto plantar calibrada por placa ArUco | medidas 2D (mm/cm²), PDF |
| 2 | Captura 3D guiada com celular compatível | malha 3D do pé + altura do arco |
| 3 | Integração com fabricação | exportação OBJ/STL/PLY e ponte com CAD de palmilhas |

## Fase 2 — Scanner 3D com o celular

### Tecnologias candidatas

- **Fotogrametria (multi-view stereo):** sequência guiada de fotos ao redor do
  pé, reconstrução no servidor. Funciona em qualquer celular com boa câmera;
  custo: processamento pesado no backend e maior sensibilidade a protocolo.
- **ARCore Depth API / sensores de profundidade (ToF/LiDAR):** captura de mapas
  de profundidade em aparelhos compatíveis; reconstrução mais rápida e estável,
  porém limitada à lista de dispositivos suportados.
- Abordagem prevista: **híbrida** — usar depth quando o aparelho suportar e
  fotogrametria como caminho universal; a placa ArUco do kit permanece como
  referência de escala métrica em ambos os casos.

### Captura

Sessão guiada no app (evolução da tela de captura guiada atual):

- **dorso** do pé (vista superior);
- **laterais** medial e lateral;
- **calcanhar** (vista posterior);
- vista plantar continua vindo da placa (pé em carga) — o 3D complementa, não
  substitui, as medidas 2D em carga.

O app orienta o percurso da câmera (arco ao redor do pé), valida cobertura e
qualidade (nitidez, exposição, marcadores/escala visíveis) antes de enviar.

### Novas medidas

- **Estimativa da altura do arco** (navicular/dorso do mediopé) a partir do
  perfil medial reconstruído;
- alturas e circunferências auxiliares (dorso, tornozelo) conforme validação;
- mantém-se o princípio do produto: **medidas e documentação, sem diagnóstico
  automático**.

### Impacto técnico previsto

- Novos valores de `view` nas capturas e um artefato de reconstrução por exame
  (malha + metadados de qualidade), estendendo o formato `measures`
  (`version` ≥ 2) sem quebrar clientes do MVP;
- fila de processamento assíncrono no servidor (reconstrução demora mais que o
  pipeline 2D síncrono atual);
- armazenamento de malhas em `{data_dir}` e visualizador 3D no painel web.

## Fase 3 — Exportação e integração com palmilhas

- **Exportação de malha** nos formatos **OBJ, STL e PLY**, em milímetros, com
  orientação e origem documentadas, via API e painel (download por exame);
- integração com softwares de **modelagem/CAD de palmilhas** (importação direta
  da malha + medidas 2D em carga no relatório técnico);
- pacote de fabricação por exame: malha 3D + medidas + PDF, pronto para enviar
  ao laboratório (fresagem ou impressão 3D);
- comparação 3D entre exames (evolução de volume/arco), estendendo o histórico
  atual.

## Pré-requisitos técnicos para iniciar a Fase 2

1. **MVP aceito em campo:** critérios do
   [protocolo-validacao.md](protocolo-validacao.md) atendidos em pelo menos uma
   instalação real, com uso rotineiro.
2. **Base estável:** API do MVP em produção com sincronização offline
   funcionando (sem regressões pendentes nos testes).
3. **Estudo de viabilidade concluído:** protótipo comparando fotogrametria ×
   depth em ≥ 3 aparelhos (incluindo um com Depth API), medindo erro contra um
   scanner 3D de referência ou gabarito rígido de dimensões conhecidas.
4. **Meta de acurácia 3D definida** a partir do estudo (proposta inicial:
   erro ≤ 2 mm em distâncias-chave e altura do arco dentro de ± 3 mm).
5. **Infraestrutura de processamento:** fila assíncrona e armazenamento
   dimensionados para reconstrução (CPU/GPU e espaço em disco por exame).
6. **Privacidade revisada:** termo de consentimento atualizado (novas vistas e
   malha 3D são dados de saúde; ver
   [privacidade-lgpd.md](privacidade-lgpd.md)).

## Critérios para promover a Fase 2 → produção (gate)

- Reconstrução bem-sucedida em ≥ 90% das sessões guiadas de teste;
- acurácia dentro da meta definida no estudo de viabilidade, validada com
  protocolo análogo ao 2D (instrumento de referência + repetibilidade);
- tempo de processamento por exame aceitável para o fluxo clínico
  (alvo: minutos, com notificação no app quando pronto);
- exportação OBJ/STL/PLY aberta com sucesso em pelo menos 2 softwares CAD de
  palmilhas usados por laboratórios parceiros.
