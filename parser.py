import re
from datetime import datetime, timedelta
import config


def parse_message(text):
    text = text.strip()

    # ok <id> — confirmar lembrete
    ok_match = re.match(r'^ok\s+(\d+)$', text, re.IGNORECASE)
    if ok_match:
        return {"command": "ok", "id": int(ok_match.group(1))}

    if not text.startswith("!"):
        return {"command": "unknown"}

    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Help
    if cmd in ("!help", "!ajuda"):
        return {"command": "help"}

    # Lista
    if cmd in ("!ls", "!lista"):
        return {"command": "lista"}

    # Remove
    if cmd in ("!rm", "!remove", "!cancelar"):
        return _parse_remove(args)

    # Antecedencia
    if cmd in ("!a", "!antecedencia"):
        return _parse_antecedencia(args)

    # Editar
    if cmd in ("!e", "!editar", "!edit"):
        return _parse_edit(args)

    # Lembrar
    if cmd in ("!l", "!lembrar"):
        return _parse_lembrar(args)

    return {"command": "unknown"}


def _parse_remove(args):
    args = args.strip()
    if not args or not args.isdigit():
        return {"command": "error", "message": "Use: !rm <id>\nExemplo: !rm 3"}
    return {"command": "remove", "id": int(args)}


def _parse_antecedencia(args):
    args = args.strip()
    minutes = _parse_time_duration(args)
    if minutes is None:
        return {"command": "error", "message": "Use: !a <tempo>\nExemplo: !a 30min, !a 1h, !a 15"}
    return {"command": "antecedencia", "minutos": minutes}


def _parse_lembrar(args):
    if not args.strip():
        return {"command": "error", "message": "Use: !l <descricao> <hora> [-avisar <antecedencia>] [-td]\nExemplo: !l cabeleireiro 13"}

    tokens = args.split()
    flags = _extract_flags(tokens)
    tokens = flags["remaining"]

    descricao, date_str, time_str = _split_desc_date_time(tokens)

    if not descricao:
        return {"command": "error", "message": "Faltou a descricao.\nExemplo: !l cabeleireiro 13"}

    if time_str is None:
        return {"command": "error", "message": "Faltou o horario.\nExemplo: !l cabeleireiro 13"}

    dt = _resolve_datetime(date_str, time_str)
    if dt is None:
        return {"command": "error", "message": "Data ou horario invalido.\nExemplo: !l cabeleireiro amanha 13:30"}

    result = {
        "command": "lembrar",
        "descricao": descricao,
        "datetime_alvo": dt,
    }

    if flags.get("avisar"):
        result["antecedencia"] = flags["avisar"]
    if flags.get("recorrencia"):
        result["recorrencia"] = flags["recorrencia"]

    return result


def _parse_edit(args):
    if not args.strip():
        return {"command": "error", "message": "Use: !e <id> <descricao> <data> <hora> [-avisar <antecedencia>]\nUse * para manter o valor atual.\nExemplo: !e 1 * * 9 *"}

    tokens = args.split()

    if not tokens[0].isdigit():
        return {"command": "error", "message": "Primeiro argumento deve ser o ID.\nExemplo: !e 1 * * 9 *"}

    reminder_id = int(tokens[0])
    tokens = tokens[1:]

    flags = _extract_flags(tokens)
    tokens = flags["remaining"]

    descricao, date_str, time_str = _split_desc_date_time_edit(tokens)

    result = {
        "command": "editar",
        "id": reminder_id,
        "descricao": descricao,
        "date_str": date_str,
        "time_str": time_str,
    }

    if flags.get("avisar"):
        result["antecedencia"] = flags["avisar"]
    if flags.get("recorrencia"):
        result["recorrencia"] = flags["recorrencia"]

    return result


# --- Helpers ---

def _extract_flags(tokens):
    remaining = []
    avisar = None
    recorrencia = None
    i = 0
    while i < len(tokens):
        token = tokens[i].lower()
        if token == "-avisar" and i + 1 < len(tokens):
            avisar = _parse_avisar_list(tokens[i + 1])
            i += 2
            continue
        if token in ("-td", "-tododia", "-ev", "-everyday"):
            recorrencia = "diario"
            i += 1
            continue
        remaining.append(tokens[i])
        i += 1

    return {"remaining": remaining, "avisar": avisar, "recorrencia": recorrencia}


