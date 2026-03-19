import requests
from datetime import datetime, timedelta
import config


def send_message(text):
    try:
        response = requests.post(
            config.OPENCLAW_API_URL,
            headers={
                "Authorization": f"Bearer {config.OPENCLAW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"message": text, "deliver": True, "channel": "whatsapp"},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao enviar mensagem: {e}")
        return False


def format_reminder_alert(reminder):
    rec = " [LOOP]" if reminder.get("recorrencia") == "diario" else ""
    return (
        f"⏰ LEMBRETE ID-{reminder['id']}: {reminder['descricao']}{rec}\n"
        f"Horario: {_format_dt(reminder['datetime_alvo'])}\n"
        f"Responda \"ok {reminder['id']}\" para confirmar."
    )


def format_prealert(reminder, tempo_antes):
    return (
        f"⏰ LEMBRETE ID-{reminder['id']}: {reminder['descricao']} em {tempo_antes}\n"
        f"Horario: {_format_dt(reminder['datetime_alvo'])}"
    )


def format_confirmation(reminder_id, descricao, datetime_alvo, recorrencia=None):
    rec = " [LOOP]" if recorrencia == "diario" else ""
    return (
        f"✅ Lembrete #{reminder_id} criado{rec}:\n"
        f"{descricao} - {_format_dt(datetime_alvo)}"
    )


def format_edit_confirmation(reminder_id, reminder):
    rec = " [LOOP]" if reminder.get("recorrencia") == "diario" else ""
    return (
        f"✏️ Lembrete #{reminder_id} editado{rec}:\n"
        f"{reminder['descricao']} - {_format_dt(reminder['datetime_alvo'])}"
    )


def format_delete_confirmation(reminder_id):
    return f"🗑️ Lembrete #{reminder_id} removido."


def format_ok_confirmation(reminder_id):
    return f"👍 Lembrete #{reminder_id} confirmado!"


def format_antecedencia_confirmation(minutos):
    return f"⏱️ Antecedencia padrao atualizada para {_format_duration(minutos)}."


def format_reminder_list(reminders):
    if not reminders:
        return "📋 Nenhum lembrete ativo."

    lines = ["📋 *Lembretes ativos:*\n"]
    for r in reminders:
        rec = " [LOOP]" if r.get("recorrencia") == "diario" else ""
        lines.append(f"  {r['id']}. {r['descricao']} - {_format_dt(r['datetime_alvo'])}{rec}")

    return "\n".join(lines)


def format_help():
    lines = [
        "📖 *Comandos disponiveis:*",
        "",
        "*Criar lembrete:*",
        "  !l <descricao> <hora>",
        "  !l <descricao> <data> <hora>",
        "  !l <descricao> <hora> -avisar <antecedencia>",
        "  !l <descricao> <hora> -td (lembrete diario)",
        "",
        "  Exemplos:",
        "    !l cabeleireiro 13",
        "    !l reuniao amanha 9:30",
        "    !l dentista 25/03 15",
        "    !l remedio 8 -td",
        "    !l prova damanha 14 -avisar 1h,30min",
        "",
        "  Datas: hoje, amanha, damanha, DD/MM, DD/MM/AAAA",
        "  Horas: 13 = 13:00, 9:30, 15h30",
        "",
        "*Listar lembretes:*",
        "  !ls  ou  !lista",
        "",
        "*Remover lembrete:*",
        "  !rm <id>  ou  !remove <id>  ou  !cancelar <id>",
        "",
        "*Editar lembrete:*",
        "  !e <id> <descricao> <data> <hora> [-avisar <antecedencia>]",
        "  Use * para manter o valor atual.",
        "  Exemplo: !e 1 * * 9 *",
        "",
        "*Antecedencia padrao:*",
        "  !a <tempo>",
        "  Exemplo: !a 30min, !a 1h",
        "",
        "*Confirmar lembrete:*",
        "  ok <id>",
        "",
        "*Ajuda:*",
        "  !help  ou  !ajuda",
    ]
    return "\n".join(lines)


def format_error(message):
    return f"❌ {message}"


def _format_dt(dt_str):
    if isinstance(dt_str, str):
        dt = datetime.fromisoformat(dt_str)
    else:
        dt = dt_str

    agora = config.now()
    if dt.date() == agora.date():
        return f"hoje {dt.strftime('%H:%M')}"
    elif dt.date() == (agora + timedelta(days=1)).date():
        return f"amanha {dt.strftime('%H:%M')}"
    else:
        return dt.strftime("%d/%m/%Y %H:%M")


def _format_duration(minutes):
    if minutes >= 1440 and minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days}d"
    if minutes >= 60 and minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours}h"
    return f"{minutes}min"
