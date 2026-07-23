# FootScan — App Android (scaffold)

Aplicativo Android (Kotlin + Jetpack Compose + CameraX + Room) do FootScan:
captura guiada das fotos da placa, funcionamento offline-first e sincronização
com o servidor FastAPI (ver `SPEC.md` na raiz do repositório).

## Requisitos

- Android Studio (Koala ou mais recente) com Android SDK 34+ instalado.
- JDK 17 (embutido no Android Studio).
- Gradle 8.7+ instalado localmente **apenas para gerar o wrapper na primeira
  vez** (ver abaixo) — depois disso o wrapper cuida de tudo.
- Dispositivo/emulador com Android 8.0 (API 26) ou superior e câmera traseira.

## Primeira compilação (gerar o Gradle wrapper)

O jar do Gradle wrapper **não é comitado** neste repositório. Na primeira vez,
gere o wrapper dentro de `android/`:

```bash
cd android
gradle wrapper --gradle-version 8.7
./gradlew assembleDebug
```

Alternativamente, abra a pasta `android/` no Android Studio ("Open"), que
baixa o Gradle correto automaticamente e permite compilar/instalar pelo botão
Run.

O APK de debug fica em `app/build/outputs/apk/debug/app-debug.apk`.

## Configurar a URL do servidor

1. Suba o servidor FootScan (`server/run.sh`), por padrão em `http://0.0.0.0:8000`.
2. No app, abra **Configurações** (ícone de engrenagem, ou o link na tela de
   login) e informe a URL:
   - Emulador Android: `http://10.0.2.2:8000` (padrão do app) aponta para o
     `localhost` da máquina host.
   - Dispositivo físico na mesma rede: `http://IP_DA_MAQUINA:8000`.
3. Faça login com um usuário do servidor (admin padrão: `admin@clinica.local`
   / `admin1234`).

O scaffold permite tráfego HTTP em texto claro (`usesCleartextTraffic`) para
facilitar o desenvolvimento; em produção use HTTPS.

## Fluxo do app (infográfico)

Cadastro do paciente (com consentimento LGPD) → Seleção do exame → Captura
guiada (moldura da placa + pé E/D, CameraX) → Processamento (upload em segundo
plano) → Resultados (medidas em mm/cm², assimetria E−D) → Exportação do
relatório (abre `{servidor}/api/exams/{uuid}/report.pdf` no navegador).

## Offline-first

- Pacientes, exames e capturas são gravados primeiro no banco local (Room) com
  `syncState = PENDING`.
- O `SyncWorker` (WorkManager, constraint de rede) envia:
  1. `POST /api/sync/batch` com pacientes e exames pendentes (upsert por uuid);
  2. upload das imagens pendentes via `POST /api/exams/{uuid}/captures` com
     `client_uuid` (idempotente — reenvio não duplica).
- Resultados, histórico e overlay são lidos do servidor (exigem conexão).

## Estrutura

```
app/src/main/java/com/footscan/app/
  FootScanApp.kt          — Application + container de dependências
  di/AppContainer.kt
  data/local/             — Room: entidades (uuid/syncState), DAOs, AppDatabase
  data/api/               — Retrofit + kotlinx-serialization (rotas do SPEC)
  data/repo/              — AuthRepository, PatientRepository, ExamRepository
  data/settings/          — DataStore (URL do servidor, token, usuário)
  sync/SyncWorker.kt      — sincronização em segundo plano
  ui/                     — MainActivity, NavHost e telas Compose (pt-BR)
  ui/theme/               — Material 3 (azul clínico)
```

## Limitações do scaffold

- Não há testes instrumentados nem unitários no módulo Android.
- O login exige conexão; não há refresh de token (o token JWT expira conforme
  configurado no servidor — padrão 8 h — e é preciso logar de novo).
- O botão "Exportar relatório (PDF)" abre o navegador com o token na query
  string (`?token=...`); o servidor precisa aceitar token via query para essa
  rota — caso contrário, o navegador receberá 401 (limitação conhecida).
- O ajuste manual de landmarks (`PUT /api/captures/{uuid}/landmarks`) está
  disponível apenas no painel web, não no app.
- Exclusão de pacientes/exames não está exposta no app (apenas no painel web).
- A moldura de captura é estática (não valida em tempo real se os 4 marcadores
  ArUco estão visíveis) — a validação ocorre no processamento do servidor.
- Conflitos de sincronização são resolvidos de forma simplista: a última
  escrita vence (upsert por uuid no servidor).
