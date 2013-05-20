import os
import random
from base_user import BaseTransaction


terms = open(os.path.join(os.path.dirname(__file__), 'terms.txt')).read().split('\n')


class Transaction(BaseTransaction):

    def process(self):
        """
        - Select random category name as search term
        - Search for videos with that term
        - Page through results, up to max 10 pages
        """
        term = random.choice(terms)
        for page_count in xrange(random.randint(1, 10)):
            params = dict(q=term, start=page_count * 100, size=100)
            channels = self.get(self.urls['channel_search'], params=params)
            for channel in channels[:random.randint(0, min(10, len(channels)))]:
                videos = self.get(channel['resource_url'])['videos']['items']
                for video in videos[:random.randint(0, min(10, len(videos)))]:
                    self.post(self.urls['activity'],
                              dict(action='view', video_instance=video['id']),
                              token=self.token)
                    yield True

            if channels['channels']['total'] < (page_count + 1) * 100:
                break


if __name__ == '__main__':
    Transaction().test()
