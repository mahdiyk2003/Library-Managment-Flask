import os
import secrets
from datetime import datetime, timedelta
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from library import app, db, bcrypt, mail
from library.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             PostForm , RequestResetForm, ResetPasswordForm,
                             AddAdminForm)
from library.models import User, Book
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def home():
    page = request.args.get('page', 1, type=int)
    books_posted = Book.query.order_by(Book.published_at.desc()).paginate(page=page, per_page=3)
    return render_template('home.html', posts=books_posted)
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home') )
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home') )


def save_picture(form_picture , usage):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    if usage=='user':
        picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    if usage=='book':
        picture_path = os.path.join(app.root_path, 'static/books_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn
def remove_picture(object,kind):
    if kind=='user':
        picture_path = url_for('static',filename='profile_pics/'+object.image_file)
    if kind=='book':
        picture_path = url_for('static', filename='books_pics/' + object.thumbnail)
    if os.path.exists(picture_path):
        os.remove(picture_path)


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data , 'user')
            remove_picture(current_user,'user')
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account') )
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form )
@app.route("/post/<int:book_id>")
def book_posted(book_id):
    post = Book.query.get_or_404(book_id)
    return render_template('book.html', title=post.name, book=post)



@app.route("/post/create", methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        name = form.name.data
        author = form.author.data
        category = form.category.data.lower()
        
        price_per_month = form.price_per_month.data
        quantity = form.quantity.data
        if form.thumbnail.data:
            picture_file = save_picture(form.thumbnail.data , 'book')
            thumbnail = picture_file
            book=Book(name=name , author=author , category=category , price_per_month=price_per_month , quantity=quantity , thumbnail=thumbnail)
        else:
            book=Book(name=name , author=author , category=category , price_per_month=price_per_month , quantity=quantity)
        if form.description.data:
            book.description=form.description.data
        db.session.add(book)
        db.session.commit()
        flash('The book has been create!', 'success')
        return redirect(url_for('account'))
    return render_template('create_book.html', title='Update Post',
                           form=form, legend='Update Post')





@app.route("/post/<int:book_id>/update", methods=['GET', 'POST'])
@login_required
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not current_user.is_admin:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        book.name = form.name.data
        book.author = form.author.data
        book.category = form.category.data.lower()
        book.price_per_month = form.price_per_month.data
        book.quantity = form.quantity.data
        if form.thumbnail.data:
            picture_file = save_picture(form.thumbnail.data , 'book')
            remove_picture(book,'book')
            book.thumbnail = picture_file
        
        db.session.commit()
        flash('The book has been updated!', 'success')
        return redirect(url_for('book_posted', book_id=book.id))
    elif request.method == 'GET':
        form.name.data = book.name
        form.author.data = book.author
        form.category.data = book.category 
        form.price_per_month.data = book.price_per_month 
        form.quantity.data = book.quantity 
        form.description.data = book.description
    return render_template('create_book.html', title='Update Post',
                           form=form, legend='Update Post')



@app.route("/post/<int:book_id>/delete", methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not current_user.is_admin:
        abort(403)
    db.session.delete(book)
    db.session.commit()
    flash('The book has been deleted!', 'success')
    return redirect(url_for('home') )



@app.route("/borrow/<int:book_id>", methods=['GET', 'POST'])
@login_required
def borrow_request(book_id):
    book=Book.query.get(book_id)
    if book.quantity>0 and (current_user.money-book.price_per_month)>=0:
        if current_user in book.borrowers:
            flash('You have already borrowed this book before.','warning')
            return redirect(url_for('book_posted',book_id=book.id))
        else:
            book.quantity-=1
            current_user.money-=book.price_per_month
            book.borrowers.append(current_user)
            db.session.add(book)
            db.session.commit()
            flash('The book borrowed successfully!', 'success')
            return redirect(url_for('book_posted',book_id=book.id))
    else:
        flash('This borrowing is not possible!', 'warning')
        return redirect(url_for('book_posted',book_id=book.id))



@app.route("/have_over/<int:book_id>", methods=['GET', 'POST'])
@login_required
def have_over(book_id):
    book=Book.query.get(book_id)
    if current_user in book.borrowers:
        book.quantity+=1
        book.borrowers.remove(current_user)
        db.session.commit()
        flash('The book had over successfully!', 'success')
        return redirect(url_for('book_posted',book_id=book.id ))
    else:
        flash('You have already borrowed this book before.','warning')
        return redirect(url_for('book_posted',book_id=book.id ))




def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='librarymanagement2003@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home') )
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)



@app.route("/admin_create", methods=['GET','POST'])
@login_required
def add_admin():
    if not current_user.is_admin:
        abort(403)
    form = AddAdminForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        user.is_admin=True
        db.session.commit()
        flash('The user got admin successfully.', 'success')
        return redirect(url_for('account'))
    return render_template('add_admin.html',title='Add new admin',form=form)




