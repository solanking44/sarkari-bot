import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                score INTEGER DEFAULT 0,
                referred_by INTEGER,
                referrals INTEGER DEFAULT 0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                date TEXT,
                link TEXT
            )
        ''')
        await db.commit()

async def add_user(user_id: int, first_name: str, referred_by: int = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_exists = await cursor.fetchone()
            
        if not user_exists:
            await db.execute(
                "INSERT INTO users (user_id, first_name, referred_by) VALUES (?, ?, ?)",
                (user_id, first_name, referred_by)
            )
            if referred_by and referred_by != user_id:
                await db.execute(
                    "UPDATE users SET score = score + 20, referrals = referrals + 1 WHERE user_id = ?",
                    (referred_by,)
                )
            await db.commit()
            return True
        return False

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT score, referrals FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def update_score(user_id: int, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (points, user_id))
        await db.commit()

async def get_leaderboard():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT first_name, score FROM users ORDER BY score DESC LIMIT 5"
        ) as cursor:
            return await cursor.fetchall()

async def save_job(title: str, date: str, link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO jobs (title, date, link) VALUES (?, ?, ?)", (title, date, link))
        await db.commit()
