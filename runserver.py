#!/usr/bin/env python
from rockpack.mainsite.wsgi import application

if __name__ == '__main__':
    application.run(debug=True)
