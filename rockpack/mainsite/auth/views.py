from flask import redirect
from flask import url_for
from flask import session
from flask.ext import login
from flask.ext.rauth import RauthOAuth2

from flask import current_app
from flask import make_response

import patching
patching.patch_rauth()

from user import Admin

google = RauthOAuth2(
    name='google',
    base_url='https://www.googleapis.com/oauth2/v1/',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    consumer_key='902099289100.apps.googleusercontent.com',
    consumer_secret='ja-jW0BDASKVIwIRFurpCaZi'
    )


def load_user(login_id):
    current_app.logger.debug('attempting to fetch user with id {}'.format(login_id))
    return Admin.get_from_login(login_id)


def login_view():
    return google.authorize(
            callback=url_for('.authorised', _external=True),
            scope='https://www.googleapis.com/auth/userinfo.email')


@google.authorized_handler()
def authorised(response, access_token):
    if response == 'access denied' or not access_token:
        return 'Not logging in with Google account' +\
                '<a href="{}">Login again</a>'.format(url_for('.login_view'))

    current_app.logger.debug('loggin in .... checking token')
    user = Admin.get_from_token(access_token)
    if not user:
        current_app.logger.debug('no token found, cross-referencing email against token')
        response = google.get('https://www.googleapis.com/oauth2/v1/userinfo?alt=json', access_token=access_token).response
        if response.status_code != 200:
            current_app.logger.error('Failed to retrieve userinfo with: {}'.format(response.content))
            return 'Error fetching userinfo', 500
        email = response.json().get('email')
        user = Admin.register_token(access_token, email)
        if not user:
            return 'No registered email address found', 401

    login.login_user(user, remember=True)
    session['access_token'] = access_token

    # else redirect them to failed login page

    return redirect(url_for('admin.index'))


def logout_view():
    login.logout_user()

    # remove any keys
    if session.get('access_token'):
        session.pop('access_token')

    response =  make_response(redirect(url_for('admin.index')))
    response.delete_cookie('access_token')
    return response
