from flask import flash
from flask import redirect
from flask import url_for
from flask import render_template
from flask import session
from flask.ext import login
from flask.ext.rauth import RauthOAuth2

import patching
patching.patch_rauth()

from user import User
from forms import LoginForm

google = RauthOAuth2(
    name='google',
    base_url='https://www.googleapis.com/oauth2/v1/',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    consumer_key='902099289100.apps.googleusercontent.com',
    consumer_secret='ja-jW0BDASKVIwIRFurpCaZi'
    )


def load_user(login_id):
    return User.get_from_login(login_id)

def login_view():
    return google.authorize(
            callback=url_for('.authorised', _external=True),
            scope='https://www.googleapis.com/auth/userinfo.profile')
    """
    form = LoginForm()
    if form.validate_on_submit():
        login.login_user(load_user(form.login.data))
        flash("Logged in successfully.")
        return redirect(url_for('admin.index'))
    return render_template("login.html", form=form)
    """

@google.authorized_handler()
def authorised(response, access_token):
    if response == 'access denied':
        return 'What? You don\'t want to login in with your google account? Booo ...' +\
                '<a href="{}">Login again</a>'.format(url_for('.login_view'))

    # if we have access token, check it against db.
    # if we have a hit, login as user

    user = User.get_from_token(access_token)
    login.login_user(user)
    session['access_token'] = access_token

    # else redirect them to failed login page

    return redirect(url_for('admin.index'))

from flask import make_response

def logout_view():
    login.logout_user()

    # remove any keys
    if session.get('access_token'):
        session.pop('access_token')

    response =  make_response(redirect(url_for('admin.index')))
    response.delete_cookie('access_token')
    return response

