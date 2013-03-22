#!/usr/bin/env python
import os
import sys
import stat

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

try:
    import libxml2
except ImportError:
    sys.exit("libxml2 is missing on your system")

if sys.version_info < (2, 4):
    sys.exit("requires python 2.4 or higher")

if sys.version_info >= (3, 0):
    sys.exit("python 3.x is not supported")

package_name = 'qmemtools'
config_dir = '/etc/qmem'
initd_dir = '/etc/init.d'

setup (
    name = 'QmemTools',
    version = '0.1',
    description='QmemTools is a set of tools to monitor memory usage in an SGE cluster',
    long_description=open('README.rst').read(),
    author='Cedric Clerget',
    author_mail='cedric.clerget@univ-fcomte.fr',
    url='https://github.com/mesocentrefc/qmemtools',
    install_requires=['simplejson>=2.0.9','web.py>=0.34'],
    package_dir = {'': package_name},
    packages = find_packages(package_name, exclude=['config','init.d']),
    data_files=[
        (config_dir, [os.path.join(package_name, 'config', 'qmemserver.conf')]),
        (initd_dir, [os.path.join(package_name, 'init.d', 'qmemserver')])
    ],
    scripts = [os.path.join(package_name, 'qmemserver.py'), os.path.join(package_name, 'qmemview.py')],
    platforms = ['POSIX'],
    use_2to3 = False,
    license='GPL',
    zip_safe = True
)

# setup right permissions on files
config_file = os.path.join(config_dir, 'qmemserver.conf')
initd_file = os.path.join(initd_dir, 'qmemserver')

os.chmod(config_file, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
os.chmod(initd_file, stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
