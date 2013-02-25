import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class TestCommand_(TestCommand):
    def finalize_options(self):
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.test_args))


def get_git_version():
    from subprocess import check_output
    return check_output(('git', 'describe', '--match', '[0-9].*')).strip()

setup(
    name="rockpack-mainsite",
    version=get_git_version(),
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
    tests_require=['pytest'],
    cmdclass={
        'test': TestCommand_,
    },
)
