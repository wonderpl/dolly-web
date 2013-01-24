import os
from test.base import RockPackTestCase
from rockpack.mainsite.core import imaging


PATH_TO_TEST_IMAGE = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../assets/avatar-392x530.jpg')


class TestFileResize(RockPackTestCase):

    def test_resize_invalid(self):
        with self.assertRaises(imaging.Resizer.ConfigurationInvalid):
            imaging.Resizer({})

        with self.assertRaises(imaging.Resizer.FileDoesNotExist):
            i = imaging.Resizer({1:1})
            i.path_to_image('/tmp/dysufdysdufsdyufsduiYOUSUCK')


    def test_resize_image(self):
        config = self.app.config['AVATAR_IMAGES']
        cu = imaging.Resizer(config)
        cu.path_to_image(PATH_TO_TEST_IMAGE)
        converted_images = cu.resize()

        for name, img in converted_images.iteritems():
            self.assertEquals(name, 'avatar', 'returned images key should match')
            self.assertEquals(img.size,
                    config['avatar'],
                    'background image should be resized to config dimensions')
            #import tempfile
            #f = tempfile.NamedTemporaryFile(delete=False)
            #img.save(f.name, 'JPEG', quality=100)
            #f.close()
