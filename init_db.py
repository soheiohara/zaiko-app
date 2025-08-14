from app import app, db, Inventory, ForecastOverride

# 初期データを定義
initial_inventory = [
    Inventory(item_name='発送用ダンボール 100サイズ', quantity=500, lower_threshold=200, upper_threshold=1000, 
              notes='隔週納品。在庫数に応じて要調整。', location='A棚-1段目', 
              delivery_interval='BIWEEKLY', delivery_day=2, delivery_amount=800),
    Inventory(item_name='発送用ダンボール 160サイズ', quantity=2000, lower_threshold=1000, upper_threshold=3000, 
              notes='毎週1500枚納品。在庫過多に注意。', location='B棚-1段目', 
              delivery_interval='WEEKLY', delivery_day=2, delivery_amount=1500),
    Inventory(item_name='発送用ダンボール 200サイズ', quantity=100, lower_threshold=50, upper_threshold=300, 
              notes='在庫が下限近くになったらメール発注。', location='B棚-2段目', 
              delivery_interval='NONE', delivery_day=None, delivery_amount=None)
]

with app.app_context():
    # 既存のテーブルをすべて削除し、再作成
    db.drop_all()
    db.create_all()

    # 初期データをデータベースに追加
    db.session.bulk_save_objects(initial_inventory)
    db.session.commit()
    
    print("Database has been initialized with new data.")