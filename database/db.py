import aiosqlite

class DatabaseManager:
    """
    Asynchronous SQLite database manager class for handling user data,
    chat history, message types, and user interaction modes.

    This class provides high-level functions to interact with the database
    using `aiosqlite` to ensure non-blocking I/O operations.
    """

    def __init__(self, db_path="database.db"):
        """
        Initialize the database manager.

        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.db = None
        self._initialized = False

    async def _ensure_connection(self):
        """
        Ensure that a connection to the database is established and the schema is initialized.
        This method is called before any database operation to guarantee readiness.
        """
        if not self._initialized:
            self.db = await aiosqlite.connect(self.db_path)
            await self.db.execute("PRAGMA foreign_keys = ON;")
            await self._setup_db()
            self._initialized = True

    async def close(self):
        """
        Close the active database connection, if any.
        """
        if self.db:
            await self.db.close()

    async def _setup_db(self):
        """
        Create required tables if they do not exist.
        This method is called internally during initialization.
        """
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                nickname TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                message TEXT,
                response TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS messages_type (
                user_id TEXT PRIMARY KEY,
                type TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS response_count (
                user_id TEXT PRIMARY KEY,
                response_count INTEGER DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_mode (
                user_id TEXT PRIMARY KEY,
                mode INTEGER
            )
            """
        ]
        for query in queries:
            await self.db.execute(query)
        await self.db.commit()

    async def setup_db(self):
        """
        Public method to manually trigger database connection and schema setup.
        """
        await self._ensure_connection()

    async def update_user_info(self, user_id, nickname):
        """
        Insert or update user nickname.

        :param user_id: Unique ID of the user.
        :param nickname: Nickname to associate with the user.
        """
        await self._ensure_connection()
        await self.db.execute("""
            INSERT OR REPLACE INTO users (user_id, nickname)
            VALUES (?, ?)
        """, (user_id, nickname))
        await self.db.commit()

    async def get_user_nick(self, user_id):
        """
        Retrieve nickname of the given user.

        :param user_id: User ID to look up.
        :return: Nickname as a string, or None if not found.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT nickname FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

    async def save_history(self, user_id, message, response):
        """
        Save a message-response pair in the history.

        :param user_id: ID of the user who sent the message.
        :param message: The original user message.
        :param response: The bot's response to the message.
        """
        await self._ensure_connection()
        await self.db.execute("""
            INSERT INTO history (user_id, message, response)
            VALUES (?, ?, ?)
        """, (user_id, message, response))
        await self.db.commit()

    async def get_recent_history(self, user_id, limit=None):
        """
        Get the most recent message-response pairs for a user.

        :param user_id: The user ID whose history is requested.
        :param limit: Optional limit on the number of entries returned.
        :return: List of (message, response) tuples.
        """
        await self._ensure_connection()
        query = "SELECT message, response FROM history WHERE user_id = ? ORDER BY id ASC"
        if limit is not None:
            query += f" LIMIT {limit}"
        async with self.db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchall()

    async def get_user_full_history(self, user_id):
        """
        Retrieve all messages (only messages, not responses) for a user.

        :param user_id: ID of the user.
        :return: A single string combining all messages separated by newlines.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT message FROM history WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return "\n".join(row[0] for row in rows)

    async def get_history_with_id(self, user_id):
        """
        Retrieve full history with ID, message, and response.

        :param user_id: ID of the user.
        :return: List of dictionaries with keys: 'id', 'message', 'response'.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT id, message, response FROM history WHERE user_id = ?", (user_id,)) as cursor:
            return [{"id": row[0], "message": row[1], "response": row[2]} for row in await cursor.fetchall()]

    async def reset_chat(self, user_id):
        """
        Delete all history entries for a given user.

        :param user_id: ID of the user whose history should be deleted.
        """
        await self._ensure_connection()
        await self.db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def set_message_type(self, user_id, msg_type):
        """
        Set the type of message (e.g., text, image) for a user.

        :param user_id: ID of the user.
        :param msg_type: Type of the message.
        """
        await self._ensure_connection()
        await self.db.execute("""
            INSERT INTO messages_type (user_id, type)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET type = excluded.type
        """, (user_id, msg_type))
        await self.db.commit()

    async def get_message_type(self, user_id):
        """
        Retrieve the stored message type for a user.

        :param user_id: ID of the user.
        :return: The message type as a string or None if not found.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT type FROM messages_type WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

    async def success_response(self, user_id):
        """
        Increment the response count for a user. If the user does not exist, create a new entry with count 1.

        :param user_id: ID of the user.
        """
        await self._ensure_connection()
        await self.db.execute("""
            INSERT INTO response_count (user_id, response_count)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET response_count = response_count + 1
        """, (user_id,))
        await self.db.commit()

    async def get_response_count(self, user_id):
        """
        Get the total number of responses sent to a user.

        :param user_id: ID of the user.
        :return: Number of responses sent, or 1 if not found.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT response_count FROM response_count WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 1

    async def delete_by_id(self, ids):
        """
        Delete specific history entries by their ID.

        :param ids: List of message IDs to delete.
        """
        await self._ensure_connection()
        for _id in ids:
            await self.db.execute("DELETE FROM history WHERE id = ?", (_id,))
        await self.db.commit()

    async def fetch_user_messages(self, user_id, limit=10):
        """
        Retrieve a limited number of most recent messages from a user.

        :param user_id: ID of the user.
        :param limit: Number of messages to retrieve (default: 10).
        :return: List of message strings.
        """
        await self._ensure_connection()
        async with self.db.execute("""
            SELECT message FROM history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in reversed(rows)]

    async def set_mode(self, user_id, mode):
        """
        Set a user-specific interaction mode (e.g., silent, verbose, voice mode).

        :param user_id: ID of the user.
        :param mode: Integer representing the mode.
        """
        await self._ensure_connection()
        await self.db.execute("""
            INSERT INTO user_mode (user_id, mode)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET mode = excluded.mode
        """, (user_id, mode))
        await self.db.commit()

    async def get_mode(self, user_id):
        """
        Retrieve the interaction mode set for a specific user.

        :param user_id: ID of the user.
        :return: Integer representing the mode or None if not set.
        """
        await self._ensure_connection()
        async with self.db.execute("SELECT mode FROM user_mode WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
