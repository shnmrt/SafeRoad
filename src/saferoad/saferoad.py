# standard modules
import io
from datetime import datetime
from joblib import Parallel, delayed
from shapely.wkb import loads as wkb_loads
from dataclasses import dataclass
from typing import Literal
from tqdm import tqdm

# plotting modules
import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import pyplot as plt

matplotlib.use("Agg")
# saferoad modules
from .plotter import Plotter
from .database import DataBase
from .pipeline import Pipeline
from .utils import extract_dates, time_vector, Timer


@dataclass
class PsData:
    """Class for storing point source data information.

    :param filepath: Path to the point source data file.
    :type filepath: str
    :param latitude: Field name of the latitude field in the data file.
    :type latitude: str
    :param longitude: Field name of the longitude field in the data file.
    :type longitude: str
    :param unit: Unit of measurement for the coordinates. Options are "m", "cm", or "mm". Default is "m".
    :type unit: Literal["m", "cm", "mm"]
    :param crs_code: Coordinate Reference System code. Default is "EPSG:4326".
    :type crs_code: str
    :param name: Name identifier for the point source data. Default is "pspoint".
    :type name: str
    """

    filepath: str
    latitude: str
    longitude: str
    unit: Literal["m", "cm", "mm"] = "m"
    crs_code: str = "EPSG:4326"
    name: str = "pspoint"

    def __post_init__(self):
        assert self.filepath, "File path must be provided."
        assert isinstance(self.filepath, str), "File path must be a string."
        assert self.latitude, "Latitude field name must be provided."
        assert isinstance(self.latitude, str), "Latitude field name must be a string."
        assert self.longitude, "Longitude field name must be provided."
        assert isinstance(self.longitude, str), "Longitude field name must be a string."
        assert self.unit in ["m", "cm", "mm"], "Unit must be one of 'm', 'cm', or 'mm'."
        assert self.crs_code, "CRS code must be provided."
        assert isinstance(self.crs_code, str), "CRS code must be a string."
        assert self.name, "Name must be provided."
        assert isinstance(self.name, str), "Name must be a string."


@dataclass
class Road:
    """Class for storing road data information.

    :param filepath: Path to the road data file.
    :type filepath: str
    :param crs_code: Coordinate Reference System code. Default is "EPSG:4326".
    :type crs_code: str
    :param name: Name identifier for the road data. Default is "road".
    :type name: str
    """

    filepath: str
    crs_code: str = "EPSG:4326"
    name: str = "road"

    def __post_init__(self):
        assert self.filepath, "File path must be provided."
        assert isinstance(self.filepath, str), "File path must be a string."
        assert self.name, "Name must be provided."
        assert isinstance(self.name, str), "Name must be a string."


class SafeRoad:
    """
    A class to perform road deformation analysis using MT-InSAR data.

    :param road: An instance of the Road class containing road data information.
    :type road: Road
    :param ps_data: An instance of the PsData class containing MT-InSAR data information.
    :type ps_data: PsData
    :param computational_crs: A string representing the EPSG code for the computational CRS.
    :type computational_crs: str
    """

    def __init__(self, road: Road, ps_data: PsData, computational_crs: str):

        assert isinstance(road, Road), "road must be an instance of Road class"
        assert isinstance(
            ps_data, PsData
        ), "ps_data must be an instance of PsData class"
        assert isinstance(
            computational_crs, str
        ), "computational_crs must be a string representing the EPSG code"

        self.ps_data = ps_data
        self.road_data = road
        self.database = DataBase()
        # self.scaling_factor = self._set_scaling_factor_()
        self.computational_crs = computational_crs

    @property
    def _scaling_factor_(self):
        # determine the scaling factor based on the unit
        units = ["m", "cm", "mm"]
        sf = [1000, 10, 1]
        return sf[units.index(self.ps_data.unit)]

    def load_files(self):
        """
        Load the road and MT-InSAR data files into the database.
        """

        # setup the db if loading
        with Timer("Setting up the database"):
            self.database.setup()
        # road_query
        with Timer("Loading road data"):
            self.database.run(
                Pipeline.Processing.load_file(
                    self.road_data.filepath, self.road_data.name
                )
            )
        # ps_query
        with Timer("Loading ps data"):
            self.database.run(
                Pipeline.Processing.load_file(self.ps_data.filepath, self.ps_data.name)
            )

    def preprocess(self, attribute: str = None):
        """
        Preprocess the road and MT-InSAR data.

        This includes transforming the data to the computational CRS, dissolving road features,
        and building geometries for the MT-InSAR points.
        1. Transform the road and MT-InSAR data to the computational CRS.
        2. Dissolve road features based on the provided attribute if given, otherwise merge all features.
        3. Build geometries for the MT-InSAR points from the latitude and longitude columns.
        4. Transform the MT-InSAR data to the computational CRS.

        :param attribute: An optional string representing the attribute to dissolve road features.
                          If None, all features will be merged. Default is None.
        :type attribute: str, optional
        """
        # Transform the road projection
        with Timer("Transforming road data to computational CRS"):
            self.database.run(
                Pipeline.Processing.spatial_tranformation(
                    source_epsg=self.road_data.crs_code,
                    target_epsg=self.computational_crs,
                    table_name=self.road_data.name,
                )
            )

        # Dissolve the road features based on the provided attribute if given if not merge everything
        with Timer("Dissolving road features"):
            self.database.run(
                Pipeline.Processing.dissolve_features(
                    attribute=attribute, table_name=self.road_data.name
                )
            )
        # build the geometry for the psoints from csv headers
        with Timer("Building geometry for PS data"):
            self.database.run(
                Pipeline.Processing.build_geometry(
                    latitude=self.ps_data.latitude,
                    longitude=self.ps_data.longitude,
                    table_name=self.ps_data.name,
                )
            )

        # Transform the ps data to the computational CRS
        with Timer("Transforming PS data to computational CRS"):
            self.database.run(
                Pipeline.Processing.spatial_tranformation(
                    source_epsg=self.ps_data.crs_code,
                    target_epsg=self.computational_crs,
                    table_name=self.ps_data.name,
                )
            )

    def generate_rectangles(self, road_width: float, segment_length: float):
        """
        Generate road segments and patches.

        This involves:
        1. Splitting the road into segments of equal length.
        2. Generating rectangles along the road segments with a specified width.
        2. Rotating the generated rectangles int the same direction along the road.

        :param road_width: A float representing the width of the road segments in meters.
        :param segment_length: A float representing the length of each road segment in meters.
        """

        with Timer("Generating road segments and patches"):
            self.database.run(
                Pipeline.Processing.split_to_segments(segment_length=segment_length)
            )
            self.database.run(
                Pipeline.Processing.generate_patches(
                    width=road_width, length=segment_length
                )
            )

    def run_analysis(self):
        """
        Run the deformation analysis on the MT-InSAR data for road network.

        This includes calculating cumulative displacement, average velocity, point density,
        local control points, and outliers.
        """
        # calculate displacement per points
        # get the column names from the ps_data
        fields = [
            i[0]
            for i in self.database.connection.sql(
                Pipeline.Processing.get_column_names(self.ps_data.name)
            ).fetchall()
        ]

        # extract dates from the column names and generate time vector
        names, dates = extract_dates(column_names=fields)
        date_vector = time_vector(dates=dates)

        with Timer("Calculating cumulative displacement per point"):
            self.database.run(
                Pipeline.Processing.calc_cum_disp(
                    dates=names, table_name=self.ps_data.name
                )
            )

        # build spatial relation with
        # assign points to patches generate patch_id field on pspoint table
        with Timer("Relating points to patches"):
            self.database.run(
                Pipeline.Processing.relate_point_patches(self.ps_data.name)
            )

        # calculate average velocity per point needs patch_id in pspoint table for optimization purposes
        with Timer("Calculating average velocity per point"):
            self.database.run(
                Pipeline.Processing.calc_avg_velocity(
                    time_vector=date_vector,
                    field_names=names,
                    table_name=self.ps_data.name,
                )
            )

        # calculate point count per patch and point density
        with Timer("Calculating point density per patch"):
            self.database.run(Pipeline.Processing.calc_point_density(self.ps_data.name))
        # calculate average cumulative displacement per patch
        with Timer("Calculating average cumulative displacement per patch"):
            self.database.run(Pipeline.Processing.calc_avg_cum_disp())
        # calculate average displacement time series per patch based on gcp
        with Timer(
            "Calculating average displacement time series per patch based on GCP"
        ):
            self.database.run(
                Pipeline.Processing.calc_avg_disp_ts_gcp(date_fields=names)
            )
        # calculate standard deviation of displacement time series per patch based on gcp
        with Timer(
            "Calculating standard deviation of displacement time series per patch based on GCP"
        ):
            self.database.run(
                Pipeline.Processing.calc_std_disp_ts_gcp(date_fields=names)
            )

        # calculate average velocity per patch based on gcp
        with Timer("Calculating average velocity per patch based on GCP"):
            self.database.run(
                Pipeline.Processing.calc_avg_velocity_gcp(table_name=self.ps_data.name)
            )

        # calculate the local control point per patch
        with Timer("Calculating local control points per patch"):
            self.database.run(Pipeline.Processing.select_lcps(self.ps_data.name))

        # calculate the local control point avg velocity per patch
        with Timer("Calculating local control points average velocity per patch"):
            self.database.run(Pipeline.Processing.calc_lcp_velocity())

        # calculate the average and std of the displacement time series per patch based on lcp
        with Timer(
            "Calculating average and std of displacement time series per patch based on LCP"
        ):
            self.database.run(
                Pipeline.Processing.calc_avg_std_disp_ts_lcp(
                    date_fields=names, table_name=self.ps_data.name
                )
            )

        # calculate the median and std of the displacement time series per patch based on lcp
        with Timer(
            "Calculating median and std of displacement time series per patch based on LCP"
        ):
            self.database.run(
                Pipeline.Processing.calc_med_std_disp_ts_lcp(
                    date_fields=names, table_name=self.ps_data.name
                )
            )

        # calculate the average velocity per patch based on lcp
        with Timer("Calculating average velocity per patch based on LCP"):
            self.database.run(
                Pipeline.Processing.calc_avg_velocity_lcp(table_name=self.ps_data.name)
            )

        # calculate the average relative velocity per patch based on lcp
        with Timer("Calculating average relative velocity per patch based on LCP"):
            self.database.run(
                Pipeline.Processing.calc_avg_lcp_velocity(self.ps_data.name)
            )

        # calulate the outliers per patch based
        with Timer("Calculating outliers per patch"):
            self.database.run(
                Pipeline.Processing.calc_outliers(
                    self._scaling_factor_, self.ps_data.name
                )
            )

            threshold_count = self.database.connection.execute(
                "Select count(*) from outliers;"
            ).fetchone()[0]
            print("%s outliers detected by threshold method" % threshold_count)

            self.database.run(
                Pipeline.Processing.calc_outliers_avg_lcd(
                    self.ps_data.name, date_vector=date_vector, date_names=names
                )
            )
            ald_count = (
                self.database.connection.execute(
                    "Select count(*) from outliers;"
                ).fetchone()[0]
                - threshold_count
            )
            print("%s outliers detected by avg local disp method" % (ald_count))

            self.database.run(
                Pipeline.Processing.calc_outliers_med_lcd(
                    self.ps_data.name, date_vector=date_vector, date_names=names
                )
            )
            med_count = (
                self.database.connection.execute(
                    "select count(*) from outliers;"
                ).fetchone()[0]
                - ald_count
                - threshold_count
            )
            print("%s outliers detected by median local disp method" % (med_count))

        with Timer("Collecting and patching the LCP time series"):
            self.database.run(
                Pipeline.Processing.lcp_ts_patch(
                    date_fields=names, table_name=self.ps_data.name
                )
            )
        with Timer("Collecting outlier time series"):
            self.database.run(
                Pipeline.Processing.outlier_ts_patch(
                    date_fields=names, table_name=self.ps_data.name
                )
            )
        with Timer("collecting differential displacement time series"):
            self.database.run(Pipeline.Processing.outlier_rel_ts_patch())

    def generate_report(self, output_name: str):
        """
        Generate a PDF report containing maps and time series plots.

        :param output_name: A string representing the name of the output PDF file endswith `.pdf` extension.
        :type output_name: str
        """

        def render_ts_plots_workers(
            patch_uid: float,
            outliers: list[tuple],
            dates: list[datetime],
            outlier_center: tuple[float, float],  #
            patch_center: tuple,
            pspoints: list[tuple],
            lcp_point: list[tuple],
            cum_disp: list[tuple],
            avg_cum_disp: list[tuple],
            std_cum_disp: list[tuple],
            outlier_rel_ts: list[tuple],
            avg_lcp_disp: list[tuple],
            std_lcp_disp: list[tuple],
            lcp_disp: list[tuple],
        ) -> bytes:

            # plotting
            tsplotter = Plotter.TimeSeriesPane()
            # 0
            tsplotter.plot_basemap_outlier(wkb_loads(outlier_center[0]).xy)
            tsplotter.plot_all_outliers(outliers)
            tsplotter.plot_square(wkb_loads(outlier_center[0]).xy)
            tsplotter.plot_basemap_pspoint(wkb_loads(patch_center[0]).xy)
            # 1
            tsplotter.plot_pspoint_dist(pspoints)
            tsplotter.plot_lcp(lcp_point)
            tsplotter.plot_outlier(outliers)
            # 2
            tsplotter.plot_std_disp_graph(avg_cum_disp, std_cum_disp, dates)
            tsplotter.plot_avg_disp_graph(avg_cum_disp, dates)
            tsplotter.plot_cum_disp_graph(cum_disp, dates)

            # 3
            tsplotter.plot_std_rel_disp_graph(avg_lcp_disp, std_lcp_disp, dates)
            tsplotter.plot_avg_rel_disp_graph(avg_lcp_disp, dates)
            tsplotter.plot_rel_disp_graph(outlier_rel_ts, dates)

            # 4
            tsplotter.plot_std_lcp_disp_graph(avg_cum_disp, std_cum_disp, dates)
            tsplotter.plot_avg_lcp_disp_graph(avg_cum_disp, dates)
            tsplotter.plot_lcp_disp_graph(lcp_disp, dates)
            tsplotter.post_process()

            fig, _ = tsplotter.get_figure()

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            plt.close(fig)
            return buf.getvalue()

        # export the results
        with Timer("Generating and saving the report"):
            with PdfPages(output_name) as pdf:
                # bbox of the patches

                bbox = self.database.connection.execute(
                    Pipeline.Visualisation.get_table_bbox(
                        "patches", self.computational_crs
                    )
                ).fetchall()
                # ps density and patch geometries
                ps_density = self.database.connection.execute(
                    Pipeline.Visualisation.get_ps_density(self.computational_crs)
                ).fetchall()
                # outliers and coordinates
                outliers = self.database.connection.execute(
                    Pipeline.Visualisation.get_outliers_map(
                        self.computational_crs, self._scaling_factor_
                    )
                ).fetchall()
                # cumulative displacement per point
                cum_disp = self.database.connection.execute(
                    Pipeline.Visualisation.get_cum_disp_map(
                        self.computational_crs, self._scaling_factor_
                    )
                ).fetchall()
                # gcp average velocity per point
                gcp_vel = self.database.connection.execute(
                    Pipeline.Visualisation.get_ps_vel_gcp(
                        self.computational_crs, self._scaling_factor_
                    )
                ).fetchall()
                # lcp average velocity per point
                lcp_vel = self.database.connection.execute(
                    Pipeline.Visualisation.get_ps_vel_lcp(
                        self.computational_crs, self._scaling_factor_
                    )
                ).fetchall()

                # plotting the first page -- maps
                print("Starting to render the map page")
                map_plotter = Plotter.MapPane()
                map_plotter.plot_basemap(bbox=bbox)
                map_plotter.plot_ps_density(ps_density)
                map_plotter.plot_outliers(outliers)
                map_plotter.plot_cum_disp(cum_disp)
                map_plotter.plot_gcp_velocity(gcp_vel)
                map_plotter.plot_lcp_velocity(lcp_vel)
                map_plotter.post_process()
                fig, _ = map_plotter.get_figure()
                plt.close(fig)
                pdf.savefig(fig)
                print("Map page has been rendered")

                print("Intiating time series rendering")
                # collect the patch_ids which has outliers
                puids = [
                    i[0]
                    for i in self.database.connection.execute(
                        Pipeline.Visualisation.patch_uids()
                    ).fetchall()
                ]
                _, dates = extract_dates(
                    [
                        i[0]
                        for i in self.database.connection.execute(
                            Pipeline.Processing.get_column_names(self.ps_data.name)
                        ).fetchall()
                    ]
                )
                outliers_map = self.database.connection.execute(
                    Pipeline.Visualisation.get_outliers_map(
                        self.computational_crs, self._scaling_factor_
                    )
                ).fetchall()

                # prepare the data for parallel processing
                data_ready = []
                for uid in puids:
                    outliers = self.database.connection.execute(
                        Pipeline.Visualisation.get_outlier_points(
                            patch_id=uid, source_crs=self.computational_crs
                        )
                    ).fetchall()
                    patch_center = self.database.connection.execute(
                        Pipeline.Visualisation.get_patch_center(
                            patch_id=uid, source_crs=self.computational_crs
                        )
                    ).fetchone()

                    pspoints = self.database.connection.execute(
                        Pipeline.Visualisation.get_ps_points(
                            patch_id=uid,
                            source_crs=self.computational_crs,
                            table_name=self.ps_data.name,
                        )
                    ).fetchall()  # pspoints

                    lcp_point = self.database.connection.execute(
                        Pipeline.Visualisation.get_lcp_point(
                            patch_id=uid, source_crs=self.computational_crs
                        )
                    ).fetchone()  # lcp point

                    avg_cum_disp = self.database.connection.execute(
                        Pipeline.Visualisation.get_avg_cum_disp_graph(
                            patch_id=uid, scaling_factor=self._scaling_factor_
                        )
                    ).fetchall()  # avg_cum_disp

                    std_cum_disp = self.database.connection.execute(
                        Pipeline.Visualisation.get_std_cum_disp_graph(
                            patch_id=uid, scaling_factor=self._scaling_factor_
                        )
                    ).fetchall()  # std_cum_disp

                    avg_lcp_disp = self.database.connection.execute(
                        Pipeline.Visualisation.get_avg_disp_lcp_graph(
                            patch_id=uid, scaling_factor=self._scaling_factor_
                        )
                    ).fetchall()  # avg_lcp_disp

                    std_lcp_disp = self.database.connection.execute(
                        Pipeline.Visualisation.get_std_disp_lcp_graph(
                            patch_id=uid, scaling_factor=self._scaling_factor_
                        )
                    ).fetchall()  # std_lcp_disp

                    lcp_disp = self.database.connection.execute(
                        Pipeline.Visualisation.get_lcp_disp_graph(
                            patch_id=uid, scaling_factor=self._scaling_factor_
                        )
                    ).fetchall()  # lcp_disp

                    for outlier in outliers:
                        o_id = outlier[0]
                        center = self.database.connection.execute(
                            Pipeline.Visualisation.get_center(
                                point_uid=o_id, source_crs=self.computational_crs
                            )
                        ).fetchone()
                        cum_disp = self.database.connection.execute(
                            Pipeline.Visualisation.get_cum_disp_graph(
                                outlier_id=o_id, scaling_factor=self._scaling_factor_
                            )
                        ).fetchall()  # cum_disp

                        outlier_rel_ts = self.database.connection.execute(
                            Pipeline.Visualisation.get_outlier_rel_ts_graph(
                                outlier_id=o_id, scaling_factor=self._scaling_factor_
                            )
                        ).fetchall()  # outlier_rel_ts
                        data_ready.append(
                            (
                                uid,
                                outliers_map,
                                dates,
                                center,
                                patch_center,
                                pspoints,
                                lcp_point,
                                cum_disp,
                                avg_cum_disp,
                                std_cum_disp,
                                outlier_rel_ts,
                                avg_lcp_disp,
                                std_lcp_disp,
                                lcp_disp,
                            )
                        )

                print(f"Total pages to render for outliers: {len(data_ready)}")

                png_pages = Parallel(n_jobs=-1, backend="loky")(
                    delayed(render_ts_plots_workers)(
                        patch_uid,
                        outliers,
                        dates,
                        outlier_center,
                        patch_center,
                        pspoints,
                        lcp_point,
                        cum_disp,
                        avg_cum_disp,
                        std_cum_disp,
                        outlier_rel_ts,
                        avg_lcp_disp,
                        std_lcp_disp,
                        lcp_disp,
                    )
                    for (
                        patch_uid,
                        outliers,
                        dates,
                        outlier_center,
                        patch_center,
                        pspoints,
                        lcp_point,
                        cum_disp,
                        avg_cum_disp,
                        std_cum_disp,
                        outlier_rel_ts,
                        avg_lcp_disp,
                        std_lcp_disp,
                        lcp_disp,
                    ) in tqdm(data_ready)
                )
                print("All plots rendered, now saving to pdf")
                for png in png_pages:
                    img = plt.imread(io.BytesIO(png), format="png")
                    fig, ax = plt.subplots(figsize=(12, 12), dpi=80)
                    # ax = fig.add_subplot(111)
                    ax.imshow(img)
                    ax.axis("off")
                    ax.set_xticks([])
                    ax.set_yticks([])
                    ax.set_frame_on(False)
                    pdf.savefig(fig)
                    plt.close(fig)
                print("All pages saved to pdf")
