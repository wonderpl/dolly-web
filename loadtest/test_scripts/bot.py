import time
import random
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def __init__(self):
        super(Transaction, self).__init__()
        # prevent service discovery request
        self.urls = dict(status=True)

    def process(self):
        """
        - Get status
        """
        self.get('http://lb.us.rockpack.com/status/')
        time.sleep(random.random() / 3)


if __name__ == '__main__':
    Transaction().test()
