import os
import shutil
import unittest
from src.saferoad.database import DataBase


class TestDataBase(unittest.TestCase):
    def setUp(self):
        self.db = DataBase()

    def tearDown(self):
        if self.db.connection:
            self.db.connection.close()
        # Remove the database file if it exists
        if self.db.db_path and os.path.exists(self.db.db_path):
            os.remove(self.db.db_path)
        # Remove the directory and all its contents if it exists
        if os.path.exists("SafeRoadDB"):
            shutil.rmtree("SafeRoadDB")
            # os.rmdir("SafeRoadDB")

    def test_setup_creates_database_file(self):
        self.db.setup()

        # Check if the database file is created
        self.assertIsNotNone(self.db.db_path)
        self.assertTrue(os.path.exists(self.db.db_path))

    def test_setup_raises_error_if_already_initialized(self):
        self.db.setup()

        with self.assertRaises(AssertionError) as context:
            self.db.setup()
        self.assertIn(
            "Database connection already established.", str(context.exception)
        )

    def test_run_executes_query(self):
        self.db.setup()

        # Create a table and insert data
        self.db.run("CREATE TABLE test_table (id INTEGER, name STRING);")
        self.db.run("INSERT INTO test_table VALUES (1, 'Test Name');")

        # Verify the table exists and data is inserted
        result = self.db.connection.execute("SELECT * FROM test_table;").fetchall()
        self.assertEqual(result, [(1, "Test Name")])

    def test_run_raises_error_if_no_connection(self):
        with self.assertRaises(AssertionError) as context:
            self.db.run("SELECT 1;")
        self.assertIn("Database connection is not established.", str(context.exception))


if __name__ == "__main__":
    unittest.main()
