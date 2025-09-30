import unittest
from datetime import datetime
from src.saferoad.utils import extract_dates, time_vector, Timer
import io
from contextlib import redirect_stdout
import time


class TestExtractDates(unittest.TestCase):

    def test_valid_dates(self):
        column_names = ["data_20230101", "info_20221231", "value_20220101"]
        expected_names = ["data_20230101", "info_20221231", "value_20220101"]
        expected_dates = [
            datetime(2023, 1, 1).date(),
            datetime(2022, 12, 31).date(),
            datetime(2022, 1, 1).date(),
        ]
        result_names, result_dates = extract_dates(column_names)
        self.assertEqual(result_names, expected_names)
        self.assertEqual(result_dates, expected_dates)

    def test_no_dates(self):
        column_names = ["data", "info", "value"]
        expected_names = []
        expected_dates = []
        result_names, result_dates = extract_dates(column_names)
        self.assertEqual(result_names, expected_names)
        self.assertEqual(result_dates, expected_dates)

    def test_mixed_columns(self):
        column_names = ["data_20230101", "info", "value_20220101"]
        expected_names = ["data_20230101", "value_20220101"]
        expected_dates = [
            datetime(2023, 1, 1).date(),
            datetime(2022, 1, 1).date(),
        ]
        result_names, result_dates = extract_dates(column_names)
        self.assertEqual(result_names, expected_names)
        self.assertEqual(result_dates, expected_dates)

    def test_empty_list(self):
        column_names = []
        with self.assertRaises(AssertionError):
            extract_dates(column_names)

    def test_invalid_input_type(self):
        column_names = "data_20230101"
        with self.assertRaises(AssertionError):
            extract_dates(column_names)

    def test_non_string_elements(self):
        column_names = ["data_20230101", 123, "value_20220101"]
        with self.assertRaises(AssertionError):
            extract_dates(column_names)

    def test_time_vector(self):
        dates = [
            datetime(2022, 1, 1),
            datetime(2022, 1, 2),
            datetime(2022, 1, 10),
            datetime(2022, 1, 20),
        ]
        expected_vector = [0, 1, 9, 19]
        result_vector = time_vector(dates)
        self.assertEqual(list(result_vector), expected_vector)

    def test_time_vector_single_date(self):
        dates = [datetime(2022, 1, 1)]
        expected_vector = [0]
        result_vector = time_vector(dates)
        self.assertEqual(result_vector, expected_vector)

    def test_extract_date_with_list_numbers(self):
        column_names = ["data_20230101", "info_20221231", "value_20220101", 123]
        with self.assertRaises(AssertionError):
            extract_dates(column_names)

    def test_extract_date_with_empty_list(self):
        column_names = []
        with self.assertRaises(AssertionError):
            extract_dates(column_names)


class TestTimer(unittest.TestCase):

    def test_timer_with_name(self):
        """Test that Timer works correctly with a name parameter."""

        # Capture stdout
        f = io.StringIO()
        with redirect_stdout(f):
            with Timer(name="test_timer"):
                time.sleep(0.1)  # Sleep for a short time

        output = f.getvalue()
        self.assertIn("test_timer took", output)
        self.assertRegex(output, r"test_timer took \d+\.\d+ seconds")

    def test_timer_without_name(self):
        """Test that Timer works correctly without a name parameter."""

        # Capture stdout
        f = io.StringIO()
        with redirect_stdout(f):
            with Timer():
                time.sleep(0.1)  # Sleep for a short time

        # No output should be produced when name is None
        output = f.getvalue()
        self.assertEqual(output, "")

    def test_timer_accuracy(self):
        """Test that Timer measures time with reasonable accuracy."""

        sleep_time = 0.2  # seconds
        timer = Timer("accuracy_test")

        # Measure the time manually
        start_time = time.time()
        with redirect_stdout(io.StringIO()):  # Suppress output
            with timer:
                time.sleep(sleep_time)
        end_time = time.time()

        elapsed_time = end_time - start_time
        # Check that the elapsed time is reasonably close to sleep_time
        # Allow for some overhead in timing operations
        self.assertGreaterEqual(elapsed_time, sleep_time)
        self.assertLess(elapsed_time, sleep_time + 0.1)  # Allow 0.1s margin


if __name__ == "__main__":
    unittest.main()
