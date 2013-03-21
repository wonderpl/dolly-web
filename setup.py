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

name = 'rockpack-mainsite'

setup(
    name=name,
    version=get_git_version(),
    author="rockpack ltd",
    author_email="developers@rockpack.com",
    description="Flask app for rockpack web services and content admin",
    long_description=open('README.md').read(),
    license="Copyright 2013 Rockpack Ltd",
    url="http://dev.rockpack.com/",
    packages=find_packages(),
    include_package_data=True,
    data_files=[
        ('/etc/rockpack/mainsite', ['uwsgi.ini']),
        ('/etc/init.d', [name])],
    entry_points={
        'console_scripts': ['%s-manage = rockpack.mainsite.manager:run' % name]
    },
    setup_requires=['setuptools_git'],
    tests_require=['pytest'],
    cmdclass={
        'test': TestCommand_,
    },
)
