from test import base
from flask import json

class MoodService(base.RockPackTestCase):

    def test_moods(self):
        with self.app.test_client() as client:
            r = client.get('/ws/moods/',
                content_type='application/json')

            moods = json.loads(r.data)['moods']['items']
            self.assertIn(dict(id=u'1', name=u'Indifferent'), moods)
            self.assertIn(dict(id=u'2', name=u'Misanthropic'), moods)
