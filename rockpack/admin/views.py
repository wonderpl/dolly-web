from flask.ext.admin import BaseView
from flask.ext.admin import expose

class PermissionView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')
