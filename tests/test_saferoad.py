import unittest
from src.saferoad.saferoad import SafeRoad, PsData, Road
import os


class TestSafeRoad(unittest.TestCase):
    def setUp(self):
        # Setup the test data
        self.computational_crs = "EPSG:28992"
        self.road = Road(
            filepath="./examples/fixtures/A10_ams.geojson",
            crs_code="EPSG:4326",
            name="road",
        )
        self.ps_data = PsData(
            filepath="./examples/fixtures/psdata_mod.csv",
            latitude="pnt_lat",
            longitude="pnt_lon",
            unit="m",
            crs_code="EPSG:4326",
            name="pspoint",
        )
        self.saferoad = SafeRoad(
            road=self.road,
            ps_data=self.ps_data,
            computational_crs=self.computational_crs,
        )

    def test_initialization(self):
        # Test initialization of SafeRoad
        self.assertEqual(
            self.saferoad.road_data.filepath, "./examples/fixtures/A10_ams.geojson"
        )
        self.assertEqual(
            self.saferoad.ps_data.filepath, "./examples/fixtures/psdata_mod.csv"
        )
        self.assertEqual(self.saferoad.computational_crs, "EPSG:28992")

    def test_load_files(self):
        # Test loading files
        try:
            self.saferoad.load_files()
        except Exception as e:
            self.fail(f"load_files raised an exception: {e}")

    def test_preprocess(self):
        # Test preprocessing
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
        except Exception as e:
            self.fail(f"preprocess raised an exception: {e}")

    def test_generate_rectangles(self):
        # Test generating rectangles
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
            self.saferoad.generate_rectangles(road_width=8, segment_length=500)
        except Exception as e:
            self.fail(f"generate_rectangles raised an exception: {e}")

    def test_run_analysis(self):
        # Test running analysis
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
            self.saferoad.generate_rectangles(road_width=8, segment_length=500)
            self.saferoad.run_analysis()
        except Exception as e:
            self.fail(f"run_analysis raised an exception: {e}")

    def test_generate_report(self):
        # Test generating report
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
            self.saferoad.generate_rectangles(road_width=8, segment_length=500)
            self.saferoad.run_analysis()
            self.saferoad.generate_report("./test_report2.pdf")
        except Exception as e:
            self.fail(f"generate_report raised an exception: {e}")

    def test_scaling_factor(self):
        # Test the _scaling_factor_ property
        self.ps_data.unit = "m"
        self.assertEqual(self.saferoad._scaling_factor_, 1000)

        self.ps_data.unit = "cm"
        self.assertEqual(self.saferoad._scaling_factor_, 10)

        self.ps_data.unit = "mm"
        self.assertEqual(self.saferoad._scaling_factor_, 1)

    def test_invalid_initialization(self):
        # Test initialization with invalid inputs
        with self.assertRaises(AssertionError):
            SafeRoad(
                road="not_a_road",
                ps_data=self.ps_data,
                computational_crs=self.computational_crs,
            )
        with self.assertRaises(AssertionError):
            SafeRoad(
                road=self.road,
                ps_data="not_ps_data",
                computational_crs=self.computational_crs,
            )
        with self.assertRaises(AssertionError):
            SafeRoad(road=self.road, ps_data=self.ps_data, computational_crs=123)

    def test_generate_rectangles_different_values(self):
        # Test generating rectangles with different values
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
            # Test with smaller values
            self.saferoad.generate_rectangles(road_width=5, segment_length=250)
            # Test with larger values
            self.saferoad.generate_rectangles(road_width=10, segment_length=1000)
        except Exception as e:
            self.fail(
                f"generate_rectangles with different values raised an exception: {e}"
            )

    def test_ps_data_validation(self):
        # Test PsData validation
        with self.assertRaises(AssertionError):
            PsData(filepath="", latitude="lat", longitude="lon")  # Empty filepath
        with self.assertRaises(AssertionError):
            PsData(filepath="test.csv", latitude="", longitude="lon")  # Empty latitude
        with self.assertRaises(AssertionError):
            PsData(filepath="test.csv", latitude="lat", longitude="")  # Empty longitude
        with self.assertRaises(AssertionError):
            PsData(
                filepath="test.csv",
                latitude="lat",
                longitude="lon",
                unit="invalid",
            )  # Invalid unit

    def test_road_validation(self):
        # Test Road validation
        with self.assertRaises(AssertionError):
            Road(filepath="", name="road")  # Empty filepath
        with self.assertRaises(AssertionError):
            Road(filepath=123, name="road")  # Non-string filepath
        with self.assertRaises(AssertionError):
            Road(filepath="test.geojson", name="")  # Empty name

    def test_generate_report_custom_output(self):
        # Test generating report with custom output path
        try:
            self.saferoad.load_files()
            self.saferoad.preprocess()
            self.saferoad.generate_rectangles(road_width=8, segment_length=500)
            self.saferoad.run_analysis()
            self.saferoad.generate_report("./custom_report_output.pdf")
        except Exception as e:
            self.fail(f"generate_report with custom output raised an exception: {e}")

        def test_render_ts_plots_workers(self):
            """Test that time series plots are correctly rendered in the report."""

            # First, load files and run necessary preprocessing
            self.saferoad.load_files()
            self.saferoad.preprocess()
            self.saferoad.generate_rectangles(road_width=8, segment_length=500)
            self.saferoad.run_analysis()

            # Generate a report
            report_path = "./test_ts_plots_report.pdf"
            try:
                self.saferoad.generate_report(report_path)

                # Check if the report file exists
                self.assertTrue(os.path.exists(report_path))

                # Check file size to ensure it contains plots (a PDF with time series plots
                # should be reasonably large)
                file_size = os.path.getsize(report_path)
                self.assertGreater(
                    file_size, 10000
                )  # A reasonable minimum size for a PDF with plots

            finally:
                # Clean up the test file
                if os.path.exists(report_path):
                    os.remove(report_path)


if __name__ == "__main__":
    unittest.main()
