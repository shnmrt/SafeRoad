import unittest
from unittest.mock import patch
from shapely.geometry import Point, Polygon
from shapely.wkb import dumps as dump_wkb
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from src.saferoad.plotter import Plotter  # replace with actual import path


class TestMapPane(unittest.TestCase):
    def setUp(self):
        self.pane = Plotter.MapPane()

    def test_generate_figure(self):
        fig, axs = self.pane.get_figure()
        self.assertIsInstance(fig, plt.Figure)
        self.assertEqual(len(axs), 5)

    @patch("contextily.add_basemap")
    def test_plot_basemap(self, mock_basemap):
        bbox = ([0, 0, 100, 100],)
        self.pane.plot_basemap(bbox)
        self.assertTrue(mock_basemap.called)

    def test_ps_density_color_label(self):
        self.assertEqual(self.pane.ps_density_color_label(50), ("red", "Low"))
        self.assertEqual(self.pane.ps_density_color_label(200), ("yellow", "Medium"))
        self.assertEqual(self.pane.ps_density_color_label(600), ("green", "High"))

    def test_outlier_color_label(self):
        self.assertEqual(self.pane.outlier_color_label(6), ("yellow", "5<|v|<7 mm/yr"))
        self.assertEqual(self.pane.outlier_color_label(8), ("orange", "7<|v|<9 mm/yr"))
        self.assertEqual(self.pane.outlier_color_label(12), ("red", "9<|v|<12 mm/yr"))

    def test_cum_disp_color_label(self):
        self.assertEqual(self.pane.cum_disp_color_label(-30), ("red", "(-60,-20) mm"))
        self.assertEqual(
            self.pane.cum_disp_color_label(-17), ("orange", "(-20,-15) mm")
        )
        self.assertEqual(self.pane.cum_disp_color_label(-10), ("yellow", "(-15,-5) mm"))
        self.assertEqual(self.pane.cum_disp_color_label(0), ("lightgreen", "(-5,5) mm"))
        self.assertEqual(self.pane.cum_disp_color_label(10), ("cyan", "(5,15) mm"))
        self.assertEqual(self.pane.cum_disp_color_label(20), ("blue", "(15,60) mm"))

    def test_gcp_vel_color(self):
        self.assertEqual(self.pane.gcp_vel_color(-7), "red")
        self.assertEqual(self.pane.gcp_vel_color(-5), "orange")
        self.assertEqual(self.pane.gcp_vel_color(-3), "yellow")
        self.assertEqual(self.pane.gcp_vel_color(1), "lightgreen")
        self.assertEqual(self.pane.gcp_vel_color(3), "cyan")
        self.assertEqual(self.pane.gcp_vel_color(10), "blue")

    def test_lcp_vel_color(self):
        self.assertEqual(self.pane.lcp_vel_color(1), "green")
        self.assertEqual(self.pane.lcp_vel_color(5), "red")

    def test_plot_ps_density(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        data = [(dump_wkb(poly), 200)]
        self.pane.plot_ps_density(data)
        self.assertTrue(len(self.pane.axs[0].patches) > 0)

    def test_plot_outliers(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt), 8)]
        self.pane.plot_outliers(data)
        self.assertTrue(len(self.pane.axs[1].collections) > 0)

    def test_plot_cum_disp(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        data = [(dump_wkb(poly), -10)]
        self.pane.plot_cum_disp(data)
        self.assertTrue(len(self.pane.axs[2].patches) > 0)

    def test_plot_gcp_velocity(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt), -5)]
        self.pane.plot_gcp_velocity(data)
        self.assertTrue(len(self.pane.axs[3].collections) > 0)

    def test_plot_lcp_velocity(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt), 5)]
        self.pane.plot_lcp_velocity(data)
        self.assertTrue(len(self.pane.axs[4].collections) > 0)

    def test_post_process_runs(self):
        self.pane.post_process()  # should not raise


class TestTimeSeriesPane(unittest.TestCase):
    def setUp(self):
        self.pane = Plotter.TimeSeriesPane()
        self.dates = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(5)]

    @patch("contextily.add_basemap")
    def test_plot_basemap_outlier(self, mock_basemap):
        self.pane.plot_basemap_outlier(([100], [200]))
        self.assertTrue(mock_basemap.called)

    @patch("contextily.add_basemap")
    def test_plot_basemap_pspoint(self, mock_basemap):
        self.pane.plot_basemap_pspoint(([100], [200]))
        self.assertTrue(mock_basemap.called)

    def test_outlier_color_label(self):
        self.assertEqual(self.pane.outlier_color_label(6), ("yellow", "5<|v|<7 mm/yr"))
        self.assertEqual(self.pane.outlier_color_label(8), ("orange", "7<|v|<9 mm/yr"))
        self.assertEqual(self.pane.outlier_color_label(12), ("red", "9<|v|<12 mm/yr"))

    def test_plot_all_outliers(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt), 10)]
        self.pane.plot_all_outliers(data)
        self.assertTrue(len(self.pane.axs[0].collections) > 0)

    def test_plot_square(self):
        self.pane.plot_square([(0, 0), (10, 10)])
        self.assertTrue(len(self.pane.axs[0].patches) > 0)

    def test_plot_pspoint_dist(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt),)]
        self.pane.plot_pspoint_dist(data)
        self.assertTrue(len(self.pane.axs[1].collections) > 0)

    def test_plot_outlier(self):
        pt = Point(0, 0)
        data = [(dump_wkb(pt), 9)]
        self.pane.plot_outlier(data)
        self.assertTrue(len(self.pane.axs[1].collections) > 0)

    def test_plot_lcp(self):
        pt = Point(0, 0)
        data = [dump_wkb(pt)]
        self.pane.plot_lcp(data)
        self.assertTrue(len(self.pane.axs[1].collections) > 0)

    def test_cum_disp_graphs(self):
        y = [([1, 2, 3, 4, 5],)]
        std = [([1, 1, 1, 1, 1],)]
        self.pane.plot_cum_disp_graph(y, self.dates)
        self.pane.plot_avg_disp_graph(y, self.dates)
        self.pane.plot_std_disp_graph(y, std, self.dates)
        # scatter + 2x fill_between -> collections exist
        self.assertGreater(len(self.pane.axs[2].collections), 0)

    def test_rel_disp_graphs(self):
        y = [([1, 2, 3, 4, 5],)]
        std = [([1, 1, 1, 1, 1],)]
        self.pane.plot_rel_disp_graph(y, self.dates)
        self.pane.plot_avg_rel_disp_graph(y, self.dates)
        self.pane.plot_std_rel_disp_graph(y, std, self.dates)
        self.assertTrue(len(self.pane.axs[3].collections) > 0)

    def test_lcp_disp_graphs(self):
        y = [([1, 2, 3, 4, 5],)]
        std = [([1, 1, 1, 1, 1],)]
        self.pane.plot_lcp_disp_graph(y, self.dates)
        self.pane.plot_avg_lcp_disp_graph(y, self.dates)
        self.pane.plot_std_lcp_disp_graph(y, std, self.dates)
        self.assertTrue(len(self.pane.axs[4].collections) > 0)

    def test_post_process_runs(self):
        self.pane.post_process()  # should not raise


if __name__ == "__main__":
    unittest.main()
