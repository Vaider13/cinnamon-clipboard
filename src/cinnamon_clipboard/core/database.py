import json
import os
import sqlite3
from pathlib import Path


class HistoryDatabase:
    """Maneja la persistencia del historial en SQLite con soporte para elementos anclados."""

    def __init__(self, db_path=None):
        if db_path is None:
            data_dir = Path.home() / ".local" / "share" / "cinnamon-clipboard"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "history.db"
        else:
            self.db_path = Path(db_path)

        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crea la tabla de historial y aplica migraciones si faltan columnas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    data_path TEXT,
                    pinned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migración por si la tabla fue creada sin la columna 'pinned'
            cursor.execute("PRAGMA table_info(history)")
            columns = [col[1] for col in cursor.fetchall()]
            if "pinned" not in columns:
                cursor.execute("ALTER TABLE history ADD COLUMN pinned INTEGER DEFAULT 0")

            conn.commit()

    def load_history(self, limit=50):
        """Carga los registros: primero los anclados (pinned) y luego por ID descendente."""
        items = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, item_type, data, preview, data_path, pinned FROM history ORDER BY pinned DESC, id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()

            for row in rows:
                db_id, item_type, raw_data, preview, data_path, pinned = row

                if item_type == "files":
                    try:
                        data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        data = []
                else:
                    data = raw_data

                items.append({
                    "id": db_id,
                    "type": item_type,
                    "data": data,
                    "preview": preview,
                    "data_path": data_path,
                    "pinned": bool(pinned)
                })
        return items

    def add_item(self, item_type, data, preview, data_path=None):
        """Inserta un nuevo elemento no anclado por defecto."""
        if item_type == "files" and isinstance(data, list):
            stored_data = json.dumps(data)
        else:
            stored_data = str(data)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (item_type, data, preview, data_path, pinned) VALUES (?, ?, ?, ?, 0)",
                (item_type, stored_data, preview, data_path)
            )
            conn.commit()
            return cursor.lastrowid

    def toggle_pin(self, item_id, is_pinned):
        """Marca o desmarca un ítem como anclado."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE history SET pinned = ? WHERE id = ?", (1 if is_pinned else 0, item_id))
            conn.commit()

    def delete_item(self, item_id):
        """Elimina un registro por su ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
            conn.commit()

    def clear_all(self, keep_pinned=True):
        """Vacía el historial pero conserva los elementos anclados si keep_pinned=True."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if keep_pinned:
                cursor.execute("DELETE FROM history WHERE pinned = 0")
            else:
                cursor.execute("DELETE FROM history")
            conn.commit()