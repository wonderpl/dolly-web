def pytest_configure(config):
    from rockpack.mainsite.core.es import mappings
    mappings.CHANNEL_INDEX = 'test_channels'
    mappings.VIDEO_INDEX = 'test_videos'
    mappings.USER_INDEX = 'test_users'

    from rockpack.mainsite import app, init_app

    app.config['FORCE_INDEX_INSERT_REFRESH'] = True
    app.config['DATABASE_URL'] = app.config.get('TEST_DATABASE_URL', 'sqlite://')

    # import after setting DATABASE_URL
    from rockpack.mainsite.core import dbapi

    if app.config.get('ELASTICSEARCH_URL'):
        from rockpack.mainsite.core.es import helpers

        i = helpers.Indexing()
        i.create_all_indexes(rebuild=True)
        i.create_all_mappings()

    if 'sqlite:' in app.config['DATABASE_URL']:
        # Seems to be required for sub-transaction support:
        dbapi.db.engine.raw_connection().connection.isolation_level = None
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
        i = helpers.Indexing()
        i.delete_index('channel')
        i.delete_index('video')
        i.delete_index('user')
