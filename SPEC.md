# FootScan — Especificação Técnica (MVP 2D calibrado)

App de escaneamento de pé pelo celular para captura, medição e documentação,
com apoio à fabricação de palmilhas personalizadas. **Sem diagnóstico automático no MVP.**

Este documento é o CONTRATO entre os módulos. Qualquer código deve seguir
exatamente os nomes, formatos e assinaturas definidos aqui.

## Layout do repositório

```
README.md                  — visão geral, setup, uso
SPEC.md                    — este documento
.gitignore
server/
  requirements.txt
  run.sh                   — uvicorn app.main:app
  app/
    __init__.py
    main.py                — cria FastAPI, inclui routers, monta /panel (webpanel estático), bootstrap admin
    config.py              — settings via env vars
    database.py            — engine SQLAlchemy 2.x + SessionLocal + Base + init_db()
    models.py              — modelos ORM
    schemas.py             — Pydantic v2
    security.py            — hash de senha (passlib pbkdf2_sha256), JWT HS256 (pyjwt)
    deps.py                — get_db, get_current_user, require_admin
    audit.py               — log_action(db, user_id, action, entity, entity_id, details)
    routers/
      __init__.py
      auth.py patients.py exams.py captures.py reports.py sync.py users.py audit.py
    processing/
      __init__.py
      calibration.py       — detecção ArUco + homografia + retificação
      segmentation.py      — segmentação do pé (contorno)
      measures.py          — cálculo das medidas a partir do contorno
      pipeline.py          — process_capture() e recompute_from_landmarks()
    reportgen/
      __init__.py
      pdf.py               — build_exam_pdf()
  tools/
    generate_markers.py    — gera PDF imprimível da placa (marcadores ArUco)
    make_demo_image.py     — gera imagem sintética de teste/demonstração
  tests/
    conftest.py test_auth.py test_patients.py test_exams_flow.py test_sync.py test_processing.py
webpanel/                  — painel web estático (pt-BR, sem CDN externo)
  index.html  app.js  styles.css
android/                   — scaffold Kotlin + Jetpack Compose + CameraX + Room
docs/
  kit-de-captura.md  protocolo-validacao.md  privacidade-lgpd.md  roadmap-3d.md
```

## Stack e dependências (server/requirements.txt)

```
fastapi>=0.110
uvicorn[standard]>=0.29
sqlalchemy>=2.0
pydantic>=2.6
pydantic-settings>=2.2
opencv-python-headless>=4.9
numpy>=1.26
reportlab>=4.1
passlib>=1.7.4
PyJWT>=2.8
python-multipart>=0.0.9
httpx>=0.27
pytest>=8.0
```

Banco: SQLite por padrão; PostgreSQL via `FOOTSCAN_DB_URL` (o código não pode usar nada exclusivo de SQLite).

## Configuração (app/config.py — pydantic-settings, prefixo de env `FOOTSCAN_`)

| Setting | Env var | Default |
|---|---|---|
| `db_url` | FOOTSCAN_DB_URL | `sqlite:///./footscan.db` |
| `data_dir` | FOOTSCAN_DATA_DIR | `./data` (imagens em `{data_dir}/captures/`) |
| `secret_key` | FOOTSCAN_SECRET_KEY | `dev-secret-change-me` |
| `token_expire_minutes` | FOOTSCAN_TOKEN_EXPIRE_MINUTES | `480` |
| `admin_email` | FOOTSCAN_ADMIN_EMAIL | `admin@clinica.local` |
| `admin_password` | FOOTSCAN_ADMIN_PASSWORD | `admin1234` |
| `admin_name` | FOOTSCAN_ADMIN_NAME | `Administrador` |

No startup (`main.py`): `init_db()`; se não existir nenhum usuário, cria o admin acima (role `admin`).

## Modelos (app/models.py) — todos com `id` int PK autoincremento e `uuid` str único (uuid4 hex)

- **User**: uuid, name, email (unique), password_hash, role (`admin`|`professional`), is_active bool, created_at
- **Patient**: uuid, name, birth_date (date, nullable), sex (`F`|`M`|`outro`, nullable), document (nullable), phone, email, notes, consent_accepted_at (datetime nullable), consent_version (str nullable), created_by_id (FK User), created_at, updated_at, deleted_at (soft delete, nullable)
- **Exam**: uuid, patient_id (FK), professional_id (FK User), status (`draft`|`processed`|`reviewed`), notes, created_at, updated_at
- **Capture**: uuid, exam_id (FK), foot_side (`left`|`right`), view (`plantar`|`lateral`|`dorsal`; MVP processa só `plantar`), image_path, processed bool, measures_json (TEXT nullable), manual_landmarks_json (TEXT nullable), error (TEXT nullable), created_at, updated_at
- **AuditLog**: user_id (FK nullable), action, entity, entity_id (str), details_json (TEXT), created_at

