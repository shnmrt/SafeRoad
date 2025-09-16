import os
import duckdb
from pathlib import Path
from datetime import datetime


class DataBase:
    """Class for managing a DuckDB database connection.

    This class provides methods to set up a DuckDB database connection, and run SQL queries.
    """

    def __init__(self):
        self.connection = None
        self.db_path = None

    def setup(self):
        """Setup the DuckDB database connection.
        This method initializes the database path and establishes a connection
        to the DuckDB database. It also loads the spatial extension if available.

        :raises AssertionError: If the database connection or path is already established.
        """
        assert self.connection is None, "Database connection already established."
        assert self.db_path is None, "Database path already initialized."

        self.db_path = self.init_database_path()
        self.connection = duckdb.connect(self.db_path)
        # Load the spatial extension if available
        self.connection.install_extension("spatial")
        self.connection.load_extension("spatial")

    def init_database_path(self):
        """Initialize the database path.

        This method creates a directory for the database if it does not exist
        and generates a filename based on the current date and time.

        :return: The path to the DuckDB database file.
        :rtype: str
        """
        assert self.connection is None, "Database connection already established."
        assert self.db_path is None, "Database path already initialized."

        # Create a folder for the database if it does not exist
        dbFolder = "SafeRoadDB"
        os.makedirs(dbFolder, exist_ok=True)
        filename = os.path.join(
            dbFolder, f"{datetime.now().strftime('%Y%m%d%H%M')}.duckdb"
        )
        return filename

    def run(self, query: str):
        """Run a SQL query on the database.

        This method executes the provided SQL query on the connected database.

        :param query: The SQL query to execute.
        :type query: str
        :raises AssertionError: If the database connection is not established.
        """
        if self.connection is None:
            raise AssertionError("Database connection is not established.")

        self.connection.execute(query)
