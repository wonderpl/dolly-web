import random
import uuid
import string
import simplejson as json
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def process(self):
        """
        - Register new user
        - Search for videos
        - Choose 10 at random and record select activity
        - Get cover art
        - Create new channel
        - Add the 10 videos to new channel
        """
        self.register_user()
        r = self.get(self.urls['video_search_terms'], dict(q=random.choice(string.ascii_lowercase)))
        term = random.choice(json.loads(r[19:-1])[1])[0]
        params = dict(q=term, start=random.randint(0, 800), size=100)
        videos = self.get(self.urls['video_search'], params=params)['videos']['items']
        if not videos:
            return
        instance_ids = [v['id'] for v in random.sample(videos, min(10, len(videos)))]

        for instance_id in instance_ids:
            self.post(self.urls['activity'],
                      dict(action='select', video_instance=instance_id),
                      token=self.token)
            #yield True

        category = random.choice(self.get_categories())
        cover = random.choice(self.get(self.urls['cover_art'])['cover_art']['items'])['cover_ref']
        chdata = dict(
            title=uuid.uuid4().hex,
            category=category,
            cover=cover,
            description='test',
            public=True,
        )
        c = self.post(self.urls['channels'], chdata, token=self.token)
        self.put(c['resource_url'] + 'videos/', instance_ids, token=self.token)


if __name__ == '__main__':
    Transaction().test()
