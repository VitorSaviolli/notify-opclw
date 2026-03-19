# Notificador - Bot de Lembretes via WhatsApp

Bot pessoal de lembretes que envia notificacoes pelo WhatsApp usando [OpenClaw](https://openclaw.ai/) como ponte de comunicacao.

Escrito em Python, roda com Docker em qualquer maquina Linux.

## Funcionalidades

- Criar lembretes com data/hora inteligente (`amanha`, `damanha`, horario simples)
- Lembretes diarios recorrentes (`-td`)
- Multiplos alertas de antecedencia (`-avisar 1h,30min,10min`)
- Insistencia configuravel ate confirmacao (`ok <id>`)
- Edicao parcial de lembretes usando `*` como placeholder
- Historico automatico dos ultimos 20 lembretes
- Comando desconhecido mostra ajuda automaticamente

## Comandos

| Comando | Atalho | Descricao |
|---|---|---|
| `!lembrar <desc> <hora>` | `!l` | Criar lembrete |
| `!lista` | `!ls` | Listar lembretes ativos |
| `!cancelar <id>` / `!remove <id>` | `!rm` | Remover lembrete |
| `!editar <id> <desc> <data> <hora>` | `!e` | Editar lembrete (`*` = manter) |
| `!antecedencia <tempo>` | `!a` | Antecedencia padrao global |
| `!ajuda` | `!help` | Mostrar todos os comandos |
| `ok <id>` | | Confirmar lembrete recebido |

### Exemplos de uso

```
!l cabeleireiro 13              → hoje as 13:00
!l reuniao amanha 9:30          → amanha as 09:30
!l dentista damanha 15          → depois de amanha as 15:00
!l consulta 25/03 10            → dia 25/03 as 10:00
!l remedio 8 -td                → todo dia as 08:00 [LOOP]
!l prova 14 -avisar 1h,30min   → avisa 1h e 30min antes
!e 1 * * 9 *                   → muda so a hora do lembrete #1 para 9:00
!rm 3                           → remove lembrete #3
!a 30min                        → antecedencia padrao de 30 minutos
ok 2                            → confirma lembrete #2
```

### Parsing inteligente

- `13` → 13:00 | `9:30` → 09:30 | `15h30` → 15:30
- `amanha` → dia seguinte | `damanha` → depois de amanha
- Horario ja passou? Assume amanha automaticamente
- Descricao com espacos funciona: `!l reuniao de equipe amanha 14`

## Arquitetura

```
WhatsApp ←→ OpenClaw Gateway ←→ Bot Python (Flask)
                                      ↕
                                   SQLite
                                      ↕
                               Scheduler (cron)
```

| Arquivo | Responsabilidade |
|---|---|
| `bot.py` | Servidor Flask, recebe webhooks, despacha comandos |
| `parser.py` | Interpreta mensagens em comandos estruturados |
| `database.py` | CRUD SQLite para lembretes e configuracoes |
| `scheduler.py` | Thread que verifica lembretes e envia notificacoes |
| `notifier.py` | Formata mensagens e envia via API do OpenClaw |
| `config.py` | Carrega `.env` e define constantes |

## Instalacao

### Pre-requisitos

- [Docker](https://docs.docker.com/engine/install/) instalado na maquina
- [OpenClaw](https://openclaw.ai/) instalado e conectado ao WhatsApp

### Deploy

```bash
# Clonar o repositorio
git clone https://github.com/VitorSaviolli/notify-opclw.git
cd notify-opclw

# Configurar variaveis de ambiente
cp .env.example .env
nano .env  # preencher com suas credenciais

# Subir o bot
docker compose up -d
```

### Configuracao do `.env`

```env
OPENCLAW_API_URL=http://localhost:3000/api/v1/chat
OPENCLAW_API_KEY=sua_api_key_aqui
OPENCLAW_WEBHOOK_SECRET=seu_secret_aqui
BOT_PORT=5000
TIMEZONE=America/Sao_Paulo
```

Para obter a API Key do OpenClaw:
```bash
openclaw dashboard
```
Acesse `http://localhost:18789/` → Settings → API Keys.

### Conectar com OpenClaw

Configure o webhook do OpenClaw para encaminhar mensagens do WhatsApp para o bot:

```
http://localhost:5000/webhook
```

## Comandos uteis

```bash
# Ver logs em tempo real
docker logs -f notificador-bot

# Reiniciar o bot
docker compose restart

# Parar o bot
docker compose down

# Atualizar (apos git pull)
docker compose up -d --build
```

## Stack

- **Python 3.12**
- **Flask** — servidor HTTP
- **SQLite** — banco de dados local
- **OpenClaw** — ponte com WhatsApp
- **Docker** — containerizacao

## Licenca

MIT
