import os
import pymysql
from flask import Flask, render_template, request, redirect, url_for, flash, session
import subprocess
from datetime import datetime
import base64
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = 'emotion_secret_key'

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123lyh456lyh',
    'database': 'emotions',
    'charset': 'utf8mb4'
}

# 配置文件夹路径
app.config['INPUT_FOLDER'] = 'input_images'
app.config['OUTPUT_FOLDER'] = os.path.join('static', 'output_images')

# 确保上传和输出目录存在
os.makedirs(app.config['INPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 连接数据库
def get_db_connection():
    return pymysql.connect(**db_config)

# 管理员权限校验装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or not session.get('is_admin'):
            flash('无权限访问后台')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# 首页路由
@app.route('/')
def index():
    return render_template('login.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or url_for('upload')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM login_user WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['is_admin'] = user['is_admin']
            return redirect(url_for('upload'))
        else:
            flash('登录失败，用户名或密码错误')
            return redirect(url_for('login', next=next_url))
    return render_template('login.html')

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) as admin_count FROM login_user WHERE is_admin=1")
    admin_count = cursor.fetchone()['admin_count']
    allow_admin_register = (admin_count == 0)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = int(request.form.get('is_admin', 0)) if allow_admin_register else 0
        try:
            cursor.execute("SELECT * FROM login_user WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('用户名已存在，请选择其他用户名')
                conn.close()
                return redirect(url_for('register'))
            password_hash = generate_password_hash(password)
            cursor.execute("INSERT INTO login_user (username, password, is_admin) VALUES (%s, %s, %s)", (username, password_hash, is_admin))
            conn.commit()
            conn.close()
            flash('注册成功，请登录')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'注册过程中发生错误：{str(e)}')
            conn.rollback()
            conn.close()
            return redirect(url_for('register'))
    conn.close()
    return render_template('register.html', allow_admin_register=allow_admin_register)

# 上传图片路由
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 摄像头拍照上传
        if 'photo_data' in request.form and request.form['photo_data']:
            photo_data = request.form['photo_data']
            # 解析base64头部
            match = re.match(r'data:image/(png|jpeg);base64,(.*)', photo_data)
            if match:
                ext = match.group(1)
                img_data = match.group(2)
                img_bytes = base64.b64decode(img_data)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                input_filename = f"{session['username']}_{timestamp}.png"
                output_filename = f"{session['username']}_{timestamp}_result.png"
                input_path = os.path.join(app.config['INPUT_FOLDER'], input_filename)
                with open(input_path, 'wb') as f:
                    f.write(img_bytes)
                # 保存文件记录到数据库
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO image_records (username, input_image, output_image) 
                    VALUES (%s, %s, %s)
                """, (session['username'], input_filename, output_filename))
                conn.commit()
                conn.close()
                # 调用处理脚本
                input_filename = os.path.abspath(os.path.join('input_images', f"{session['username']}_{timestamp}.png"))
            
                subprocess.run(['python', 'image_emotion_gender_demo.py', input_filename, output_filename], cwd='emotion_recognition\src' )
                # subprocess.run(['python', 'reverse.py', input_filename, output_filename])
                return redirect(url_for('result', filename=output_filename))
            else:
                flash('拍照图片数据格式有误')
                return redirect(request.url)
        # ...原有本地上传逻辑...
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)

        if file:
            # 生成唯一的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_filename = f"{session['username']}_{timestamp}.png"
            output_filename = f"{session['username']}_{timestamp}_result.png"
            
            # 保存输入文件
            input_path = os.path.join(app.config['INPUT_FOLDER'], input_filename)
            file.save(input_path)
            
            # 保存文件记录到数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO image_records (username, input_image, output_image) 
                VALUES (%s, %s, %s)
            """, (session['username'], input_filename, output_filename))
            conn.commit()
            conn.close()

            # 调用处理脚本
            input_filename = os.path.abspath(os.path.join('input_images', f"{session['username']}_{timestamp}.png"))
            
            subprocess.run(['python', 'image_emotion_gender_demo.py', input_filename, output_filename], cwd='emotion_recognition\src' )
            # subprocess.run(['python', 'reverse.py', input_filename, output_filename])

            # 跳转到结果页面
            return redirect(url_for('result', filename=output_filename))

    return render_template('upload.html')

# 结果路由
@app.route('/result')
def result():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    filename = request.args.get('filename')
    if not filename:
        return redirect(url_for('upload'))
        
    output_image_path = url_for('static', filename=f'output_images/{filename}')
    return render_template('result.html', output_image=output_image_path)

# 历史记录路由
@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
        SELECT input_image, output_image, created_at 
        FROM image_records 
        WHERE username = %s 
        ORDER BY created_at DESC
    """, (username,))
    
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('history.html', records=records)

# 删除历史记录
@app.route('/history/delete', methods=['POST'])
def delete_history():
    if 'username' not in session:
        return redirect(url_for('login'))
    delete_ids = request.form.getlist('delete_ids')
    if not delete_ids:
        flash('请选择要删除的记录')
        return redirect(url_for('history'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for input_image in delete_ids:
            # 查找output_image
            cursor.execute("SELECT output_image FROM image_records WHERE username=%s AND input_image=%s", (session['username'], input_image))
            row = cursor.fetchone()
            if row:
                output_image = row[0]
                # 删除图片文件
                input_path = os.path.join(app.config['INPUT_FOLDER'], input_image)
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_image)
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
            # 删除数据库记录
            cursor.execute("DELETE FROM image_records WHERE username=%s AND input_image=%s", (session['username'], input_image))
        conn.commit()
        flash('删除成功')
    except Exception as e:
        flash(f'删除失败: {str(e)}')
        conn.rollback()
    conn.close()
    return redirect(url_for('history'))

# 退出登录
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 后台登录页面
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM login_user WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and user['is_admin'] and check_password_hash(user['password'], password):
            session['username'] = username
            session['is_admin'] = 1
            return redirect(url_for('admin'))
        else:
            flash('仅限管理员账号登录后台')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

# 后台管理页面
@app.route('/admin')
def admin():
    if 'username' not in session or not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, username, is_admin FROM login_user")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# 新增用户
@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username']
    password = request.form['password']
    is_admin = int(request.form.get('is_admin', 0))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO login_user (username, password, is_admin) VALUES (%s, %s, %s)", (username, password_hash, is_admin))
        conn.commit()
        flash('用户添加成功')
    except Exception as e:
        flash(f'添加用户失败: {str(e)}')
        conn.rollback()
    conn.close()
    return redirect(url_for('admin'))

# 删除用户
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM login_user WHERE id = %s", (user_id,))
        conn.commit()
        flash('用户删除成功')
    except Exception as e:
        flash(f'删除用户失败: {str(e)}')
        conn.rollback()
    conn.close()
    return redirect(url_for('admin'))

# 编辑用户
@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
@admin_required
def edit_user(user_id):
    username = request.form['username']
    password = request.form['password']
    is_admin = int(request.form.get('is_admin', 0))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        if password:
            password_hash = generate_password_hash(password)
            cursor.execute("UPDATE login_user SET username=%s, password=%s, is_admin=%s WHERE id=%s", (username, password_hash, is_admin, user_id))
        else:
            cursor.execute("UPDATE login_user SET username=%s, is_admin=%s WHERE id=%s", (username, is_admin, user_id))
        conn.commit()
        flash('用户信息更新成功')
    except Exception as e:
        flash(f'更新用户失败: {str(e)}')
        conn.rollback()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
    