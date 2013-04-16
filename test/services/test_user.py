import json

from test import base
from test.test_helpers import get_auth_header
from rockpack.mainsite.services.user.models import User


class TestProfileEdit(base.RockPackTestCase):

    def test_change_username(self):
        with self.app.test_client() as client:
            existing_user = self.create_test_user()

            new_user = self.create_test_user()
            r = client.put('/ws/{}/username/'.format(new_user.id),
                    data=json.dumps(existing_user.username),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

            data = json.loads(r.data)
            self.assertEquals(r.status_code, 400)
            self.assertEquals(['"{}" already taken.'.format(existing_user.username)], data['message'])
            assert 'suggested_username' in data

            r = client.put('/ws/{}/username/'.format(new_user.id),
                    data=json.dumps('lemonademan'),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

            self.assertEquals(r.status_code, 204)

    def test_other_fields(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            field_map = {"first_name": 'James',
                    "last_name": 'Hong',
                    "email": 'bigtrouble@littlechina.com',
                    "password": {'old': 'password', 'new': 'lopanisgod'},
                    "locale": 'en-us',
                    "gender": "m",
                    "date_of_birth": '1901-01-01'}

            for field, value in field_map.iteritems():
                r = client.put('/ws/{}/{}/'.format(new_user.id, field),
                        data=json.dumps(value),
                        content_type='application/json',
                        headers=[get_auth_header(new_user.id)])

                self.assertEquals(r.status_code, 204, "{} - {}".format(field, r.data))

            user = User.query.get(new_user.id)
            self.assertEquals(user.check_password(field_map['password']['new']), True)
            self.assertEquals(field_map['locale'], user.locale)
            self.assertEquals(field_map['email'], user.email)
            self.assertEquals(field_map['gender'], user.gender)
            self.assertEquals(field_map['last_name'], user.last_name)
            self.assertEquals(field_map['first_name'], user.first_name)
            self.assertEquals(field_map['date_of_birth'], user.date_of_birth.strftime("%Y-%m-%d"))
