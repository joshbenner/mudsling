import os

game = None

version_file = open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'VERSION'))
version = version_file.read().strip()
version_file.close()
del version_file
