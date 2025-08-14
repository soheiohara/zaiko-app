import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- SQLAlchemy設定 ---
db_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-for-dev')
db = SQLAlchemy(app)


# --- データベースモデル定義 ---
class Inventory(db.Model):
    # ... (変更なし)
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
    # ... (変更なし)
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    forecast_date = db.Column(db.String(10), nullable=False)
    manual_consumption = db.Column(db.Integer)
    manual_delivery = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('item_id', 'forecast_date'),)


# --- ルート関数 ---
# ... (index, add, edit, delete, update, forecast 関数は変更なし)
@app.route('/')
def index():
    try:
        items = Inventory.query.order_by(Inventory.item_name).all()
        return render_template('index.html', items=items, search_query='')
    except Exception as e:
        # DBが初期化されていない場合などのエラーをハンドル
        flash(f"データベースの準備ができていない可能性があります。管理者に連絡してください。エラー: {e}", "error")
        return render_template('index.html', items=[], search_query='')

# ... (他の関数もそのまま)
# (add, edit, delete, update, forecast...などの関数も同様に、次のステップで書き換えます)
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
                delivery_day=int(request.form.get('delivery_day')) if request.form.get('delivery_day') else None,
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

@app.route('/forecast',

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)