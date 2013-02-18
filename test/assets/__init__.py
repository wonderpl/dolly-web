import os

AVATAR_IMG_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'avatar-392x530.jpg')

AVATAR_IMG_DATA = open(AVATAR_IMG_PATH).read()
