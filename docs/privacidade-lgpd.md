# Privacidade e LGPD — FootScan

Este documento orienta o uso do FootScan em conformidade com a Lei Geral de
Proteção de Dados (Lei nº 13.709/2018 — LGPD). Ele descreve como o sistema
trata dados pessoais e o que a clínica (controladora) deve fazer da sua parte.

> O FootScan trata **dados pessoais sensíveis** (dados referentes à saúde:
> imagens do pé e medidas associadas a um paciente identificado). Isso exige
> cuidado reforçado — art. 11 da LGPD.

## 1. Dados tratados

- **Cadastro do paciente:** nome, data de nascimento, sexo, documento, telefone,
  e-mail, observações clínicas.
- **Exames:** fotos do pé (plantar; opcionalmente lateral/dorsal), medidas
  calculadas, contorno, pontos de referência, relatórios PDF.
- **Usuários do sistema:** nome, e-mail, papel (`admin`/`professional`), hash de
  senha.
- **Auditoria:** registro de quem fez o quê e quando (login, criação/edição/
  exclusão, consentimento, ajuste de pontos, download de relatório, sincronização).

## 2. Papéis: controladora e operadora

- **Controladora:** a clínica/profissional que decide as finalidades do
  tratamento (avaliação do paciente, confecção de palmilhas, acompanhamento).
- **Operadora:** quem hospeda/opera o servidor FootScan em nome da clínica
  (a própria clínica, se auto-hospedado, ou o provedor contratado). Formalize a
  relação com o provedor por contrato com cláusulas de proteção de dados.
- A controladora deve indicar um **encarregado (DPO)** e manter canal de contato
  para os titulares.

## 3. Base legal

Para o MVP, a base recomendada é o **consentimento do titular**
(art. 7º, I e art. 11, I da LGPD), colhido antes do primeiro exame.
Conforme o contexto, também podem incidir:

- **Tutela da saúde** (art. 11, II, f), em procedimento realizado por
  profissional de saúde no exercício da atividade;
- **Cumprimento de obrigação legal/regulatória** (guarda de prontuário);
- **Exercício regular de direitos** (art. 7º, VI).

O sistema **exige consentimento registrado para criar exames**: a API retorna
erro 400 ao tentar criar exame para paciente sem consentimento
(`POST /api/patients/{uuid}/consent` registra data/hora e versão do termo).

### Modelo de termo de consentimento (v1)

> **Termo de Consentimento — Avaliação do pé com FootScan**
>
> Eu, ______________________________, documento __________________, autorizo
> [NOME DA CLÍNICA/PROFISSIONAL] a coletar e tratar meus dados pessoais —
> incluindo dados de saúde: fotografias dos meus pés e medidas deles derivadas —
> com as finalidades de: (i) avaliação e acompanhamento profissional;
> (ii) confecção de palmilhas/órteses personalizadas; (iii) emissão de
> relatórios; (iv) manutenção do meu histórico clínico.
>
> Fui informado(a) de que: os dados ficam armazenados em sistema com controle de
> acesso restrito aos profissionais envolvidos no meu atendimento; **não é
> realizado diagnóstico automático** — as imagens e medidas são material de
> apoio ao profissional; posso solicitar acesso, correção ou eliminação dos
> meus dados, bem como revogar este consentimento a qualquer momento, pelo
> canal [CONTATO/DPO], sem prejuízo do tratamento já realizado; os dados serão
> mantidos pelo prazo de [PRAZO — ver política de retenção] e depois eliminados.
>
> Local e data: ____________________  Assinatura: ____________________
>
> Versão do termo: v1

Guarde o termo assinado (papel ou digital) e registre a aceitação no sistema
(campo `consent_version` = versão do termo apresentado).

## 4. Minimização

- Colete **apenas o necessário**: dos campos do cadastro, somente nome é
  obrigatório; preencha os demais apenas se houver finalidade concreta.
