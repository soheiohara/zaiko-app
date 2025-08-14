from datetime import datetime, timedelta
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'my-secret-key-is-very-secret'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 在庫一覧ページ
@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory ORDER BY item_name').fetchall()
    conn.close()
    return render_template('index.html', items=items)

# 新しい資材を登録するページ
@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity_str = request.form['quantity']
        location = request.form['location']
        lower_threshold_str = request.form['lower_threshold']
        upper_threshold_str = request.form['upper_threshold']
        notes = request.form['notes']

        if not item_name or not quantity_str:
            flash('資材名と在庫数は必須です。', 'error')
            return redirect(url_for('add'))

        try:
            quantity = int(quantity_str)
            lower_threshold = int(lower_threshold_str) if lower_threshold_str else None
            upper_threshold = int(upper_threshold_str) if upper_threshold_str else None
        except ValueError:
            flash('在庫数や閾値には数値を入力してください。', 'error')
            return redirect(url_for('add'))

        conn = get_db_connection()
        conn.execute('INSERT INTO inventory (item_name, quantity, location, lower_threshold, upper_threshold, notes) VALUES (?, ?, ?, ?, ?, ?)',
                     (item_name, quantity, location, lower_threshold, upper_threshold, notes))
        conn.commit()
        conn.close()
        
        flash(f'資材「{item_name}」が正常に登録されました。', 'success')
        return redirect(url_for('index'))

    return render_template('add.html')

# 在庫数を更新する処理（一覧画面の小さなフォーム）
@app.route('/update/<int:item_id>', methods=['POST'])
def update(item_id):
    try:
        change = int(request.form['change'])
    except ValueError:
        flash('更新する数量は半角数字で入力してください。', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    item = conn.execute('SELECT quantity, item_name FROM inventory WHERE id = ?', (item_id,)).fetchone()
    
    if item:
        new_quantity = item['quantity'] + change
        if new_quantity < 0:
            new_quantity = 0
        conn.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (new_quantity, item_id))
        conn.commit()
        flash(f"「{item['item_name']}」の在庫を更新しました。", 'info')

    conn.close()
    return redirect(url_for('index'))

# 資材を編集するページ
# --- ▼▼▼ 削除した場所に、この新しいedit関数を貼り付けます ▼▼▼ ---
@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (item_id,)).fetchone()

    if request.method == 'POST':
        item_name = request.form['item_name']
        # 文字から数値への変換を、より安全な書き方に修正
        try:
            quantity = int(request.form['quantity'])
            lower_threshold = int(request.form['lower_threshold']) if request.form['lower_threshold'] else None
            upper_threshold = int(request.form['upper_threshold']) if request.form['upper_threshold'] else None
            delivery_day = int(request.form['delivery_day']) if request.form.get('delivery_day') else None
            delivery_amount = int(request.form['delivery_amount']) if request.form.get('delivery_amount') else None
        except (ValueError, TypeError):
            flash('数値項目には半角数字を入力してください。', 'error')
            conn.close()
            # itemを渡して編集ページを再表示
            return render_template('edit.html', item=item)
            
        location = request.form['location']
        notes = request.form['notes']
        # 新しいフォーム項目を取得
        delivery_interval = request.form['delivery_interval']

        conn.execute(
            '''UPDATE inventory SET 
               item_name = ?, quantity = ?, location = ?, lower_threshold = ?, 
               upper_threshold = ?, notes = ?, delivery_interval = ?, 
               delivery_day = ?, delivery_amount = ?
               WHERE id = ?''',
            (item_name, quantity, location, lower_threshold, upper_threshold, 
             notes, delivery_interval, delivery_day, delivery_amount, item_id)
        )
        conn.commit()
        
        flash(f'資材「{item_name}」の情報を更新しました。', 'success')
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', item=item)
# --- ▲▲▲ ここまでが新しいedit関数です ▲▲▲ ---
# 資材を削除する処理
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    conn = get_db_connection()
    item = conn.execute('SELECT item_name FROM inventory WHERE id = ?', (item_id,)).fetchone()
    conn.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    if item:
        flash(f'資材「{item["item_name"]}」を削除しました。', 'info')
    return redirect(url_for('index'))

