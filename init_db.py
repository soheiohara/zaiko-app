import sqlite3

connection = sqlite3.connect('database.db')
cur = connection.cursor()

cur.execute('DROP TABLE IF EXISTS inventory')

# 納品ルールを保存する列を追加
cur.execute('''
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    lower_threshold INTEGER,
    upper_threshold INTEGER,
    notes TEXT,
    location TEXT,
    delivery_interval TEXT,   -- 納品間隔 (NONE, WEEKLY, BIWEEKLY)
    delivery_day INTEGER,     -- 納品曜日 (0=月, 1=火, ...)
    delivery_amount INTEGER   -- 納品数
)
''')

# 初期データに納品ルールを追加
cur.execute("""
    INSERT INTO inventory 
    (item_name, quantity, lower_threshold, upper_threshold, notes, location, delivery_interval, delivery_day, delivery_amount) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    ('発送用ダンボール 100サイズ', 500, 200, 1000, '隔週納品。在庫数に応じて要調整。', 'A棚-1段目', 'BIWEEKLY', 2, 800) # 隔週水曜に800枚と仮定
)
cur.execute("""
    INSERT INTO inventory 
    (item_name, quantity, lower_threshold, upper_threshold, notes, location, delivery_interval, delivery_day, delivery_amount) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    ('発送用ダンボール 160サイズ', 2000, 1000, 3000, '毎週1500枚納品。在庫過多に注意。', 'B棚-1段目', 'WEEKLY', 2, 1500) # 毎週水曜に1500枚
)
cur.execute("""
    INSERT INTO inventory 
    (item_name, quantity, lower_threshold, upper_threshold, notes, location, delivery_interval, delivery_day, delivery_amount) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    ('発送用ダンボール 200サイズ', 100, 50, 300, '在庫が下限近くになったらメール発注。', 'B棚-2段目', 'NONE', None, None) # 定期納品なし
)

# ...（既存のINSERT文などの下）...

# 予測値の上書きを保存するテーブルを新しく作成
cur.execute('DROP TABLE IF EXISTS forecast_overrides')
cur.execute('''
CREATE TABLE forecast_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    forecast_date TEXT NOT NULL,
    manual_consumption INTEGER,
    manual_delivery INTEGER,
    UNIQUE(item_id, forecast_date)
)
''')

print("forecast_overridesテーブルを作成しました。")

# connection.commit() と connection.close() は一番最後に一度だけあればOK
connection.commit()
connection.close()
print("データベースが新しい構造で初期化され、初期データが挿入されました。")