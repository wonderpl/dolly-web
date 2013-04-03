import time
import random
from base_user import BaseTransaction


class Transaction(BaseTransaction):

    def _run(self):
        """
        - Get status
        """
        self.get('http://lb.us.rockpack.com/status/')
        time.sleep(random.random() / 3)


if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    trans.print_times()
