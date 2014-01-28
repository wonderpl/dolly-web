from flask import json
from mock import patch
from test import base
from ..test_helpers import get_auth_header


class TestBaseServices(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.base.api.send_email')
    def test_feedback(self, send_email):
        with self.app.test_client() as client:
            user = self.create_test_user()
            message = 'testing 1 2 3'
            r = client.post(
                '/ws/feedback/',
                data=json.dumps(dict(message=message, score=3)),
                content_type='application/json',
                headers=[get_auth_header(user.id)],
            )
            self.assertEquals(r.status_code, 204)

            self.assertEquals(send_email.call_count, 1)
            recipient, body = send_email.call_args[0]
            self.assertEquals(recipient, self.app.config['FEEDBACK_RECIPIENT'])
            self.assertIn(message, body)
