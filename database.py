import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the users table if it does not exist."""
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notifications_enabled INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        print("[DB] Database initialized successfully.")
    except Exception as e:
        print(f"[DB] Error initializing database: {e}")
    finally:
        conn.close()

def get_user(email):
    """Retrieves a user by email."""
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE email = ?', (email.strip().lower(),)).fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"[DB] Error fetching user {email}: {e}")
        return None
    finally:
        conn.close()

def upsert_user(name, email):
    """Logs in or registers a user. If the user exists, returns their profile. Otherwise, creates them."""
    email_clean = email.strip().lower()
    name_clean = name.strip()
    
    conn = get_db_connection()
    try:
        user = get_user(email_clean)
        if user:
            # Optionally update name if it changed
            if user['name'] != name_clean:
                conn.execute('UPDATE users SET name = ? WHERE email = ?', (name_clean, email_clean))
                conn.commit()
                user['name'] = name_clean
            return user
        
        # Insert new user
        conn.execute(
            'INSERT INTO users (email, name, notifications_enabled) VALUES (?, ?, 1)',
            (email_clean, name_clean)
        )
        conn.commit()
        return {
            'email': email_clean,
            'name': name_clean,
            'notifications_enabled': 1
        }
    except Exception as e:
        print(f"[DB] Error upserting user {email}: {e}")
        return None
    finally:
        conn.close()

def update_notification_setting(email, enabled):
    """Updates the user's notification toggle setting."""
    email_clean = email.strip().lower()
    val = 1 if enabled else 0
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET notifications_enabled = ? WHERE email = ?', (val, email_clean))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating notification for {email}: {e}")
        return False
    finally:
        conn.close()

def get_subscribers():
    """Retrieves all users who want daily notifications."""
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT * FROM users WHERE notifications_enabled = 1').fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] Error fetching subscribers: {e}")
        return []
    finally:
        conn.close()
