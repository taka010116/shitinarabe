import psycopg2

conn = psycopg2.connect(
    host="dpg-d3u927uuk2gs73dm85kg-a.oregon-postgres.render.com",
    database="mydb_6t0u",
    user="takanami",
    password="NknWfypeq70O4aKab0tHZTXXKdGsJz3b",
    sslmode="require"
)
print("✅ 接続成功")
cur = conn.cursor()
cur.execute("SELECT NOW();")
print("現在時刻:", cur.fetchone())
conn.close()
