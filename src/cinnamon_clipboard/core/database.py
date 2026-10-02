import json
import os
import sqlite3
from pathlib import Path


class HistoryDatabase:
    """Handles history persistence in SQLite with support for pinned items."""

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
        """Create the history table and apply migrations if required columns are missing."""
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
                    position INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            
    def load_history(self, limit=50):
        """Load all pinned items and up to 'limit' unpinned items."""
        items = []
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, item_type, data, preview, data_path, pinned
                FROM history
                WHERE pinned = 1
                ORDER BY position ASC
                """
            )
            pinned_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT id, item_type, data, preview, data_path, pinned
                FROM history
                WHERE pinned = 0
                ORDER BY position ASC
                LIMIT ?
                """,
                (limit,)
            )
            normal_rows = cursor.fetchall()

            rows = pinned_rows + normal_rows

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
        """Insert a new item at the beginning of the history."""
        if item_type == "files" and isinstance(data, list):
            stored_data = json.dumps(data)
        else:
            stored_data = str(data)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Make room for the new item at position 0.
            cursor.execute(
                "UPDATE history SET position = position + 1"
            )

            cursor.execute(
                """
                INSERT INTO history (
                    item_type,
                    data,
                    preview,
                    data_path,
                    pinned,
                    position
                )
                VALUES (?, ?, ?, ?, 0, 0)
                """,
                (item_type, stored_data, preview, data_path)
            )

            conn.commit()
            return cursor.lastrowid

    def save_order(self, items):
        """Persist the current history order."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            for position, item in enumerate(items):
                cursor.execute(
                    "UPDATE history SET position = ? WHERE id = ?",
                    (position, item["id"])
                )

            conn.commit()

    def toggle_pin(self, item_id, is_pinned):
        """Mark or unmark an item as pinned."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE history SET pinned = ? WHERE id = ?", (1 if is_pinned else 0, item_id))
            conn.commit()

    def delete_item(self, item_id):
        """Delete a record by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
            conn.commit()

    def clear_all(self, keep_pinned=True):
        """Clear the history but keep pinned items if keep_pinned=True."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if keep_pinned:
                cursor.execute("DELETE FROM history WHERE pinned = 0")
            else:
                cursor.execute("DELETE FROM history")
            conn.commit()
