import pytest
from rockpack.mainsite import app

skip_if_dolly = pytest.mark.skipif(app.config.get('DOLLY', False) == True, reason='Incompatible Dolly test')
skip_if_rockpack = pytest.mark.skipif(app.config.get('DOLLY', False) == False, reason='Incompatible Rockpack test')


def skip_unless_config(k):
    return pytest.mark.skipif(not app.config.get(k), reason='%s not defined' % k)
