import sqlite3

DB_NAME = "/data/efc_system.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali (Kunlik 5 ta video hisoblagichi bilan)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balans_som REAL DEFAULT 0,
        balans_efc REAL DEFAULT 0,
        balans_coin INTEGER DEFAULT 0,
        last_wheel_time TEXT,
        video_spins_count INTEGER DEFAULT 0,
        last_video_spin_date TEXT,
        referred_by INTEGER DEFAULT 0
    )''')
    
    # Balans buyurtmalari (Cheklar)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposit_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'kutilmoqda'
    )''')
    
    # Global G'ildirak hisoblagichi
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wheel_stats (
        id INTEGER PRIMARY KEY,
        total_spins INTEGER DEFAULT 0
    )''')
    
    # P2P E'lonlar
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS p2p_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        efc_amount REAL,
        som_price REAL,
        status TEXT DEFAULT 'aktiv'
    )''')
    
    # 1vs1 Match xonalari
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_rooms (
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        opponent_id INTEGER,
        bet_efc REAL,
        status TEXT DEFAULT 'kutilmoqda'
    )''')
    
    # Oltin Biletlar
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS golden_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        status TEXT DEFAULT 'aktiv',
        type TEXT DEFAULT 'oltin'
    )''')
    
    # Global wheel stats boshlang'ich qiymat kiritish
    cursor.execute("INSERT OR IGNORE INTO wheel_stats (id, total_spins) VALUES (1, 0)")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    
