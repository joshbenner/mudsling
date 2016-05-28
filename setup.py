from setuptools import setup, find_packages

setup(
    name='MUDSling',
    description='MUD Game Server',
    url='https://bitbucket.org/joshbenner/mudsling',
    author='Josh Benner',
    author_email='josh@bennerweb.com',
    license='MIT',

    entry_points={
        'console_scripts': [
            'mudsling = mudsling.runner:run'
        ],
        'mudsling.plugin': [
            # Default plugins.
            'DefaultLoginScreen = DefaultLoginScreen:DefaultLoginScreen',
            'SimpleTelnetServer = SimpleTelnetServer:SimpleTelnetServer',
            'mudslingcore = mudslingcore:MUDSlingCorePlugin',

            # Optional plugins.
            'dice = dice.diceplugin:DicePlugin',
            'furniture = furniture.furniture_plugin:FurniturePlugin',
            'icmoney = icmoney.icmoney_plugin:MoneyPlugin',
            'ictime = ictime.ictime_plugin:ICTimePlugin',
            'myobjs = myobjs.myobjs_plugin:MyObjsPlugin',
            'organizations = organizations.organizations_plugin.OrganizationsPlugin',
            'restserver = restserver.restserver_plugin:RESTServerPlugin',
            'wearables = wearables.wearables_plugin:WearablesPlugin',

            # Dev/debug -- not usually available.
            # 'captest = captest.captest_plugin:CaptestPlugin',
        ]
    },

    packages=find_packages('src'),
    package_dir={'': 'src'},

    include_package_data=True,

    use_scm_version=True,
    setup_requires=['setuptools_scm'],

    install_requires=[
        'schematics',
        'sqlalchemy',
        'Cython',
        'unqlite',
        'pyparsing>=1.5',
        'twisted>=12',
        'markdown>=2.2',
        'psutil>=0.6',
        'inflect>=0.2',
        'fuzzywuzzy>=0.1',
        'pytz',
        'flufl.enum>=4',
        'python-dateutil>=2.1',
        'parsedatetime',
        'yoyo-migrations>=4.2.2,<5.0',
        'pint==0.5.2',
        'mailer',
        'simple-pbkdf2',
        'corepost',
        'lupa',
        'pygments',
        # jsonpath-rw<=1.4.0 lacks update() patch, which breaks
        # mudsling.utils.json.JSONMappable.to_json().
        # See: https://github.com/kennknowles/python-jsonpath-rw/pull/28
        'jsonpath-rw',
    ],
    extras_require={
        'dev': ['behave'],
    }
)