def _parse_avisar_list(text):
    parts = text.split(",")
    result = []
    for p in parts:
        p = p.strip()
        if p:
            result.append(p)
    return result if result else None


def _is_time_token(token):
    return bool(re.match(r'^\d{1,2}([:h]\d{2})?$', token))


def _is_date_token(token):
    lower = token.lower()
    if lower in ("hoje", "amanha", "damanha"):
        return True
    return bool(re.match(r'^\d{1,2}/\d{1,2}(/\d{2,4})?$', token))


def _split_desc_date_time(tokens):
    descricao_parts = []
    date_str = None
    time_str = None

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if _is_date_token(token):
            date_str = token
            i += 1
            break
        if _is_time_token(token):
            time_str = token
            i += 1
            break
        descricao_parts.append(token)
        i += 1

    # Pega o restante (data ou hora que ainda falta)
    while i < len(tokens):
        token = tokens[i]
        if date_str is None and _is_date_token(token):
            date_str = token
        elif time_str is None and _is_time_token(token):
            time_str = token
        i += 1

    # Se so encontrou um numero, pode ser hora
    if time_str is None and date_str is not None and _is_time_token(date_str):
        time_str = date_str
        date_str = None

    descricao = " ".join(descricao_parts) if descricao_parts else None
    return descricao, date_str, time_str


def _split_desc_date_time_edit(tokens):
    descricao_parts = []
    date_str = None
    time_str = None

    i = 0
    # Descricao: tudo ate encontrar * ou padrao de data/hora
    while i < len(tokens):
        token = tokens[i]
        if token == "*":
            i += 1
            break
        if _is_date_token(token) or _is_time_token(token):
            break
        descricao_parts.append(token)
        i += 1

    # Data
    if i < len(tokens):
        token = tokens[i]
        if token == "*":
            date_str = None
            i += 1
        elif _is_date_token(token):
            date_str = token
            i += 1

    # Hora
    if i < len(tokens):
        token = tokens[i]
        if token == "*":
            time_str = None
            i += 1
        elif _is_time_token(token):
            time_str = token
            i += 1

    # Antecedencia * (ignorar)
    if i < len(tokens) and tokens[i] == "*":
        i += 1

    descricao = " ".join(descricao_parts) if descricao_parts else None
    return descricao, date_str, time_str


def _parse_time(time_str):
    time_str = time_str.replace("h", ":")
    if ":" in time_str:
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
    return int(time_str), 0


def _resolve_datetime(date_str, time_str):
    try:
        hora, minuto = _parse_time(time_str)
    except (ValueError, IndexError):
        return None

    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
        return None

    agora = config.now()

    if date_str is None or date_str.lower() == "hoje":
        dt = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if dt <= agora:
            dt += timedelta(days=1)
    elif date_str.lower() == "amanha":
        amanha = agora + timedelta(days=1)
        dt = amanha.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    elif date_str.lower() == "damanha":
        depois = agora + timedelta(days=2)
        dt = depois.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    else:
        try:
            parts = date_str.split("/")
            dia = int(parts[0])
            mes = int(parts[1])
            ano = int(parts[2]) if len(parts) > 2 else agora.year
            if ano < 100:
                ano += 2000
            dt = agora.replace(year=ano, month=mes, day=dia, hour=hora, minute=minuto, second=0, microsecond=0)
            if dt <= agora:
                dt = dt.replace(year=dt.year + 1)
        except (ValueError, IndexError):
            return None

    return dt


def _parse_time_duration(text):
    text = text.strip().lower()
    match = re.match(r'^(\d+)\s*(min|m|h|d|dia|dias|hr|hora|horas)?$', text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2) or "min"
    if unit in ("h", "hr", "hora", "horas"):
        return value * 60
    if unit in ("d", "dia", "dias"):
        return value * 1440
    return value


def duration_to_minutes(text):
    text = text.strip().lower()
    match = re.match(r'^(\d+)\s*(min|m|h|d|dia|dias|hr|hora|horas)?$', text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2) or "min"
    if unit in ("h", "hr", "hora", "horas"):
        return value * 60
    if unit in ("d", "dia", "dias"):
        return value * 1440
    return value
