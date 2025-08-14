import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- ▼▼▼ SQLAlchemy設定（修正版）▼▼▼ ---
# データベースURLの取得と修正
db_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-for-dev') # SECRET_KEYも環境変数から取得
db = SQLAlchemy(app)
# --- ▲▲▲ 設定ここまで ▲▲▲ ---


# --- データベースモデル定義 (変更なし) ---
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    lower_threshold = db.Column(db.Integer)
    upper_threshold = db.Column(db.Integer)
    notes = db.Column(db.Text)
    location = db.Column(db.String(100))
    delivery_interval = db.Column(db.String(20))
    delivery_day = db.Column(db.Integer)
    delivery_amount = db.Column(db.Integer)

class ForecastOverride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    forecast_date = db.Column(db.String(10), nullable=False)
    manual_consumption = db.Column(db.Integer)
    manual_delivery = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('item_id', 'forecast_date'),)


# --- ルート関数 (変更なし) ---
@app.route('/')
def index():
    items = Inventory.query.order_by(Inventory.item_name).all()
    return render_template('index.html', items=items)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        # ... (変更なし)
        # ... (add関数の残りのコード)
        new_item = Inventory(
            item_name=request.form['item_name'],
            quantity=int(request.form['quantity']),
            location=request.form['location'],
            lower_threshold=int(request.form['lower_threshold']) if request.form['lower_threshold'] else None,
            upper_threshold=int(request.form['upper_threshold']) if request.form['upper_threshold'] else None,
            notes=request.form['notes'],
            delivery_interval=request.form['delivery_interval'],
            delivery_day=int(request.form['delivery_day']) if request.form.get('delivery_day') else None,
            delivery_amount=int(request.form['delivery_amount']) if request.form.get('delivery_amount') else None
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f'資材「{new_item.item_name}」が正常に登録されました。', 'success')
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    item = Inventory.query.get_or_404(item_id)
    if request.method == 'POST':
        # ... (変更なし)
        # ... (edit関数の残りのコード)
        item.item_name = request.form['item_name']
        item.quantity = int(request.form['quantity'])
        item.location = request.form['location']
        item.lower_threshold = int(request.form['lower_threshold']) if request.form['lower_threshold'] else None
        item.upper_threshold = int(request.form['upper_threshold']) if request.form['upper_threshold'] else None
        item.notes = request.form['notes']
        item.delivery_interval = request.form['delivery_interval']
        item.delivery_day = int(request.form['delivery_day']) if request.form.get('delivery_day') else None
        item.delivery_amount = int(request.form['delivery_amount']) if request.form.get('delivery_amount') else None
        
        db.session.commit()
        flash(f'資材「{item.item_name}」の情報を更新しました。', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', item=item)


@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    item_to_delete = Inventory.query.get_or_404(item_id)
    item_name = item_to_delete.item_name
    db.session.delete(item_to_delete)
    db.session.commit()
    flash(f'資材「{item_name}」を削除しました。', 'info')
    return redirect(url_for('index'))

@app.route('/update/<int:item_id>', methods=['POST'])
def update(item_id):
    item = Inventory.query.get_or_404(item_id)
    try:
        change = int(request.form.get('change', 0))
        item.quantity += change
        if item.quantity < 0:
            item.quantity = 0
        db.session.commit()
        flash(f"「{item.item_name}」の在庫を更新しました。", 'info')
    except ValueError:
        flash('更新する数量は半角数字で入力してください。', 'error')
    return redirect(url_for('index'))

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    all_items = Inventory.query.order_by(Inventory.item_name).all()
    if not all_items:
        flash('在庫がありません。まず資材を登録してください。', 'error')
        return redirect(url_for('index'))

    selected_item_id = request.form.get('item_id', request.args.get('item_id', all_items[0].id, type=int), type=int)
    item = Inventory.query.get_or_404(selected_item_id)

    if request.method == 'POST':
        # ... (変更なし)
        # ... (forecast関数のPOST部分のコード)
        for i in range(28):
            day_iso = (datetime.now().date() + timedelta(days=i)).isoformat()
            consumption_val = int(request.form.get(f"consumption-{day_iso}", 0))
            delivery_val = int(request.form.get(f"delivery-{day_iso}", 0))

            override = ForecastOverride.query.filter_by(item_id=selected_item_id, forecast_date=day_iso).first()
            if override:
                override.manual_consumption = consumption_val
                override.manual_delivery = delivery_val
            else:
                new_override = ForecastOverride(
                    item_id=selected_item_id, forecast_date=day_iso,
                    manual_consumption=consumption_val, manual_delivery=delivery_val
                )
                db.session.add(new_override)
        db.session.commit()
        flash('予測値を保存しました。', 'success')
        return redirect(url_for('forecast', item_id=selected_item_id))

    # GETリクエストの処理 (変更なし)
    overrides = {row.forecast_date: row for row in ForecastOverride.query.filter_by(item_id=selected_item_id).all()}
    
    forecast_days = []
    today = datetime.now().date()
    current_stock = item.quantity
    for i in range(28):
        # ... (変更なし)
        # ... (forecast関数のGET部分の計算ロジック)
        day = today + timedelta(days=i)
        date_iso = day.isoformat()
        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][day.weekday()]
        
        override_data = overrides.get(date_iso)
        if override_data:
            consumption = override_data.manual_consumption
            delivery = override_data.manual_delivery
        else: