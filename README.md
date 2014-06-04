Flask app for rockpack web services and content admin.

Development
-----------

Run dev server with:

    python2.7 manage.py runserver

### Step-by-step env setup

0. `cd mainsite`
0. `virtualenv --system-site-packages env`	([see virtualenv usage](http://www.virtualenv.org/en/latest/virtualenv.html#usage))
0. `. env/bin/activate`
0. `pip install -r requirements.txt -r requirements-dev.txt`	([see pip usage](http://www.pip-installer.org/en/latest/usage.html#pip-install))
0. Create local configuration file: `echo -e "DEBUG = True\nDATABASE_URL = 'sqlite:///rockpack.db'" >rockpack/mainsite/settings/local.py`
0. `python2.7 manage.py syncdb`
0. `python2.7 manage.py runserver`
0. `curl http://127.0.0.1:5000/ws/`

#### Troubleshooting

Cryptography package installation error: _raise ffiplatform.VerificationError(error)_

Possible fix: http://chriskief.com/2014/03/25/installing-cryptography-via-pip-with-macports-or-homebrew/

    sudo env ARCHFLAGS="-arch x86_64" LDFLAGS="-L/opt/local/lib" CFLAGS="-I/opt/local/include" pip install cryptography

Syncdb Response error: _ImportError: cannot import name Response_

Possible fix: https://github.com/joelverhagen/flask-rauth/issues/4

    easy_install rauth==0.4.17


### Database setup

0. Install & start postgres server (version 9)
0. `sudo -u postgres createdb rockpack`
0. Load db dump from s3: `s3cmd get s3://backup.dev.rockpack.com/postgres/rockpack/2013-09-03T15:42:30.792652.sql.gz - | zcat | psql rockpack`
0. `echo "DATABASE_URL = 'postgresql:///rockpack'" >>rockpack/mainsite/settings/local.py`
0. Update schema: `alembic upgrade head`

0. Install & start ElasticSearch (version 0.90)
0. `echo "ELASTICSEARCH_URL = 'http://localhost:9200'" >>rockpack/mainsite/settings/local.py`
0. `python2.7 manage.py init_es`
0. `python2.7 manage.py import_to_es`	_Warning: will take a while!_

### Using database from dev

0. Create ssh tunnels: `ssh -L 45432:localhost:5432 -L 49200:localhost:9200 -N dev.rockpack.com`
0. Update config: `echo -e "DATABASE_URL = 'postgresql://mainsite:mainsite@localhost:45432/rockpack'\nELASTICSEARCH_URL = 'http://localhost:49200'" >>rockpack/mainsite/settings/local.py`

Test
----

Run unit tests with [pytest](http://pytest.org/latest/usage.html)

    py.test -x

Build
-----

To build rpm:

    python2.7 setup.py rpm
