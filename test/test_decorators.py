import pytest
from mock import patch
from rockpack.mainsite import app

skip_if_dolly = pytest.mark.skipif(app.config.get('DOLLY', False) == True, reason='Incompatible Dolly test')
skip_if_rockpack = pytest.mark.skipif(app.config.get('DOLLY', False) == False, reason='Incompatible Rockpack test')


def skip_unless_config(k):
    return pytest.mark.skipif(not app.config.get(k), reason='%s not defined' % k)


def patch_send_email(target='rockpack.mainsite.core.email.send_email'):
    def decorator(f):
        @patch(target)
        def wrapper(self, send_email):
            result = f(self, send_email)
            if 'TEST_EMAIL_DUMP_PREFIX' in app.config and send_email.call_count:
                (recipient, body), kwargs = send_email.call_args
                type = '.txt' if kwargs.get('format') == 'text' else '.html'
                dump_file = app.config['TEST_EMAIL_DUMP_PREFIX'] + type
                with open(dump_file, 'wb') as file:
                    file.write(body.encode('utf8'))
            return result
        return wrapper
    return decorator
