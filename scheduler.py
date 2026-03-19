import json
import threading
import time
from datetime import datetime, timedelta

import config
import database
import notifier


_sent_prealerts = set()


def start():
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    print("[SCHEDULER] Iniciado.")


def _loop():
    while True:
        try:
            _check_and_notify()
        except Exception as e:
            print(f"[SCHEDULER] Erro: {e}")
        time.sleep(30)


def _check_and_notify():
    agora = config.now()
    settings = database.get_settings()
    interval_min = settings["insistence_interval"]
    max_insist = settings["insistence_max"]
    default_antecedencia = settings["default_antecedencia"]

    reminders = database.list_reminders(include_completed=False)

    for r in reminders:
        dt_alvo = datetime.fromisoformat(r["datetime_alvo"])

        # --- Pre-alertas ---
        antecedencia_list = json.loads(r["antecedencia"]) if r["antecedencia"] else []
        if not antecedencia_list and default_antecedencia > 0:
            antecedencia_list = [f"{default_antecedencia}min"]

        alertas_enviados = json.loads(r["alertas_enviados"]) if r["alertas_enviados"] else []

        for alerta in antecedencia_list:
            if alerta in alertas_enviados:
                continue

            minutos = _duration_to_minutes(alerta)
            if minutos is None:
                continue

            alerta_time = dt_alvo - timedelta(minutes=minutos)
            if alerta_time <= agora < dt_alvo:
                key = (r["id"], alerta)
                if key not in _sent_prealerts:
                    msg = notifier.format_prealert(r, alerta)
                    notifier.send_message(msg)
                    database.mark_alert_sent(r["id"], alerta)
                    _sent_prealerts.add(key)

        # --- Lembrete na hora ---
        if dt_alvo <= agora:
            insistencias = r["insistencias"]

            if insistencias >= max_insist:
                continue

            if insistencias == 0:
                msg = notifier.format_reminder_alert(r)
                notifier.send_message(msg)
                database.increment_insistence(r["id"])
            else:
                ultima = r.get("ultima_insistencia")
                if ultima:
                    ultima_dt = datetime.fromisoformat(ultima)
                    if agora >= ultima_dt + timedelta(minutes=interval_min):
                        msg = notifier.format_reminder_alert(r)
                        notifier.send_message(msg)
                        database.increment_insistence(r["id"])


def _duration_to_minutes(text):
    import re
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


def clear_prealert_cache(reminder_id):
    to_remove = {k for k in _sent_prealerts if k[0] == reminder_id}
    _sent_prealerts.difference_update(to_remove)
