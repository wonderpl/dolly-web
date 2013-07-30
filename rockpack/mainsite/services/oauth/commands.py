from sqlalchemy import func
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from .models import ExternalToken, ExternalFriend


@manager.command
def refresh_all_facebook_friends():
    """Populate the external_friend table with facebook friend data."""
    tokens = ExternalToken.query.filter(
        (ExternalToken.external_system == 'facebook') &
        (ExternalToken.expires > func.now()) &
        (ExternalToken.external_token != 'xxx'))
    app.logger.info('Updating friends for %d users', tokens.count())
    for user, in tokens.values(ExternalToken.user):
        try:
            ExternalFriend.populate_facebook_friends(user)
        except:
            app.logger.exception('Failed to update friends for %s', user)
        else:
            app.logger.debug('Updated friends for %s', user)
