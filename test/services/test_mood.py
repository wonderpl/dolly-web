from test import base
from flask import json

class MoodService(base.RockPackTestCase):

    def test_moods(self):
        with self.app.test_client() as client:
            r = client.get('/ws/moods/',
                content_type='application/json')

            moods = json.loads(r.data)['moods']['items']
            self.assertIn(dict(id=u'indifferent', name=u'Indifferent'), moods)
            self.assertIn(dict(id=u'misanthropic', name=u'Misanthropic'), moods)
