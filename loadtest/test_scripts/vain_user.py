from base_user import BaseTransaction


AVATAR_IMG = 'rockpack/mainsite/static/assets/front/images/icon_large.png'
COVER_IMG = 'rockpack/mainsite/static/assets/front/images/top.jpg'


class Transaction(BaseTransaction):

    def process(self):
        """
        - Register new user
        - Upload avatar image
        - Upload a channel cover
        """
        self.register_user()

        yield True
        with open(AVATAR_IMG) as f:
            self.request(
                self.urls['user'] + 'avatar/',
                'put',
                {},
                f.read(),
                [('Content-Type', 'image/png')],
                self.token
            )

        yield True
        with open(COVER_IMG) as f:
            self.request(
                self.urls['user'] + 'cover_art/',
                'post',
                {},
                f.read(),
                [('Content-Type', 'image/jpeg')],
                self.token
            )


if __name__ == '__main__':
    Transaction().test()
