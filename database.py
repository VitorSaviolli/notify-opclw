import sqlite3
import json
import config


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reminders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao       TEXT NOT NULL,
            datetime_alvo   TEXT NOT NULL,
            antecedencia    TEXT DEFAULT '[]',
            recorrencia     TEXT DEFAULT NULL,
            confirmado      INTEGER DEFAULT 0,
            completado_em   TEXT DEFAULT NULL,
            criado_em       TEXT NOT NULL,
            insistencias    INTEGER DEFAULT 0,
            ultima_insistencia TEXT DEFAULT NULL,
            alertas_enviados TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS settings (
            id                      INTEGER PRIMARY KEY CHECK (id = 1),
            default_antecedencia    INTEGER DEFAULT 10,
            insistence_interval     INTEGER DEFAULT 5,
            insistence_max          INTEGER DEFAULT 10
        );

        INSERT OR IGNORE INTO settings (id) VALUES (1);
    """)
    conn.commit()
    conn.close()


# --- Settings ---

def get_settings():
    conn = _connect()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row)


def set_default_antecedencia(minutes):
    conn = _connect()
    conn.execute("UPDATE settings SET default_antecedencia = ? WHERE id = 1", (minutes,))
    conn.commit()
    conn.close()


def set_insistence(interval=None, max_count=None):
    conn = _connect()
    if interval is not None:
        conn.execute("UPDATE settings SET insistence_interval = ? WHERE id = 1", (interval,))
    if max_count is not None:
        conn.execute("UPDATE settings SET insistence_max = ? WHERE id = 1", (max_count,))
    conn.commit()
    conn.close()


# --- Reminders CRUD ---

def add_reminder(descricao, datetime_alvo, antecedencia=None, recorrencia=None):
    conn = _connect()
    antecedencia_json = json.dumps(antecedencia or [])
    cursor = conn.execute(
        """INSERT INTO reminders (descricao, datetime_alvo, antecedencia, recorrencia, criado_em)
           VALUES (?, ?, ?, ?, ?)""",
        (descricao, datetime_alvo.isoformat(), antecedencia_json, recorrencia, config.now().isoformat())
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_reminder(reminder_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_reminders(include_completed=False):
    conn = _connect()
    if include_completed:
        rows = conn.execute(
            "SELECT * FROM reminders ORDER BY datetime_alvo ASC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE confirmado = 0 ORDER BY datetime_alvo ASC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_reminder(reminder_id, **fields):
    conn = _connect()
    allowed = {"descricao", "datetime_alvo", "antecedencia", "recorrencia"}
    updates = []
    values = []
    for key, value in fields.items():
        if key in allowed and value is not None:
            if key == "datetime_alvo":
                value = value.isoformat()
            elif key == "antecedencia":
                value = json.dumps(value)
            updates.append(f"{key} = ?")
            values.append(value)

    if not updates:
        conn.close()
        return False

    values.append(reminder_id)
    conn.execute(f"UPDATE reminders SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_reminder(reminder_id):
    conn = _connect()
    cursor = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def confirm_reminder(reminder_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    if not row:
        conn.close()
        return False

    reminder = dict(row)

    if reminder["recorrencia"] == "diario":
        from datetime import datetime, timedelta
        dt_alvo = datetime.fromisoformat(reminder["datetime_alvo"])
        novo_alvo = dt_alvo + timedelta(days=1)
        conn.execute(
            """UPDATE reminders
               SET confirmado = 0, insistencias = 0,
                   ultima_insistencia = NULL, alertas_enviados = '[]',
                   datetime_alvo = ?
               WHERE id = ?""",
            (novo_alvo.isoformat(), reminder_id)
        )
    else:
        conn.execute(
            """UPDATE reminders
               SET confirmado = 1, completado_em = ?
               WHERE id = ?""",
            (config.now().isoformat(), reminder_id)
        )

    conn.commit()
    conn.close()
    cleanup_history()
    return True


def increment_insistence(reminder_id):
    conn = _connect()
    conn.execute(
        """UPDATE reminders
           SET insistencias = insistencias + 1, ultima_insistencia = ?
           WHERE id = ?""",
        (config.now().isoformat(), reminder_id)
    )
    conn.commit()
    conn.close()


def mark_alert_sent(reminder_id, alert_label):
    conn = _connect()
    row = conn.execute("SELECT alertas_enviados FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    if row:
        enviados = json.loads(row["alertas_enviados"])
        if alert_label not in enviados:
            enviados.append(alert_label)
            conn.execute(
                "UPDATE reminders SET alertas_enviados = ? WHERE id = ?",
                (json.dumps(enviados), reminder_id)
            )
            conn.commit()
    conn.close()


def get_due_reminders():
    agora = config.now().isoformat()
    conn = _connect()
    rows = conn.execute(
        """SELECT * FROM reminders
           WHERE datetime_alvo <= ? AND confirmado = 0
           ORDER BY datetime_alvo ASC""",
        (agora,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_history():
    conn = _connect()
    conn.execute(
        """DELETE FROM reminders WHERE id IN (
               SELECT id FROM reminders
               WHERE confirmado = 1
               ORDER BY completado_em DESC
               LIMIT -1 OFFSET ?
           )""",
        (config.HISTORY_LIMIT,)
    )
    conn.commit()
    conn.close()
