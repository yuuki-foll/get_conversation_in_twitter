import sqlite3
from pathlib import Path

# パスは各自変えてください。
db_path = "./reply2reply.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("select reply1, reply2 from seq2seq")
for row in cursor:
    try:
        reply1, reply2 = row
        print('------------ 会話 ------------')
        print(" User:", reply1)
        print("Agent:", reply2)
        input()
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(e)
        break