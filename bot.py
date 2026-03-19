from flask import Flask, request, jsonify
from datetime import datetime

import config
import database
import parser
import notifier
import scheduler

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    # Validar webhook secret
    secret = request.headers.get("X-Webhook-Secret", "")
    if config.OPENCLAW_WEBHOOK_SECRET and secret != config.OPENCLAW_WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    message_text = data.get("message", data.get("text", "")).strip()

    if not message_text:
        return jsonify({"status": "ignored"}), 200

    result = parser.parse_message(message_text)
    response_text = _handle_command(result)

    if response_text:
        notifier.send_message(response_text)

    return jsonify({"status": "ok"}), 200


def _handle_command(result):
    cmd = result.get("command")

    if cmd == "lembrar":
        return _cmd_lembrar(result)
    elif cmd == "lista":
        return _cmd_lista()
    elif cmd == "remove":
        return _cmd_remove(result)
    elif cmd == "editar":
        return _cmd_editar(result)
    elif cmd == "antecedencia":
        return _cmd_antecedencia(result)
    elif cmd == "ok":
        return _cmd_ok(result)
    elif cmd == "help":
        return notifier.format_help()
    elif cmd == "error":
        return notifier.format_error(result.get("message", "Comando invalido."))
    else:
        return notifier.format_help()


def _cmd_lembrar(result):
    dt_alvo = result["datetime_alvo"]
    antecedencia = result.get("antecedencia")
    recorrencia = result.get("recorrencia")

    # Se nao tem antecedencia explicita, usa a padrao
    if not antecedencia:
        settings = database.get_settings()
        default_min = settings["default_antecedencia"]
        if default_min > 0:
            antecedencia = [f"{default_min}min"]

    reminder_id = database.add_reminder(
        descricao=result["descricao"],
        datetime_alvo=dt_alvo,
        antecedencia=antecedencia,
        recorrencia=recorrencia,
    )

    return notifier.format_confirmation(
        reminder_id, result["descricao"], dt_alvo.isoformat(), recorrencia
    )


def _cmd_lista():
    reminders = database.list_reminders()
    return notifier.format_reminder_list(reminders)


def _cmd_remove(result):
    reminder_id = result["id"]
    if database.delete_reminder(reminder_id):
        scheduler.clear_prealert_cache(reminder_id)
        return notifier.format_delete_confirmation(reminder_id)
    return notifier.format_error(f"Lembrete #{reminder_id} nao encontrado.")


def _cmd_editar(result):
    reminder_id = result["id"]
    reminder = database.get_reminder(reminder_id)

    if not reminder:
        return notifier.format_error(f"Lembrete #{reminder_id} nao encontrado.")

    updates = {}

    if result.get("descricao"):
        updates["descricao"] = result["descricao"]

    # Resolver data/hora para edição
    date_str = result.get("date_str")
    time_str = result.get("time_str")

    if date_str or time_str:
        current_dt = datetime.fromisoformat(reminder["datetime_alvo"])

        if time_str:
            time_str_clean = time_str.replace("h", ":")
            if ":" in time_str_clean:
                parts = time_str_clean.split(":")
                hora, minuto = int(parts[0]), int(parts[1])
            else:
                hora, minuto = int(time_str_clean), 0
        else:
            hora, minuto = current_dt.hour, current_dt.minute

        if date_str:
            from parser import _resolve_datetime
            new_dt = _resolve_datetime(date_str, f"{hora}:{minuto:02d}")
            if new_dt:
                updates["datetime_alvo"] = new_dt
        else:
            updates["datetime_alvo"] = current_dt.replace(hour=hora, minute=minuto)

    if result.get("antecedencia"):
        updates["antecedencia"] = result["antecedencia"]

    if result.get("recorrencia"):
        updates["recorrencia"] = result["recorrencia"]

    if updates:
        database.update_reminder(reminder_id, **updates)
        scheduler.clear_prealert_cache(reminder_id)

    updated = database.get_reminder(reminder_id)
    return notifier.format_edit_confirmation(reminder_id, updated)


def _cmd_antecedencia(result):
    minutos = result["minutos"]
    database.set_default_antecedencia(minutos)
    return notifier.format_antecedencia_confirmation(minutos)


def _cmd_ok(result):
    reminder_id = result["id"]
    if database.confirm_reminder(reminder_id):
        scheduler.clear_prealert_cache(reminder_id)
        return notifier.format_ok_confirmation(reminder_id)
    return notifier.format_error(f"Lembrete #{reminder_id} nao encontrado.")


if __name__ == "__main__":
    database.init_db()
    scheduler.start()
    print(f"[BOT] Rodando na porta {config.BOT_PORT}...")
    app.run(host="0.0.0.0", port=config.BOT_PORT, debug=False)
