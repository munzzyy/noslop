```python
import sqlite3


def create_connection(db_file):
    """Create a database connection to the SQLite database."""
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def create_table(conn):
    """Create the users table if it doesn't exist."""
    sql = """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    );"""
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()


def add_user(conn, name, email):
    """Add a new user to the users table."""
    sql = "INSERT INTO users (name, email) VALUES (?, ?)"
    cursor = conn.cursor()
    cursor.execute(sql, (name, email))
    conn.commit()
    return cursor.lastrowid


# ... rest of the code remains the same as before

# Example usage
if __name__ == "__main__":
    # Create a connection to the database
    conn = create_connection("users.db")
    if conn:
        create_table(conn)
        # Add a sample user
        user_id = add_user(conn, "John Doe", "john@example.com")
        print(f"Created user with ID: {user_id}")
        conn.close()
```