- Fotografe **apenas os pés** sobre a placa — enquadre para não capturar rosto,
  tatuagens identificáveis fora do necessário ou terceiros.
- Use as observações (`notes`) para informação clínica pertinente, nunca para
  dados sem relação com a finalidade.
- Não reutilize os dados para outra finalidade (ex.: marketing) sem novo
  consentimento específico.

## 5. Segurança (medidas técnicas e organizacionais)

O sistema fornece:

- **Autenticação** por e-mail/senha com **hash de senha (PBKDF2-SHA256)** —
  senhas nunca são armazenadas em claro;
- **Tokens JWT** com expiração configurável (`FOOTSCAN_TOKEN_EXPIRE_MINUTES`);
- **Controle de acesso por papel:** `professional` acessa pacientes e exames;
  rotas administrativas (gestão de usuários, auditoria) exigem `admin`;
- **Trilha de auditoria** (`GET /api/audit`, admin): login, criação/alteração/
  exclusão de pacientes, exames e capturas, consentimento, ajuste de pontos,
  download de relatórios e sincronizações;
- **Exclusão lógica (soft delete)** de pacientes, preservando a rastreabilidade
  até a eliminação definitiva.

A clínica/operadora deve garantir:

- **TLS (HTTPS) obrigatório** em qualquer acesso fora do localhost — coloque o
  servidor atrás de um proxy reverso com certificado válido; o app Android e o
  painel devem apontar para a URL `https://`;
- **Troca das credenciais padrão** (`admin@clinica.local`/`admin1234`) e
  definição de `FOOTSCAN_SECRET_KEY` forte via variáveis de ambiente;
- **Disco cifrado** no servidor (ex.: LUKS) — recomendado, pois imagens ficam no
  sistema de arquivos (`{data_dir}/captures/`) e o banco pode ser SQLite local;
- Backups cifrados e testados, com o mesmo nível de proteção do dado original;
- Contas individuais por profissional (nunca compartilhar login), desativação
  imediata de contas de quem sai da equipe (`is_active`);
- Bloqueio de tela e cifragem nos celulares usados na captura (o app é
  offline-first e mantém dados locais até sincronizar).

## 6. Retenção e eliminação

- Defina na política interna o **prazo de retenção** dos dados, respeitando as
  normas de guarda de prontuário aplicáveis à profissão (registre o prazo no
  termo de consentimento).
- Ao final do prazo, ou mediante solicitação procedente do titular:
  - exclua o paciente no sistema (soft delete via API/painel);
  - promova a **eliminação definitiva**: remoção dos registros no banco e dos
    arquivos de imagem em `{data_dir}/captures/`, inclusive em backups conforme
    o ciclo de rotação;
  - registre a eliminação (a auditoria grava a ação de exclusão).
- Dados anonimizados de forma irreversível (sem vínculo possível com o titular)
  saem do escopo da LGPD e podem ser mantidos para estatística.

## 7. Direitos do titular

O titular pode exercer, pelo canal informado no termo (art. 18 da LGPD):

- **Confirmação e acesso:** saber se há tratamento e obter cópia dos dados
  (cadastro, imagens, medidas, relatórios);
- **Correção** de dados incompletos, inexatos ou desatualizados;
- **Anonimização, bloqueio ou eliminação** de dados desnecessários ou tratados
  em desconformidade;
- **Portabilidade** (os relatórios PDF e as medidas em JSON atendem a pedidos de
  cópia estruturada);
- **Informação** sobre compartilhamentos e sobre a possibilidade de não
  consentir;
- **Revogação do consentimento**, a qualquer momento.

Responda às solicitações nos prazos da LGPD e documente o atendimento.

## 8. Incidentes

Em caso de incidente de segurança com risco ou dano relevante aos titulares
(vazamento, perda de equipamento com dados etc.), a controladora deve avaliar,
registrar e, quando aplicável, comunicar a **ANPD** e os titulares em prazo
razoável (art. 48). Mantenha um plano simples de resposta a incidentes e use a
trilha de auditoria do sistema na investigação.
