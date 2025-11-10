from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# --- Config ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'euromove_secret_key'
import os
basedir =
os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' +  os.path.join(basedir ,'euromove.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
@app.route('/check_db')
def check_db():
    try:
        # list all tables in the database
        result = db.session.execute(
            'SELECT name FROM sqlite_master WHERE type="table";'
             ).fetchall()
        tables = [row[0]] for row in result]
        return f"Database connected! Tables: {tables}"
        except Exception as e:
            return f"Database error: {e}"

# --- Admin Credentials ---
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('euromove123')  # change this password

# --- Models ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # about_us, opportunity, privacy_policy, workshop_info
    image_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Workshop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(255))
    mode = db.Column(db.String(50), nullable=False)  # Online or Physical
    image_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkshopBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    user_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(255))
    user_email = db.Column(db.String(255))
    answer = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Logo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class SocialLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform_name = db.Column(db.String(50))
    url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Make logo available in all templates
@app.context_processor
def inject_logo():
    logo = Logo.query.order_by(Logo.uploaded_at.desc()).first()
    return dict(logo=logo)

# --- Admin Decorator ---
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('You must log in first.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    content = Post.query.filter_by(category='about_us').order_by(Post.created_at.desc()).all()
    return render_template('about.html', content=content)

@app.route('/opportunities')
def opportunities():
    content = Post.query.filter_by(category='opportunity').order_by(Post.created_at.desc()).all()
    return render_template('opportunities.html', content=content)

@app.route('/privacy')
def privacy():
    content = Post.query.filter_by(category='privacy_policy').order_by(Post.created_at.desc()).all()
    return render_template('privacy.html', content=content)

@app.route('/faqs', methods=['GET','POST'])
def faqs():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        user_email = request.form.get('user_email')
        question = request.form.get('question')
        faq = FAQ(user_name=user_name, user_email=user_email, question=question)
        db.session.add(faq)
        db.session.commit()
        flash('Your question has been submitted!', 'success')
        return redirect(url_for('faqs'))
    faqs = FAQ.query.order_by(FAQ.created_at.desc()).all()
    return render_template('faqs.html', faqs=faqs)

@app.route('/contact')
def contact():
    socials = SocialLink.query.order_by(SocialLink.created_at.desc()).all()
    return render_template('contact.html', socials=socials)

@app.route('/workshops')
def workshops():
    workshops = Workshop.query.order_by(Workshop.date).all()
    return render_template('workshops.html', workshops=workshops)

@app.route('/book/<int:workshop_id>', methods=['POST'])
def book_workshop(workshop_id):
    user_name = request.form.get('user_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    booking = WorkshopBooking(workshop_id=workshop_id, user_name=user_name, email=email, phone=phone)
    db.session.add(booking)
    db.session.commit()
    flash('Workshop booked successfully!', 'success')
    return redirect(url_for('workshops'))

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    workshops = Workshop.query.order_by(Workshop.date).all()
    faqs = FAQ.query.order_by(FAQ.created_at.desc()).all()
    socials = SocialLink.query.order_by(SocialLink.created_at.desc()).all()
    logos = Logo.query.order_by(Logo.uploaded_at.desc()).all()
    return render_template('admin.html', posts=posts, workshops=workshops, faqs=faqs, socials=socials, logos=logos)

@app.route('/admin/logo', methods=['GET','POST'])
@admin_required
def admin_logo():
    if request.method == 'POST':
        if 'logo' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['logo']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            import uuid
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logo = Logo(file_name=filename)
            db.session.add(logo)
            db.session.commit()
            flash('Logo uploaded successfully!', 'success')
            return redirect(url_for('admin_logo'))
    return render_template('admin_logo.html')

# --- DB & Upload Folder Setup ---
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
if not os.path.exists('euromove.db'):
    db.create_all()

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)