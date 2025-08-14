import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- ▼▼▼ SQLAlchemy設定（最終確定版）▼▼▼ ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-for-dev')
db = SQLAlchemy(app)
# --- ▲▲▲ 設定ここまで ▲▲▲ ---


# --- データベースモデル定義 (変更なし) ---
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ...(以下、変更なし)...
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
    # ...(以下、変更なし)...
    item_id = db.Column(db.Integer, nullable=False)
    forecast_date = db.Column(db.String(10), nullable=False)
    manual_consumption = db.Column(db.Integer)
    manual_delivery = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('item_id', 'forecast_date'),)


# --- ルート関数 (変更なし) ---
# ... (index, add, edit, delete, update, forecast 関数は変更なし)
@app.route('/')
def index():
    try:
        search_query = request.args.get('q', '')
        query = Inventory.query.order_by(Inventory.item_name)
        if search_query:
            query = query.filter(Inventory.item_name.contains(search_query))
        items = query.all()
        return render_template('index.html', items=items, search_query=search_query)
    except Exception as e:
        flash(f"データベースの準備ができていない可能性があります。「秘密のURL」にアクセスして初期化してください。エラー: {e}", "error")
        return render_template('index.html', items=[], search_query='')

# ... (add, edit, delete, update, forecast...などの関数も同様に、次のステップで書き換えます)
@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        try:
            new_item = Inventory(
                item_name=request.form['item_name'],
                quantity=int(request.form['quantity']),
                location=request.form.get('location'),
                lower_threshold=int(request.form['lower_threshold']) if request.form['lower_threshold'] else None,
                upper_threshold=int(request.form['upper_threshold']) if request.form['upper_threshold'] else None,
                notes=request.form.get('notes'),
                delivery_interval=request.form.get('delivery_interval'),
                delivery_day=int(request.form['delivery_day']) if request.form.get('delivery_day') else None,
                delivery_amount=int(request.form.get('delivery_amount')) if request.form.get('delivery_amount') else None
            )
            db.session.add(new_item)
            db.session.commit()
            flash(f'資材「{new_item.item_name}」が正常に登録されました。', 'success')
        except (ValueError, TypeError):
            flash('数値項目には半角数字を入力してください。', 'error')
        except Exception as e:
            flash(f"登録中にエラーが発生しました: {e}", "error")
            db.session.rollback()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    item = Inventory.query.get_or_404(item_id)
    if request.method == 'POST':
        try:
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
        except (ValueError, TypeError):
            flash('数値項目には半角数字を入力してください。', 'error')
            db.session.rollback()
        except Exception as e:
            flash(f"更新中にエラーが発生しました: {e}", "error")
            db.session.rollback()
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

    overrides = {row.forecast_date: row for row in ForecastOverride.query.filter_by(item_id=selected_item_id).all()}
    
    forecast_days = []
    today = datetime.now().date()
    current_stock = item.quantity
    for i in range(28):
        day = today + timedelta(days=i)
        date_iso = day.isoformat()
        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][day.weekday()]
        
        override_data = overrides.get(date_iso)
        if override_data:
            consumption = override_data.manual_consumption
            delivery = override_data.manual_delivery
        else:
            consumption = 0
            delivery = 0
            if item.delivery_interval == 'WEEKLY' and day.weekday() == item.delivery_day:
                delivery = item.delivery_amount or 0
            elif item.delivery_interval == 'BIWEEKLY' and day.weekday() == item.delivery_day and day.isocalendar().week % 2 == 0:
                delivery = item.delivery_amount or 0
        
        event_text = "納品" if delivery > 0 else ("発送日" if day.weekday() in [0, 1, 4, 5] else "週末/休日")

        start_of_day_stock = current_stock if i == 0 else forecast_days[i-1]['end_stock']
        end_of_day_stock = start_of_day_stock - consumption + delivery
        
        forecast_days.append({
            'date_str': day.strftime('%m/%d'), 'date_iso': date_iso, 'weekday': f"({weekday_jp})",
            'event': event_text, 'consumption': consumption, 'delivery': delivery, 'end_stock': end_of_day_stock
        })
    return render_template('forecast.html', item=item, all_items=all_items, forecast_days=forecast_days)


# --- データベース初期化用の秘密のルート ---
@app.route('/_internal_db_init_command_f9a8b7c6d5e4')
def secret_db_init():
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()

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
            db.session.bulk_save_objects(initial_inventory)
            db.session.commit()
        
        flash("データベースが正常に初期化されました！")
    except Exception as e:
        flash(f"データベース初期化中にエラーが発生しました: {e}", "error")
        db.session.rollback()
        
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)