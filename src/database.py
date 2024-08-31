import sqlite3


def initialize_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS file_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        archive_id TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        yt_channel TEXT NOT NULL,
                        utime INTEGER NOT NULL,
                        ctime INTEGER NOT NULL,
                        file_size INTEGER NOT NULL,
                        file_title TEXT NOT NULL,
                        text_content TEXT)''')
    conn.commit()
    return conn

def fetch_metadata(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT archive_id, channel, yt_channel, utime, ctime, file_size, file_title, text_content FROM file_metadata')
    rows = cursor.fetchall()
    cursor.close()
    return rows

def insert_metadata(conn, metadata_list):
    cursor = conn.cursor()
    try:
        cursor.executemany('''INSERT INTO file_metadata (
                           archive_id, 
                           channel, 
                           yt_channel, 
                           utime, 
                           ctime, 
                           file_size, 
                           file_title, 
                           text_content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', metadata_list)
        conn.commit()
    finally:
        cursor.close()