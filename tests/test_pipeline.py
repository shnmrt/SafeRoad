import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
from saferoad.pipeline import Pipeline


class TestPipelineProcessing(unittest.TestCase):

    def test_load_file(self):
        # Mock Path.exists to always return True
        with patch("pathlib.Path.exists", return_value=True):
            # Test CSV file
            query = Pipeline.Processing.load_file("test.csv", "test_table")
            self.assertIn("read_csv_auto", query)
            self.assertIn("test_table", query)

            # Test non-CSV file
            query = Pipeline.Processing.load_file("test.shp", "test_table")
            self.assertIn("ST_Read", query)
            self.assertIn("test_table", query)

        # Test file not found
        with patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(AssertionError):
                Pipeline.Processing.load_file("nonexistent.csv", "test_table")

    def test_dissolve_features(self):
        # Test with attribute
        query = Pipeline.Processing.dissolve_features("test_attr", "test_table")
        self.assertIn("GROUP BY test_attr", query)
        self.assertIn("test_table", query)

        # Test without attribute
        query = Pipeline.Processing.dissolve_features("", "test_table")
        self.assertNotIn("GROUP BY", query)
        self.assertIn("test_table", query)

    def test_split_to_segments(self):
        query = Pipeline.Processing.split_to_segments(10.0, "test_table")
        self.assertIn("10.0", query)
        self.assertIn("test_table", query)
        self.assertIn("CREATE OR REPLACE TABLE segments", query)

    def test_generate_patches(self):
        # Test with valid parameters
        query = Pipeline.Processing.generate_patches(5.0, 10.0, "test_segments")
        self.assertIn("5.0", query)
        self.assertIn("10.0", query)
        self.assertIn("test_segments", query)

        # Test with invalid width
        with self.assertRaises(AssertionError):
            Pipeline.Processing.generate_patches(0, 10.0)

        # Test with invalid length
        with self.assertRaises(AssertionError):
            Pipeline.Processing.generate_patches(5.0, 0)

    def test_spatial_transformation(self):
        query = Pipeline.Processing.spatial_tranformation(
            "EPSG:4326", "EPSG:3857", "test_table"
        )
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)
        self.assertIn("test_table", query)

    def test_build_geometry(self):
        query = Pipeline.Processing.build_geometry("lat", "lon", "test_table")
        self.assertIn("lat", query)
        self.assertIn("lon", query)
        self.assertIn("test_table", query)
        self.assertIn("ST_Point", query)

    def test_relate_point_patches(self):
        query = Pipeline.Processing.relate_point_patches("test_points", "test_patches")
        self.assertIn("test_points", query)
        self.assertIn("test_patches", query)
        self.assertIn("ST_Within", query)

    def test_calc_point_density(self):
        query = Pipeline.Processing.calc_point_density("test_points", "test_patches")
        self.assertIn("test_points", query)
        self.assertIn("test_patches", query)
        self.assertIn("ps_density", query)

    def test_get_column_names(self):
        query = Pipeline.Processing.get_column_names("test_table")
        self.assertIn("test_table", query)
        self.assertIn("column_name", query)

    def test_calc_cum_disp(self):
        dates = ["date1", "date2", "date3"]
        query = Pipeline.Processing.calc_cum_disp(dates, "test_table")
        self.assertIn("date1", query)
        self.assertIn("date3", query)
        self.assertIn("test_table", query)

    def test_calc_avg_cum_disp(self):
        query = Pipeline.Processing.calc_avg_cum_disp()
        self.assertIn("avg_cum_disp", query)
        self.assertIn("AVG(displacement)", query)

    def test_calc_avg_velocity(self):
        time_vector = [0, 10, 20]
        fields = ["field1", "field2", "field3"]
        query = Pipeline.Processing.calc_avg_velocity(time_vector, fields, "test_table")
        for field in fields:
            self.assertIn(field, query)
        self.assertIn("test_table", query)
        self.assertIn("avg_velocity_gcp", query)

    def test_calc_avg_disp_ts_gcp(self):
        date_fields = ["date1", "date2", "date3"]
        query = Pipeline.Processing.calc_avg_disp_ts_gcp(date_fields)
        for date in date_fields:
            self.assertIn(date, query)
        self.assertIn("avg_disp_ts_gcp", query)

    def test_calc_std_disp_ts_gcp(self):
        date_fields = ["date1", "date2", "date3"]
        query = Pipeline.Processing.calc_std_disp_ts_gcp(date_fields)
        for date in date_fields:
            self.assertIn(date, query)
        self.assertIn("std_disp_ts_gcp", query)

    def test_select_lcps(self):
        query = Pipeline.Processing.select_lcps("test_table")
        self.assertIn("test_table", query)
        self.assertIn("lcp_uid", query)

    def test_calc_lcp_velocity(self):
        query = Pipeline.Processing.calc_lcp_velocity()
        self.assertIn("lcp_velocity", query)
        self.assertIn("avg_velocity_gcp", query)

    def test_calc_avg_velocity_gcp(self):
        query = Pipeline.Processing.calc_avg_velocity_gcp("test_table")
        self.assertIn("test_table", query)
        self.assertIn("avg_gcp_velocity", query)

    def test_calc_avg_std_disp_ts_lcp(self):
        date_fields = ["date1", "date2", "date3"]
        query = Pipeline.Processing.calc_avg_std_disp_ts_lcp(date_fields, "test_table")
        for date in date_fields:
            self.assertIn(date, query)
        self.assertIn("test_table", query)
        self.assertIn("avg_disp_ts_lcp", query)
        self.assertIn("std_disp_ts_lcp", query)

    def test_calc_avg_velocity_lcp(self):
        query = Pipeline.Processing.calc_avg_velocity_lcp("test_table")
        self.assertIn("test_table", query)
        self.assertIn("avg_velocity_lcp", query)

    def test_calc_avg_lcp_velocity(self):
        query = Pipeline.Processing.calc_avg_lcp_velocity("test_table")
        self.assertIn("test_table", query)
        self.assertIn("avg_lcp_velocity", query)

    def test_calc_outliers(self):
        query = Pipeline.Processing.calc_outliers(1000.0, "test_table")
        self.assertIn("test_table", query)
        self.assertIn("outlier_uid", query)
        self.assertIn("1000.0", query)

    def test_lcp_ts_patch(self):
        date_fields = ["date1", "date2", "date3"]
        query = Pipeline.Processing.lcp_ts_patch(date_fields, "test_table")
        for date in date_fields:
            self.assertIn(date, query)
        self.assertIn("test_table", query)
        self.assertIn("lcp_disp_ts", query)

    def test_outlier_ts_patch(self):
        date_fields = ["date1", "date2", "date3"]
        query = Pipeline.Processing.outlier_ts_patch(date_fields, "test_table")
        for date in date_fields:
            self.assertIn(date, query)
        self.assertIn("test_table", query)
        self.assertIn("outlier_disp_ts", query)

    def test_outlier_rel_ts_patch(self):
        query = Pipeline.Processing.outlier_rel_ts_patch()
        self.assertIn("outlier_rel_ts", query)
        self.assertIn("outlier_disp_ts", query)
        self.assertIn("lcp_disp_ts", query)