Unicidade lógica: um exame tem no máx. 1 capture por (foot_side, view) — re-upload substitui (apaga arquivo antigo).

## Pipeline de processamento (contrato central)

### Placa de captura (kit físico)

- 4 marcadores **ArUco DICT_4X4_50**, IDs **0,1,2,3** = canto **superior-esquerdo, superior-direito, inferior-direito, inferior-esquerdo** (sentido horário), lado do marcador **40 mm**.
- Os **centros** dos 4 marcadores formam um retângulo de **250 mm (largura) × 380 mm (altura)** — constantes `PLATE_WIDTH_MM = 250.0`, `PLATE_HEIGHT_MM = 380.0`, `MARKER_SIZE_MM = 40.0` em `calibration.py`.
- Retificação: homografia dos 4 centros detectados → retângulo métrico; escala **`SCALE_PX_PER_MM = 2.0`**; imagem retificada com margem de 30 mm em volta do retângulo.

### `processing/pipeline.py`

```python
class ProcessingError(Exception):
    def __init__(self, code: str, message: str): ...
# codes: "markers_not_found" (menos de 4 marcadores), "foot_not_found", "invalid_image"

def process_capture(image_bytes: bytes, foot_side: str) -> dict   # retorna "measures dict" (abaixo)
def recompute_from_landmarks(measures: dict, landmarks: dict) -> dict  # substitui landmarks e recalcula medidas lineares
def render_overlay(image_bytes: bytes, measures: dict) -> bytes   # PNG retificado com contorno+landmarks+medidas desenhados
```

Etapas de `process_capture`: decodifica → detecta ArUco (cv2.aruco) → homografia/retificação → segmentação (cinza, blur, Otsu, morfologia, maior contorno dentro do retângulo útil, excluindo regiões dos marcadores) → PCA do contorno para eixo longitudinal → medidas no sistema métrico (mm, origem = canto superior-esquerdo do retângulo dos centros, eixo y para baixo).

### Formato `measures` (dict JSON-serializável — salvo em `Capture.measures_json`)

```json
{
  "version": 1,
  "foot_side": "left",
  "scale_px_per_mm": 2.0,
  "length_mm": 253.4,
  "forefoot_width_mm": 98.7,
  "midfoot_width_mm": 62.1,
  "heel_width_mm": 71.9,
  "plantar_area_cm2": 155.2,
  "axis_angle_deg": 1.8,
  "landmarks": {
    "toe": [125.1, 12.3], "heel": [121.9, 265.0],
    "forefoot_a": [80.2, 70.1], "forefoot_b": [178.9, 74.4],
    "midfoot_a": [95.0, 150.2], "midfoot_b": [157.1, 152.9],
    "heel_a": [88.4, 232.0], "heel_b": [160.3, 230.1]
  },
  "contour_mm": [[x, y], ...],
  "quality": {"markers_found": 4, "warnings": []}
}
```

Definição das medidas (ao longo do eixo longitudinal do pé, obtido por PCA; posição relativa 0.0 = ponta do dedo/toe, 1.0 = calcanhar/heel):

- `length_mm`: extensão total ao longo do eixo.
- `forefoot_width_mm`: largura máxima perpendicular ao eixo na faixa 0.10–0.40 do comprimento.
- `midfoot_width_mm`: largura **mínima** na faixa 0.40–0.70.
- `heel_width_mm`: largura máxima na faixa 0.75–0.95.
- `plantar_area_cm2`: área do contorno / 100.
- `axis_angle_deg`: ângulo do eixo em relação ao eixo vertical da placa (± graus).
- `landmarks`: extremos reais usados em cada medida, em mm.
- `contour_mm`: polígono simplificado (`cv2.approxPolyDP`, epsilon ≈ 1 mm, máx. ~400 pontos).

`recompute_from_landmarks(measures, landmarks)`: recebe o mesmo formato de `landmarks` (qualquer subconjunto das 8 chaves), substitui, e recalcula `length_mm` = dist(toe, heel), `forefoot_width_mm` = dist(forefoot_a, forefoot_b), idem midfoot/heel. Área e contorno não mudam. Adiciona `"manually_adjusted": true`.

### Ferramentas (server/tools/)

- `generate_markers.py [--out placa_footscan.pdf]`: PDF A3 paisagem→retrato com os 4 ArUco (40 mm) posicionados com centros no retângulo 250×380 mm, cruzes de referência, área do pé desenhada, instruções de impressão em escala 100%. Usa reportlab + cv2.aruco para gerar os bitmaps.
- `make_demo_image.py [--out demo_foot.jpg] [--length-mm 245] [--warp]`: gera foto sintética da placa: fundo claro, 4 ArUco desenhados nas posições corretas, silhueta de pé (elipses compostas) com comprimento conhecido `--length-mm` e larguras conhecidas; com `--warp` aplica perspectiva leve (simula foto de celular). Deve expor função `make_demo(length_mm=245.0, forefoot_mm=98.0, heel_mm=70.0, warp=True) -> (jpg_bytes, ground_truth: dict)` para uso nos testes.

