import sqlite3


def build_database(db_path, sql):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()