# --- ▼▼▼ この forecast 関数を丸ごと置き換えてください（PRGパターン版） ▼▼▼ ---
@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    conn = get_db_connection()
    all_items = conn.execute('SELECT id, item_name FROM inventory').fetchall()
    conn.close() # アイテムリスト取得後、一旦閉じる

    if not all_items:
        flash('在庫がありません。まず資材を登録してください。', 'error')
        return redirect(url_for('index'))

    # --- ▼▼▼ 書き込み処理 (POST) ▼▼▼ ---
    if request.method == 'POST':
        selected_item_id = int(request.form.get('item_id'))
        conn = get_db_connection()
        for i in range(28):
            day = datetime.now().date() + timedelta(days=i)
            date_iso = day.isoformat()
            
            consumption_val = request.form.get(f"consumption-{date_iso}")
            delivery_val = request.form.get(f"delivery-{date_iso}")

            # UPSERT処理
            conn.execute('''
                INSERT INTO forecast_overrides (item_id, forecast_date, manual_consumption, manual_delivery)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id, forecast_date) DO UPDATE SET
                manual_consumption = excluded.manual_consumption,
                manual_delivery = excluded.manual_delivery
            ''', (selected_item_id, date_iso, int(consumption_val), int(delivery_val)))
        conn.commit()
        conn.close()
        flash('予測値を保存しました。', 'success')
        # 保存後、同じページのGETリクエストにリダイレクトする
        return redirect(url_for('forecast', item_id=selected_item_id))
    # --- ▲▲▲ 書き込み処理ここまで ▲▲▲ ---

    # --- ▼▼▼ 読み込み・表示処理 (GET) ▼▼▼ ---
    selected_item_id = request.args.get('item_id', all_items[0]['id'], type=int)
    
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (selected_item_id,)).fetchone()
    
    # 保存された予測値を取得
    overrides = {}
    rows = conn.execute('SELECT forecast_date, manual_consumption, manual_delivery FROM forecast_overrides WHERE item_id = ?', (selected_item_id,)).fetchall()
    for row in rows:
        overrides[row['forecast_date']] = {
            'consumption': row['manual_consumption'],
            'delivery': row['manual_delivery']
        }
    conn.close()

    # 計算ロジック
    forecast_days = []
    today = datetime.now().date()
    current_stock = item['quantity']

    for i in range(28):
        day = today + timedelta(days=i)
        date_iso = day.isoformat()
        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][day.weekday()]
        
        override_data = overrides.get(date_iso)
        if override_data:
            consumption = override_data['consumption']
            delivery = override_data['delivery']
        else:
            consumption = 0
            delivery = 0
            if item['delivery_interval'] == 'WEEKLY' and day.weekday() == item['delivery_day']:
                delivery = item['delivery_amount']
            elif item['delivery_interval'] == 'BIWEEKLY' and day.weekday() == item['delivery_day'] and day.isocalendar().week % 2 == 0:
                delivery = item['delivery_amount']
        
        event_text = "納品" if delivery > 0 else ("発送日" if day.weekday() in [0, 1, 4, 5] else "週末/休日")

        start_of_day_stock = current_stock if i == 0 else forecast_days[i-1]['end_stock']
        end_of_day_stock = start_of_day_stock - consumption + delivery
        
        forecast_days.append({
            'date_str': day.strftime('%m/%d'), 'date_iso': date_iso, 'weekday': f"({weekday_jp})",
            'event': event_text, 'consumption': consumption, 'delivery': delivery, 'end_stock': end_of_day_stock
        })
    
    return render_template('forecast.html', item=item, all_items=all_items, forecast_days=forecast_days)
# --- ▲▲▲ ここまで ---
if __name__ == '__main__':
    app.run(debug=True)