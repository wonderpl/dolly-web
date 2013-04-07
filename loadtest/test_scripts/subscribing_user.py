import random
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def get_subs_videos(self):
        self.get(self.urls['subscriptions'] + 'recent_videos/', token=self.token)

    def process(self):
        """
        - Register new user
        - Pick 10 random categories
        - Subscribe to random channel for each category
        - Get recent videos for subscriptions 10 times
        """
        self.register_user()
        for cat_id in random.sample(self.get_cat_ids(), 10):
            channels = self.get(self.urls['popular_channels'], dict(category=cat_id))['channels']['items']
            if not channels:
                continue
            channel = random.choice(channels)
            self.post(self.urls['subscriptions'], channel['resource_url'], token=self.token)
            self.get_subs_videos()
            yield True
        for i in xrange(10):
            self.get_subs_videos()
            yield True


if __name__ == '__main__':
    Transaction().test()