class TestPipelineVisualisation(unittest.TestCase):

    def test_get_table_bbox(self):
        query = Pipeline.Visualisation.get_table_bbox("test_table", "EPSG:4326")
        self.assertIn("test_table", query)
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection

    def test_get_ps_density(self):
        query = Pipeline.Visualisation.get_ps_density("EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("ps_density", query)

    def test_get_outliers_map(self):
        query = Pipeline.Visualisation.get_outliers_map("EPSG:4326", 1000.0)
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("1000.0", query)
        self.assertIn("avg_velocity_lcp", query)

    def test_get_cum_disp_map(self):
        query = Pipeline.Visualisation.get_cum_disp_map("EPSG:4326", 1000.0)
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("1000.0", query)
        self.assertIn("avg_cum_disp", query)

    def test_get_ps_vel_gcp(self):
        query = Pipeline.Visualisation.get_ps_vel_gcp("EPSG:4326", 1000.0)
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("1000.0", query)
        self.assertIn("avg_velocity_gcp", query)

    def test_get_ps_vel_lcp(self):
        query = Pipeline.Visualisation.get_ps_vel_lcp("EPSG:4326", 1000.0)
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("1000.0", query)
        self.assertIn("avg_velocity_lcp", query)

    def test_get_outlier_zoom(self):
        query = Pipeline.Visualisation.get_outlier_zoom("EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("outlier_uid", query)

    def test_get_ps_points(self):
        query = Pipeline.Visualisation.get_ps_points(123, "EPSG:4326", "test_table")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("test_table", query)
        self.assertIn("123", query)

    def test_get_center(self):
        query = Pipeline.Visualisation.get_center(123, "EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("123", query)
        self.assertIn("ST_Centroid", query)

    def test_get_patch_center(self):
        query = Pipeline.Visualisation.get_patch_center(123, "EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("123", query)
        self.assertIn("ST_Centroid", query)

    def test_get_lcp_point(self):
        query = Pipeline.Visualisation.get_lcp_point(123, "EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("123", query)
        self.assertIn("lcp_uid", query)

    def test_get_outlier_point(self):
        query = Pipeline.Visualisation.get_outlier_point(123, "EPSG:4326")
        self.assertIn("EPSG:4326", query)
        self.assertIn("EPSG:3857", query)  # Default projection
        self.assertIn("123", query)
        self.assertIn("outlier_uid", query)

    def test_get_cum_disp_graph(self):
        query = Pipeline.Visualisation.get_cum_disp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("outlier_disp_ts", query)

    def test_get_avg_cum_disp_graph(self):
        query = Pipeline.Visualisation.get_avg_cum_disp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("avg_disp_ts_gcp", query)

    def test_get_std_cum_disp_graph(self):
        query = Pipeline.Visualisation.get_std_cum_disp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("std_disp_ts_gcp", query)

    def test_get_lcp_disp_graph(self):
        query = Pipeline.Visualisation.get_lcp_disp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("lcp_disp_ts", query)

    def test_get_avg_disp_lcp_graph(self):
        query = Pipeline.Visualisation.get_avg_disp_lcp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("avg_disp_ts_lcp", query)

    def test_get_std_disp_lcp_graph(self):
        query = Pipeline.Visualisation.get_std_disp_lcp_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("std_disp_ts_lcp", query)

    def test_get_outlier_rel_ts_graph(self):
        query = Pipeline.Visualisation.get_outlier_rel_ts_graph(123, 1000.0)
        self.assertIn("123", query)
        self.assertIn("1000.0", query)
        self.assertIn("outlier_rel_ts", query)

    def test_patch_uids(self):
        query = Pipeline.Visualisation.patch_uids()
        self.assertIn("uid", query)
        self.assertIn("outlier_uid IS NOT NULL", query)
