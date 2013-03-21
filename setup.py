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
        run(*'assets --parse-templates build --production --no-cache'.split())
        sys.path.remove(self.build_dir)
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
        'build_static_assets': build_static_assets,
        'install_static_assets': install_static_assets,
        'test': TestCommand_,
    },
)
