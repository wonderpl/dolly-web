from flask import flash
from flask import redirect
from flask import url_for
from flask import render_template
from flask.ext import login

from user import User
from forms import LoginForm


def load_user(userid):
    return User.get_from_login(userid)

def login_view():
    form = LoginForm()
    if form.validate_on_submit():
        login.login_user(load_user(form.login.data))
        flash("Logged in successfully.")
        return redirect(url_for('admin.index'))
    return render_template("login.html", form=form)

def logout():
    login.logout_user()

    # remove any keys

    return redirect(url_for('login'))

