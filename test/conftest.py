def pytest_configure(config):
    from rockpack.mainsite import app, init_app

    app.config['DATABASE_URL'] = 'sqlite://'

    # Seems to be required for sub-transaction support:
    from rockpack.mainsite.core import dbapi
    dbapi.db.engine.raw_connection().connection.isolation_level = None

    dbapi.sync_database()

    from test.test_helpers import install_mocks
    from test.fixtures import install, all_data
    install_mocks()
    init_app()
    install(*all_data)
