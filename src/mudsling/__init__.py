import pkg_resources

#: :type: mudsling.core.MUDSling
game = None

version = pkg_resources.get_distribution(__name__).version
