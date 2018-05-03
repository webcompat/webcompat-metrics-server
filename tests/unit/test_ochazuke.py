import unittest

import ochazuke


class OchazukeTestCase(unittest.TestCase):
    """General Test Cases for views."""

    def setUp(self):
        """Set up tests."""
        self.app = ochazuke.app.test_client()

    def test_index(self):
        """Test the index page."""
        rv = self.app.get('/')
        self.assertIn('Welcome to ochazuke', rv.data.decode())


if __name__ == '__main__':
    unittest.main()
