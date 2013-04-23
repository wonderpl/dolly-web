import random
import uuid
import string
import simplejson as json
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def process(self):
        """
        - Select random category name as search term
        - Search for videos with that term
        - Page through results, up to max 10 pages
        """
        term = random.choice(self.get_categories('name'))
        for page_count in xrange(random.randint(1, 10)):
            params = dict(q=term, start=page_count * 100, size=100)
            response = self.get(self.urls['video_search'], params=params)
            yield True
            if response['videos']['total'] < (page_count + 1) * 100:
                break


if __name__ == '__main__':
    Transaction().test()
