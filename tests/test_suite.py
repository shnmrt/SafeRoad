import unittest


def suite():
    laoder = unittest.TestLoader()
    suite = unittest.TestSuite()

    for module in [
        "test_utils",
        "test_pipeline",
        "test_database",
    ]:
        suite.addTests(laoder.loadTestsFromName(f"tests.{module}"))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
