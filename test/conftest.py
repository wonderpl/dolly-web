def pytest_configure(config):
    from rockpack.mainsite import app, init_app

    if app.config.get('ELASTICSEARCH_URL'):
        from rockpack.mainsite.core.es import mappings, helpers

        mappings.CHANNEL_INDEX = 'test_channels'
        mappings.VIDEO_INDEX = 'test_videos'
        mappings.USER_INDEX = 'test_users'

        i = helpers.Indexing()
        i.create_all_indexes(rebuild=True)
        i.create_all_mappings()

    app.config['DATABASE_URL'] = 'sqlite://'
    app.config['FORCE_INDEX_INSERT_REFRESH'] = True

    # Seems to be required for sub-transaction support:
    from rockpack.mainsite.core import dbapi
    dbapi.db.engine.raw_connection().connection.isolation_level = None

    dbapi.sync_database()

    from test.test_helpers import install_mocks
    from test.fixtures import install, all_data
    install_mocks()
    init_app()
    install(*all_data)


def pytest_unconfigure(config):
    from rockpack.mainsite import app
    if app.config.get('ELASTICSEARCH_URL'):
        from rockpack.mainsite.core.es import helpers
        i = helpers.Indexing()
        i.delete_index('channel')
        i.delete_index('video')
        i.delete_index('user')
