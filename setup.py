import sys
import os
import glob
from distutils.cmd import Command
from distutils.command.build import build
from setuptools.command.install import install
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class TestCommand_(TestCommand):
    def finalize_options(self):
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.test_args))


class build_static_assets(Command):
    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_dir'))

    def run(self):
        sys.path.insert(0, self.build_dir)
        from rockpack.mainsite.manager import run
        status = run(*'assets --parse-templates build --production --no-cache'.split())
        sys.path.remove(self.build_dir)
        if status:
            sys.exit(status)
build.sub_commands.append(('build_static_assets', None))


class install_static_assets(Command):
    def initialize_options(self):
        self.install_dir = None

    def finalize_options(self):
        self.set_undefined_options('install_lib', ('install_dir', 'install_dir'))

    def run(self):
        staticfile = lambda f: os.path.join(self.install_dir, 'rockpack/mainsite/static', f)
        self.outfiles = [staticfile('.webassets-manifest')] + glob.glob(staticfile('gen/*'))

    def get_outputs(self):
        return self.outfiles
install.sub_commands.append(('install_static_assets', None))


def get_git_version():
    from subprocess import check_output
    return check_output(('git', 'describe', '--match', '[0-9].*')).strip()


def parse_requirements(filename):
    with open(filename) as f:
        for line in f:
            if not line.startswith('git+'):
                yield line.strip()


name = 'rockpack-mainsite'

setup(
    name=name,
    version=get_git_version(),
    author="Wonder Pl",
    author_email="developers@rockpack.com",
    description="Flask app for Rockpack & Wonder web services and content admin",
    long_description=open('README.md').read(),
    license="Copyright 2014 Wonder Place Ltd",
    url="http://dev.rockpack.com/",
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    data_files=[
        ('/etc/rockpack/mainsite', ['uwsgi.ini']),
        ('/etc/rc.d/init.d', [name]),
        ('share/rockpack/mainsite', ['alembic.ini']),
    ] + [('share/rockpack/mainsite/' + x[0], map(lambda y: x[0] + '/' + y, x[2]))
                for x in os.walk('alembic')],
    entry_points={
        'console_scripts': ['%s-manage = rockpack.mainsite.manager:run' % name]
    },
    install_requires=list(parse_requirements('requirements.txt')),
    setup_requires=['setuptools_git'],
    tests_require=['pytest'],
    cmdclass={
        'build_static_assets': build_static_assets,
        'install_static_assets': install_static_assets,
        'test': TestCommand_,
    },
)
