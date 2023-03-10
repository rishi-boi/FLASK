# Importing Modules
from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import MySQLdb
from werkzeug.utils import secure_filename
from datetime import datetime
import json
from flask_mail import Mail
import os
import math

# Reading config file
with open('config.json', 'r') as c:
    params = json.load(c)["params"]

# variables
local_server = True
# Initializing app
app = Flask(__name__)
# Making variable for file storage location
app.config['UPLOAD_FOLDER'] = params['upload_location']
# Session secret key
app.secret_key = 'super secret key'
# Setting-up SMTP server
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail_user'],
    MAIL_PASSWORD = params['gmail_password']
)
# Initializing mail
mail = Mail(app)
# Checking for local server
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

# Initializing SQLAlchemy
db = SQLAlchemy(app)

# Getting tables contents 
class Contacts(db.Model):
    # sno, name, ph, email, date, msg
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    # sno, name, ph, email, date, msg
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(255), nullable=True)

# Home page
@app.route("/")
def home():
    # Filtering posts
    posts = Posts.query.filter_by().all()
    # Logic for length of page
    last = math.ceil(len(posts)/int(params['num_of_pg']))
    # Getting url
    page = request.args.get('page')
    # Logic
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    # Slicing posts
    posts = posts[(page-1)*int(params['num_of_pg']):(page-1)*int(params['num_of_pg'])+ int(params['num_of_pg'])]
    
    # First page
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    # Middle page
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    # Last page
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)

    return render_template('index.html', params = params, posts = posts, prev = prev, next = next)

# About
@app.route("/about")
def about():
    return render_template('about.html', params = params)

# Admin panel
@app.route("/dashboard", methods=['GET','POST'])
def dashboard():
    # Checking if user is already logged in
    if 'user' in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params = params, posts = posts)

    # Checking for post request
    if request.method=='POST':
        # Getting username and password from form
        username = request.form.get('name')
        password = request.form.get('password')
        
        # Checking for correct admin details
        if username == params['admin_user'] and password == params['admin_password']:
            # Setting up session
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params = params, posts = posts)
    
    return render_template('login.html', params = params)
        
# Contact
@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    # Checking for post request
    if(request.method=='POST'):
        '''Add entry to the database'''
        # Getting necessary details from form
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        # Assigning deatils from form to Contacts tabel
        entry = Contacts(name=name, phone_num = phone, msg = message, date= datetime.now(),email = email )
        # Addign entry to database
        db.session.add(entry)
        db.session.commit()

        # Sending mail
        mail.send_message('New message from ' + name,
                        sender=email,
                        recipients = [params['admin_mail']],
                        body = 'Email: ' + email + "\n" + 'Message: ' + message + "\n" + 'Phone: ' + phone
                        )
        
        # Displaying message
        flash('Thanks For Reaching Out. We Will Get Back To You Soon.', 'success')

    return render_template('contact.html', params = params)

# Post
# Showing serial number wise post
@app.route("/post/<string:post_slug>/", methods=['GET','POST'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', post = post, params = params)

# Edit
@app.route("/edit/<string:sno>/", methods=['GET','POST'])
def edit(sno):
    # Checking if user is already logged in
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            # Getting necessary details from form
            title = request.form.get('title')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            
            # Logic for new post
            if sno=='0':
                post = Posts(title=title, slug=slug, content=content, img_file=img_file, date=datetime.now())
                db.session.add(post)
                db.session.commit()
                # Displaying message
                flash('New Post Created Successfully.', 'success')
            
            # Logic for editing post
            else:
                # Getting first post with serial number
                post = Posts.query.filter_by(sno=sno).first()
                # Getting necessary details from form
                post.title = title
                post.slug = slug
                post.img_file = img_file
                post.content = content
                post.date = datetime.now()
                db.session.commit()
                # Displaying message
                flash('Post Edited Successfully.', 'success')
                return redirect('/edit/0' + sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)

# File Uploader
@app.route("/uploader", methods=['GET','POST'])
def uploader():
    # Checking if user is already logged in
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            # Getting File
            f = request.files.get('file1')
            # Saving file
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            # Displaying message
            flash('File Uploaded Successfully.', 'success')

            return redirect('/dashboard')
    
# Logout
@app.route("/logout")
def logout():
    # Killing the session
    session.pop('user')
    # Redirecting to dashboard
    return redirect('/dashboard')

# Deleting
@app.route("/delete/<string:sno>/", methods=['GET','POST'])
def delete(sno):
    # Checking if user is already logged in
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        # Deleting from database
        db.session.delete(post)
        db.session.commit()
        flash('Deleted Successfully.', 'success')
        

        return redirect('/dashboard')

app.run(debug=True)