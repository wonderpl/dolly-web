import urllib
from test.base import RockPackTestCase
from rockpack.mainsite.services.video import models

class TestAdminChannel(RockPackTestCase):

    def test_post_video(self):
        data = {'title': 'The Amazing Spider-Man',
                'owner': 'abcdefg'}
        r = self.app.post('/admin/channel/new/?{}'.format(urllib.urlencode(data)))
        q = self.session.query(models.Channel).filter_by(**data)

        self.assertEquals(q.count(), 1, 'a channel record should be recorded')
