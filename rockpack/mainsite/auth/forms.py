
from flask.ext.wtf import Form, TextField, Required, ValidationError
from user import User

class LoginForm(Form):
    login = TextField('Username', validators=[Required()])

    def validate_login(self, field):
        self.get_user()

        if self.login.data != 'neebone':
            raise ValidationError('Invalid string')

    def get_user(self):
        return User.get_from_login(self.login.data)
