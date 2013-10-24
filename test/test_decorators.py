import pytest
from rockpack.mainsite import app

skip_if_dolly = pytest.mark.skipif(app.config.get('DOLLY', False) == True, reason='Incompatible Dolly test')
skip_if_rockpack = pytest.mark.skipif(app.config.get('DOLLY', False) == False, reason='Incompatible Rockpack test')
