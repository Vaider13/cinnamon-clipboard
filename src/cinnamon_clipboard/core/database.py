import json
import os
import sqlite3
from pathlib import Path


class HistoryDatabase:
    """Maneja la persistencia del historial en SQLite."""

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
        """Crea la tabla de historial si no existe."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    data_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def load_history(self, limit=50):
        """Carga los últimos registros ordenados por el más reciente."""
        items = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, item_type, data, preview, data_path FROM history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()

            for row in rows:
                db_id, item_type, raw_data, preview, data_path = row

                # Si es una lista de archivos guardada como JSON, la reconstruimos
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
                    "data_path": data_path
                })
        return items

    def add_item(self, item_type, data, preview, data_path=None):
        """Inserta un nuevo elemento en la base de datos."""
        # Convertir lista de rutas a JSON si es de tipo files
        if item_type == "files" and isinstance(data, list):
            stored_data = json.dumps(data)
        else:
            stored_data = str(data)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (item_type, data, preview, data_path) VALUES (?, ?, ?, ?)",
                (item_type, stored_data, preview, data_path)
            )
            conn.commit()
            return cursor.lastrowid

    def delete_item(self, item_id):
        """Elimina un registro por su ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
            conn.commit()

    def clear_all(self):
        """Vacía la tabla de historial."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()