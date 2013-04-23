import random
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def process(self):
        """
        - Register new user
        - Pick up to 5 random categories
        - Get popular channels for each
        - Get channel data for up to first 5
        - Record "view" action on up to 5 videos from channel
        - Sleep up to 1s between each action
        """
        self.register_user()
        for cat_id in random.sample(self.get_categories(), random.randint(1, 5)):
            channels = self.get(self.urls['popular_channels'], dict(category=cat_id))['channels']['items']
            for channel in channels[:random.randint(0, min(5, len(channels)))]:
                videos = self.get(channel['resource_url'])['videos']['items']
                for video in videos[:random.randint(0, min(5, len(videos)))]:
                    self.post(self.urls['activity'],
                              dict(action='view', video_instance=video['id']),
                              token=self.token)
                    yield True


if __name__ == '__main__':
    Transaction().test()
