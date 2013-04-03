import time
import random
import uuid
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def _run(self):
        """
        - Register new user
        - Search for videos
        - Choose 10 at random and record select activity
        - Get cover art
        - Create new channel
        - Add the 10 videos to new channel
        """
        self.register_user()
        params = dict(start=random.randint(0, 1000), size=100)
        videos = self.get(self.urls['video_search'], params=params)['videos']['items']
        instance_ids = [v['id'] for v in random.sample(videos, 10)]

        for instance_id in instance_ids:
            self.post(self.urls['activity'],
                      dict(action='select', video_instance=instance_id),
                      token=self.token)
            time.sleep(random.random())

        category = random.choice(self.get_cat_ids())
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
    trans = Transaction()
    trans.run()
    trans.print_times()
