from test.base import RockPackTestCase
from rockpack.mainsite.services.video import models


class TestAdminChannel(RockPackTestCase):

    def test_post_video(self):
        # needs auth workaround
        return
        data = {'title': 'The Amazing Spider-Man',
                'owner': 'abcdefg'}
        r = self.client.post('/admin/channel/new/', data=data)
        self.assertEquals(r.status_code, 200)
        q = self.session.query(models.Channel).filter_by(**data)

        self.assertEquals(q.count(), 1, 'a channel record should be recorded')
