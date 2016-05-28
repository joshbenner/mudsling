from setuptools import setup, find_packages


packages = find_packages()
packages.extend(find_packages('plugins'))

setup(
    name='MUDSling',
    url='https://bitbucket.org/joshbenner/mudsling',
    license='MIT',
    author='Josh Benner',
    author_email='josh@bennerweb.com',
    description='MUD Game Server',

    packages=packages,
    package_dir={'': 'plugins'},

    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)