### Teste de acurácia (tests/test_processing.py)

Gera imagem sintética com `make_demo` (com warp), roda `process_capture`, exige:
`|length_mm - gt| ≤ 3.0`, `|forefoot_width_mm - gt| ≤ 3.0`, `|heel_width_mm - gt| ≤ 3.0`, 4 marcadores encontrados. Também testa `recompute_from_landmarks` e erros (`invalid_image`, `markers_not_found` com imagem sem marcadores).

## API REST (prefixo `/api`, JSON; auth Bearer JWT exceto login)

Erros: HTTPException com `detail` legível em pt-BR. 401 sem token/inválido; 403 sem permissão; 404 não encontrado; 422 validação; 400 `ProcessingError` (detail = `{"code": ..., "message": ...}`).

### auth
- `POST /api/auth/login` `{email, password}` → `{access_token, token_type:"bearer", user: UserOut}`
- `GET /api/auth/me` → UserOut

### users (admin)
- `POST /api/users` `{name,email,password,role}` → UserOut ; `GET /api/users` → [UserOut]

UserOut: `{uuid, name, email, role, is_active, created_at}`

### patients
- `GET /api/patients?search=` → [PatientOut] (exclui soft-deleted; search por nome/documento, case-insensitive)
- `POST /api/patients` PatientIn → PatientOut
- `GET /api/patients/{uuid}` ; `PUT /api/patients/{uuid}` ; `DELETE /api/patients/{uuid}` (soft delete)
- `POST /api/patients/{uuid}/consent` `{version: "v1"}` → PatientOut (seta consent_accepted_at=now)
- `GET /api/patients/{uuid}/history` → `[{exam_uuid, created_at, status, measures_by_side: {left: measures|null, right: measures|null}}]` ordenado por data asc — base da comparação entre exames.

PatientIn: `{name, birth_date?, sex?, document?, phone?, email?, notes?}`; PatientOut adiciona `{uuid, consent_accepted_at, consent_version, created_at, updated_at}`.

Regra LGPD: criação de **exame** exige paciente com consentimento registrado (400 se não tiver).

### exams
- `POST /api/exams` `{patient_uuid, notes?}` → ExamOut
- `GET /api/exams?patient_uuid=` → [ExamOut]
- `GET /api/exams/{uuid}` → ExamDetail
- `DELETE /api/exams/{uuid}` (apaga captures e arquivos)

ExamOut: `{uuid, patient_uuid, professional: UserOut, status, notes, created_at, captures: [CaptureOut]}`
CaptureOut: `{uuid, foot_side, view, processed, error, measures (dict|null), manually_adjusted: bool, created_at}`
ExamDetail = ExamOut + `{asymmetry: {length_mm, forefoot_width_mm, midfoot_width_mm, heel_width_mm, plantar_area_cm2} | null, previous_exam: {uuid, created_at, measures_by_side} | null}`
— asymmetry = valor(left) − valor(right), presente só quando ambos os pés plantar processados; previous_exam = exame anterior mais recente do mesmo paciente com alguma medida.

### captures
- `POST /api/exams/{uuid}/captures` multipart: `foot_side`, `view` (default `plantar`), `file`; opcional `client_uuid` (idempotência do app offline: se já existe capture com esse uuid, retorna a existente). Processa sincronamente se `view == "plantar"`; salva measures ou `error` (resposta 200 com CaptureOut mesmo se processamento falhar — o erro vai no campo; status HTTP 400 SOMENTE se arquivo ilegível). Substitui capture existente do mesmo (exam, foot_side, view). Seta exam.status="processed" quando alguma capture processa OK.
- `PUT /api/captures/{uuid}/landmarks` `{landmarks: {...}}` → CaptureOut (via `recompute_from_landmarks`; exam.status="reviewed")
- `GET /api/captures/{uuid}/image` → arquivo original ; `GET /api/captures/{uuid}/overlay` → PNG do overlay (gera on-the-fly)

### reports
- `GET /api/exams/{uuid}/report.pdf` → `application/pdf` (Content-Disposition attachment `relatorio_{patient_name_slug}_{data}.pdf`)

### sync (app offline)
- `POST /api/sync/batch` → upsert por uuid, em ordem patients→exams:
```json
{"patients": [{"uuid", ...PatientIn, "consent_accepted_at"?, "consent_version"?}],
 "exams": [{"uuid", "patient_uuid", "notes"?, "created_at"?}]}
```
→ `{"patients": {"created": n, "updated": n}, "exams": {"created": n, "updated": n}}`. Imagens sobem depois via `POST captures` com `client_uuid`.

