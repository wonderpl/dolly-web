import time
import random
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def _run(self):
        """
        - Register new user
        - Pick up to 10 random categories
        - Get popular channels for each
        - Get channel data for up to first 10
        - Record "view" action on up to 10 videos from channel
        - Sleep up to 1s between each action
        """
        self.register_user()
        for cat_id in random.sample(self.get_cat_ids(), random.randint(1, 10)):
            channels = self.get(self.urls['popular_channels'], dict(category=cat_id))['channels']['items']
            for channel in channels[:random.randint(0, min(10, len(channels)))]:
                videos = self.get(channel['resource_url'])['videos']['items']
                for video in videos[:random.randint(0, min(10, len(videos)))]:
                    self.post(self.urls['activity'],
                              dict(action='view', video_instance=video['id']),
                              token=self.token)
                    time.sleep(random.random())


if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    trans.print_times()
