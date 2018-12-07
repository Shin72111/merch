from flask import render_template, redirect, url_for, flash, request, abort
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm
from app.auth.forms import AdminForm
from app.models import User



@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/admin', methods=['GET', 'POST'])
def admin():
    user_count = User.query.count()
    form = AdminForm()
    if user_count == 0:
        if form.validate_on_submit():
            admid_user = User(username=form.admin_username.data)
            admid_user.set_password(form.admin_password.data)
            db.session.add(admid_user)
            member_user = User(username=form.member_username.data)
            member_user.set_password(form.member_password.data)
            db.session.add(member_user)
            db.session.commit()
            flash('Congratulations, edited users info successfully!')
            return redirect(url_for('main.index'))
        return render_template('auth/admin.html', title='Admin', form=form)
    elif current_user.is_authenticated and current_user.id == 1:
        users = User.query.all()
        admid_user, member_user = users

        if form.validate_on_submit():
            admid_user.username = form.admin_username.data
            if form.admin_password.data != '':
                admid_user.set_password(form.admin_password.data)

            member_user.username = form.member_username.data
            if form.member_password.data != '':
                member_user.set_password(form.member_password.data)
            db.session.commit()

            flash('Congratulations, edited users info successfully!')
            return redirect(url_for('main.index'))
        form.admin_username.data = admid_user.username
        form.member_username.data = member_user.username
        return render_template('auth/admin.html', title='Admin', form=form)
    else:
        abort(403)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