### audit (admin)
- `GET /api/audit?limit=100` → [{id, user_email, action, entity, entity_id, details, created_at}]

Ações auditadas (via `audit.log_action`): login, create/update/delete de patient/exam/capture, consent, landmarks_adjust, report_download, sync.

## PDF (reportgen/pdf.py)

```python
def build_exam_pdf(exam, patient, professional, captures_with_measures, asymmetry, previous, overlay_pngs: dict[str, bytes]) -> bytes
```
A4 retrato, pt-BR: cabeçalho "Relatório de Avaliação do Pé — FootScan"; dados do paciente e profissional; data; por pé: imagem overlay + tabela de medidas (mm/cm²); tabela de assimetria E−D; comparação com exame anterior (deltas); rodapé com aviso "Documento de apoio; não constitui diagnóstico" + LGPD + paginação. O router monta os argumentos e chama esta função.

## Painel web (webpanel/ — servido pelo FastAPI em `/panel`, raiz `/` redireciona)

SPA vanilla JS (sem frameworks/CDN), pt-BR, `fetch` na API, token em localStorage. Telas: Login → Pacientes (lista/busca/form/consentimento) → Paciente (dados, botão novo exame, histórico com deltas entre exames) → Exame (upload por pé com preview, overlay renderizado, tabela de medidas, assimetria, ajuste manual de pontos arrastando-os sobre o overlay em um `<canvas>` — envia PUT landmarks —, botão Baixar PDF). Estilo limpo tipo clínica (azul/branco), responsivo. `main.py` serve os estáticos com `StaticFiles`.

## Android (android/ — scaffold compilável, Kotlin + Compose)

Pacote `com.footscan.app`. Gradle Kotlin DSL (AGP 8.x, Kotlin 2.x, Compose BOM, CameraX, Room, Retrofit+Moshi ou kotlinx-serialization, WorkManager). Estrutura: `data/` (Room: PatientEntity, ExamEntity, CaptureEntity + DAOs + AppDatabase; api/: ApiService espelhando a API; repo/), `sync/SyncWorker` (WorkManager: envia sync/batch + uploads pendentes com client_uuid), `ui/` (NavHost com telas: Login, PatientList, PatientForm, ExamNew, CaptureGuide — overlay de moldura e instruções + CameraX —, Results, History, Settings com URL do servidor). Fluxo do infográfico: Cadastro → Seleção do exame → Captura guiada → Processamento (upload) → Resultados → PDF (abre URL do relatório). README.md em android/ com instruções de build. O app é offline-first: grava local, sincroniza quando houver rede.

## Docs (docs/ — pt-BR)

- `kit-de-captura.md`: especificação física da placa (acrílico ≥6 mm, 300×450 mm, área útil, posição dos marcadores 250×380 mm, impressão via `generate_markers.py`, montagem, iluminação, posicionamento do pé/celular, pé D/E, fotos opcionais).
- `protocolo-validacao.md`: comparação com paquímetro/régua antropométrica, repetibilidade inter/intra-profissional, diferentes celulares/iluminação, metas de erro (linear ≤ 3 mm), planilha de registro.
- `privacidade-lgpd.md`: consentimento, base legal, minimização, criptografia (TLS, hash de senha, opção de disco cifrado), controle de acesso por papel, auditoria, retenção/eliminação, direitos do titular.
- `roadmap-3d.md`: Fase 2/3 (fotogrametria/ARCore depth, dorso/laterais/calcanhar, altura do arco, export OBJ/STL/PLY, integração CAD de palmilhas).

## Testes de API (tests/ — pytest, TestClient/httpx, SQLite tmp + data_dir tmp por teste via fixtures em conftest.py)

conftest: app com settings overridados (tmp_path), admin seed, fixture `client` autenticado e `auth_headers`.
- test_auth: login ok/errado, /me, rota protegida sem token → 401, criação de professional por admin, professional não acessa /api/users → 403.
- test_patients: CRUD, busca, soft delete (não aparece na lista; GET direto → 404), consent, exam sem consent → 400.
- test_exams_flow (e2e): paciente+consent → exam → upload demo image (make_demo) pé left e right → measures corretos (tolerância 3 mm), asymmetry presente, landmarks adjust muda length, overlay PNG válido, report.pdf começa com `%PDF`, history retorna exame; segundo exame → previous_exam preenchido.
- test_sync: batch cria e depois atualiza (mesmos uuids), capture com client_uuid é idempotente.

## Convenções

Código e identificadores em inglês; strings voltadas ao usuário e docs em pt-BR. Sem comentários óbvios. Datetimes em UTC ISO na API. Nada de diagnóstico automático — apenas medidas.
