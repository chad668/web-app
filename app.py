from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mailbox.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from extensions import db
db.init_app(app)

from models import User, Mail, Comment, Category

@app.context_processor
def inject_user():
    def get_current_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None
    return dict(get_current_user=get_current_user, User=User)

@app.route('/')
def index():
    categories = Category.query.all()
    selected_category = request.args.get('category')
    if selected_category:
        mails = Mail.query.filter_by(category_id=selected_category).all()
    else:
        mails = Mail.query.all()
    return render_template('index.html', mails=mails, categories=categories, selected_category=selected_category)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        flash('Registration successful')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # In a real app, you would send a reset link to the user's email
            flash('Reset link has been sent to your email')
            return redirect(url_for('login'))
        else:
            flash('Email not found')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/mail/<int:mail_id>')
def mail_detail(mail_id):
    mail = Mail.query.get_or_404(mail_id)
    comments = Comment.query.filter_by(mail_id=mail_id).all()
    return render_template('mail_detail.html', mail=mail, comments=comments)

@app.route('/comment/<int:mail_id>', methods=['POST'])
def add_comment(mail_id):
    if 'user_id' not in session:
        flash('You need to login to comment')
        return redirect(url_for('login'))
    
    content = request.form['content']
    user_id = session['user_id']
    
    new_comment = Comment(content=content, user_id=user_id, mail_id=mail_id)
    db.session.add(new_comment)
    db.session.commit()
    
    flash('Comment added successfully')
    return redirect(url_for('mail_detail', mail_id=mail_id))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    mails = Mail.query.all()
    comments = Comment.query.all()
    return render_template('admin.html', mails=mails, comments=comments)

@app.route('/admin/delete_mail/<int:mail_id>')
def delete_mail(mail_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    mail = Mail.query.get(mail_id)
    db.session.delete(mail)
    db.session.commit()
    
    flash('Mail deleted successfully')
    return redirect(url_for('admin'))

@app.route('/admin/delete_comment/<int:comment_id>')
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    comment = Comment.query.get(comment_id)
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comment deleted successfully')
    return redirect(url_for('admin'))

@app.route('/submit', methods=['GET', 'POST'])
def submit_mail():
    if 'user_id' not in session:
        flash('You need to login to submit content')
        return redirect(url_for('login'))
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form['category_id']
        thumbnail = request.form.get('thumbnail', '')
        user_id = session['user_id']
        
        new_mail = Mail(title=title, content=content, category_id=category_id, thumbnail=thumbnail, user_id=user_id)
        db.session.add(new_mail)
        db.session.commit()
        
        flash('Mail submitted successfully')
        return redirect(url_for('index'))
    
    return render_template('submit_mail.html', categories=categories)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default categories if they don't exist
        if Category.query.count() == 0:
            categories = ['Primary', 'Social', 'Promotions', 'Updates']
            for category_name in categories:
                category = Category(name=category_name)
                db.session.add(category)
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)
