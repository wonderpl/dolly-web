def pytest_configure(config):
    from rockpack.mainsite.core.es import mappings
    mappings.CHANNEL_ALIAS = mappings.CHANNEL_INDEX = 'test_channel'
    mappings.VIDEO_ALIAS = mappings.VIDEO_INDEX = 'test_video'
    mappings.USER_ALIAS = mappings.USER_INDEX = 'test_user'

    from rockpack.mainsite import app, init_app

    app.config['FORCE_INDEX_INSERT_REFRESH'] = True
    app.config['DATABASE_URL'] = app.config.get('TEST_DATABASE_URL', 'sqlite://')

    # import after setting DATABASE_URL
    from rockpack.mainsite.core import dbapi

    if app.config.get('ELASTICSEARCH_URL'):
        from rockpack.mainsite.core.es import helpers

        helpers.Indexing.create_all_indexes(rebuild=True)
        helpers.Indexing.create_all_mappings()

    if 'sqlite:' in app.config['DATABASE_URL']:
        connection = dbapi.db.engine.raw_connection().connection
        # Seems to be required for sub-transaction support:
        connection.isolation_level = None
        # For compatibility with postgres:
        from datetime import datetime
        connection.create_function(
            'age', 1, lambda d: datetime.today() - datetime.strptime(d, '%Y-%m-%d'))
        # substitute postgres-specific "interval" expression
        from rockpack.mainsite.services.user import api
        from sqlalchemy import text
        api.SUBSCRIPTION_VIDEO_FEED_THRESHOLD = text("datetime('now')")

    dbapi.sync_database(drop_all=True)

    from test.test_helpers import install_mocks
    from test.fixtures import install, all_data
    install_mocks()
    init_app()
    # Explicityly load admin tables after app is loaded.
    dbapi.sync_database(custom_modules=('rockpack.mainsite.admin', 'rockpack.mainsite.admin.auth', ))
    install(*all_data)


def pytest_unconfigure(config):
    from rockpack.mainsite import app
    if app.config.get('ELASTICSEARCH_URL'):
        from rockpack.mainsite.core.es import helpers
        helpers.Indexing.delete_indices_for('test_channel')
        helpers.Indexing.delete_indices_for('test_video')
        helpers.Indexing.delete_indices_for('test_user')
