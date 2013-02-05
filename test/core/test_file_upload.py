import os
from test.base import RockPackTestCase

from rockpack.mainsite import app
from rockpack.mainsite.core import imaging
from rockpack.mainsite.core import s3


PATH_TO_TEST_IMAGE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '../assets/avatar-392x530.jpg')


class TestImageResize(RockPackTestCase):

    def setUp(self):
        super(TestImageResize, self).setUp()
        app.config['TEST_S3_UPLOAD'] = True

    def tearDOwn(self):
        super(TestImageResize, self).tearDown()
        app.config['TEST_S3_UPLOAD'] = False

    def test_resize_invalid(self):
        with self.assertRaises(imaging.Resizer.ConfigurationInvalid):
            imaging.Resizer({})

        with self.assertRaises(imaging.Resizer.FileDoesNotExist):
            i = imaging.Resizer({1: 1})
            i.path_to_image('/tmp/dysufdysdufsdyufsduiYOUSUCK')

    def test_resize_image(self):
        config = self.app.config['AVATAR_IMAGES']
        cu = imaging.Resizer(config)
        cu.path_to_image(PATH_TO_TEST_IMAGE)
        converted_images = cu.resize()

        for name, img in converted_images.iteritems():
            self.assertIn(name, config, 'returned images key should match')
            self.assertEquals(img.size,
                config[name],
                'background image should be resized to config dimensions')


class TestFileUpload(RockPackTestCase):

    def setUp(self):
        super(TestFileUpload, self).setUp()
        app.config['TEST_S3_UPLOAD'] = True

    def tearDOwn(self):
        super(TestFileUpload, self).tearDown()
        app.config['TEST_S3_UPLOAD'] = False

    def test_put_file(self):
        with self.app.test_request_context():
            up = s3.S3Uploader()
            path_to_file, remote_name = PATH_TO_TEST_IMAGE.rsplit('/', 1)
            up.put_from_filename(PATH_TO_TEST_IMAGE, 'test_images/' + remote_name)

            self.assertTrue(up.exists('test_images/' + remote_name))
            self.assertFalse(up.exists('this_is_a_false_check_fjdfdsjkhjhu'))

    def test_failed_put(self):
        with self.app.test_request_context():
            with self.assertRaises(IOError):
                up = s3.S3Uploader()
                up.put_from_filename('/sddsdsadalitesties', 'foofoofoofootesties')
