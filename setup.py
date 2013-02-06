from setuptools import setup, find_packages


setup(
    name="rockpack-mainsite",
    version="20130205",
    author="rockpack ltd",
    author_email="developers@rockpack.com",
    description="Flask app for rockpack web services and content admin",
    long_description=open('README.md').read(),
    license="Copyright 2013 Rockpack Ltd",
    url="http://dev.rockpack.com/",
    packages=find_packages(),
    scripts=['manage.py'],
    include_package_data=True,
    data_files=[
        ('/etc/rockpack/mainsite', ['uwsgi.ini']),
        ('/etc/init.d', ['rockpack-mainsite'])],
    #package_data={'': ['templates/*/*.html', '*.html']},
    setup_requires=['setuptools_git'],
)
