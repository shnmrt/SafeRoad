from matplotlib import pyplot as plt
import contextily as ctx
from shapely.wkb import loads as load_wkb
from matplotlib.lines import Line2D
from datetime import datetime
import matplotlib.dates as mdates


class Plotter:
    """Class to create and manage plots for geospatial data analysis."""

    class MapPane:
        """
        Class to create and manage a multi-panel map figure.

        Panels include:
        - PS Density
        - Outliers
        - Cumulative Displacement
        - PS Velocity based on GCP
        - PS Velocity based on LCP
        """

        def __init__(self):
            self.generate_figure()

        def generate_figure(self):
            """
            Generates a multi-panel figure with specified layout and titles.
            """
            fig = plt.figure(figsize=(18, 12))
            layout = [
                ["A", "A", "B", "B", "C", "C"],  # top row: 3 panels, equal widths
                [".", "D", "D", "E", "E", "."],  # bottom row: 2 panels centered
            ]
            axs = fig.subplot_mosaic(layout, empty_sentinel=".")

            # Optional spacing (no constrained_layout -> safer with contextily)
            fig.subplots_adjust(wspace=0.25, hspace=0.35)
            axs["A"].set_title("PS Density", fontsize=10)
            axs["B"].set_title("Outliers", fontsize=10)
            axs["C"].set_title("Cumulative Displacement", fontsize=10)
            axs["D"].set_title("PS Velocity based on GCP", fontsize=10)
            axs["E"].set_title("PS Velocity based on LCP", fontsize=10)
            self.fig = fig
            self.axs = [axs["A"], axs["B"], axs["C"], axs["D"], axs["E"]]

        def plot_basemap(self, bbox: tuple[float, float, float, float]):
            """
            Plots a basemap on all axes using the provided bounding box.

            :param bbox: A tuple representing the bounding box (minx, miny, maxx, maxy).
            """
            bbox = [i for i in bbox[0]]

            for ax in self.axs:
                ax.set_xlim(bbox[0] - 2000, bbox[2] + 2000)
                ax.set_ylim(bbox[1] - 2000, bbox[3] + 4000)
                ctx.add_basemap(
                    ax,
                    source=ctx.providers.CartoDB.Positron,
                    crs="EPSG:3857",
                )

        def plot_ps_density(self, plot_data: list[tuple]) -> None:
            """
            Plots PS Density data on the first axis.

            :param plot_data: List of tuples containing geometry and PS density value.
            """
            label_store = []
            for geom, psdensity in plot_data:
                geom = load_wkb(geom)
                color, label = self.ps_density_color_label(psdensity)
                if label not in label_store:
                    label_store.append(label)
                else:
                    label = None

                self.axs[0].fill(
                    *geom.exterior.xy,
                    fc=color,
                    ec=color,
                    label=label,
                )
            self.axs[0].legend(
                title="PS Density",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_outliers(self, plot_data: list[tuple]) -> None:
            """
            Plots outlier data on the second axis.

            :param plot_data: List of tuples containing geometry and outlier velocity value.
            """
            label_store = []
            for geom, vel in plot_data:
                geom = load_wkb(geom)
                color, label = self.outlier_color_label(vel)
                if label not in label_store:
                    label_store.append(label)
                else:
                    label = None

                self.axs[1].scatter(
                    *geom.xy,
                    s=10,
                    c=color,
                    label=label,
                )
            self.axs[1].legend(
                title="Outlier",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_cum_disp(self, plot_data: list[tuple]) -> None:
            """
            Plots cumulative displacement data on the third axis.

            :param plot_data: List of tuples containing geometry and cumulative displacement value.
            """
            label_store = []
            for geom, disp in plot_data:
                geom = load_wkb(geom)
                color, label = self.cum_disp_color_label(disp)
                if label not in label_store:
                    label_store.append(label)
                else:
                    label = None

                self.axs[2].fill(
                    *geom.exterior.xy,
                    fc=color,
                    ec=color,
                    label=label,
                )
            self.axs[2].legend(
                title="Cumulative\nDisplacement",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_gcp_velocity(self, plot_data: list[tuple]) -> None:
            """Plots GCP velocity data on the fourth axis.

            :param plot_data: List of tuples containing geometry and GCP velocity value.
            """
            points, colors = [], []
            for geom, vel in plot_data:
                geom = load_wkb(geom)
                points.append(geom.xy)
                colors.append(self.gcp_vel_color(vel))

            x_coords = [p[0][0] for p in points]
            y_coords = [p[1][0] for p in points]

            self.axs[3].scatter(
                x_coords,
                y_coords,
                s=4,
                c=colors,
                alpha=0.7,
            )
            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="red",
                    markersize=6,
                    label="(-15,-6) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="orange",
                    markersize=6,
                    label="(-6,-4) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="yellow",
                    markersize=6,
                    label="(-4,-2) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="lightgreen",
                    markersize=6,
                    label="(-2,2) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="cyan",
                    markersize=6,
                    label="(2,5) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="blue",
                    markersize=6,
                    label="(5,15) mm",
                ),
            ]

            self.axs[3].legend(
                handles=legend_elements,
                title="PS Velocity GCP",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_lcp_velocity(self, plot_data: list[tuple]) -> None:
            """Plots LCP velocity data on the fifth axis.

            :param plot_data: List of tuples containing geometry and LCP velocity value.
            """
            points, colors = [], []
            for geom, vel in plot_data:
                geom = load_wkb(geom)
                points.append(geom.xy)
                colors.append(self.lcp_vel_color(vel))
            x_coords = [p[0][0] for p in points]
            y_coords = [p[1][0] for p in points]

            self.axs[4].scatter(
                x_coords,
                y_coords,
                s=2,
                c=colors,
                alpha=0.6,
            )

            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="green",
                    markersize=6,
                    label="(0,2) mm",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="red",
                    markersize=6,
                    label="(2,12) mm",
                ),
            ]
            self.axs[4].legend(
                handles=legend_elements,
                title="PS Velocity LCP",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def post_process(self):
            """
            Post-processes the figure for better aesthetics.

            """
            for i in [1, 2, 4]:
                self.axs[i].get_yaxis().set_visible(False)
                xticks = self.axs[i].get_xticks()
                self.axs[i].set_xticks(xticks[::2])  # Keep every other tick
                self.axs[i].set_xticklabels(self.axs[i].get_xticks())
            for i in [0, 3]:
                yticks = self.axs[i].get_yticks()
                self.axs[i].set_yticks(yticks[::3])  # Keep every other tick
                self.axs[i].set_yticklabels(
                    self.axs[i].get_yticks(),
                    horizontalalignment="center",
                    verticalalignment="center",
                )
                xticks = self.axs[i].get_xticks()
                self.axs[i].set_xticks(xticks[::2])  # Keep every other tick
                self.axs[i].set_xticklabels(self.axs[i].get_xticks())

            # self.fig.tight_layout()

        def get_figure(self) -> tuple[plt.Figure, list[plt.Axes]]:
            """
            Returns the figure and axes.

            :return: Tuple containing the figure and axes.
            :rtype: tuple[plt.Figure, list[plt.Axes]]
            """
            return self.fig, self.axs

        def outlier_color_label(self, value: float) -> tuple[str, str]:
            """Returns color and label based on outlier velocity value.

            :param value: Outlier velocity value.
            :type value: float
            :return: Tuple containing color and label.
            :rtype: tuple[str, str]
            """
            if value <= 7:
                return "yellow", "5<|v|<7 mm/yr"
            elif value <= 9:
                return "orange", "7<|v|<9 mm/yr"
            else:
                return "red", "9<|v|<12 mm/yr"

        def ps_density_color_label(self, value: float) -> tuple[str, str]:
            """Returns color and label based on PS density value.

            :param value: PS density value.
            :type value: float
            :return: Tuple containing color and label.
            :rtype: tuple[str, str]
            """
            if value < 100:
                return "red", "Low"
            if 100 <= value < 500:
                return "yellow", "Medium"
            else:
                return "green", "High"

        def cum_disp_color_label(self, value: float) -> str:
            """Returns color and label based on cumulative displacement value.

            :param value: Cumulative displacement value.
            :type value: float
            :return: Tuple containing color and label.
            :rtype: tuple[str, str]
            """
            if value < -20:
                return "red", "(-60,-20) mm"
            elif value < -15:
                return "orange", "(-20,-15) mm"
            elif value < -5:
                return "yellow", "(-15,-5) mm"
            elif value < 5:
                return "lightgreen", "(-5,5) mm"
            elif value < 15:
                return "cyan", "(5,15) mm"
            else:
                return "blue", "(15,60) mm"

        def gcp_vel_color(self, value: float) -> str:
            """Returns color based on GCP velocity value.

            :param value: GCP velocity value.
            :type value: float
            :return: Color string.
            :rtype: str
            """
            if value <= -6:
                return "red"
            elif value <= -4:
                return "orange"
            elif value <= -2:
                return "yellow"
            elif value <= 2:
                return "lightgreen"
            elif value <= 5:
                return "cyan"
            else:
                return "blue"

        def lcp_vel_color(self, value: float) -> str:
            """Returns color based on LCP velocity value.

            :param value: LCP velocity value.
            :type value: float
            :return: Color string.
            :rtype: str
            """
            if value <= 2:
                return "green"
            else:
                return "red"

    class TimeSeriesPane:
        """Class to create and manage a multi-panel time series figure.
        Panels include:
        - Basemap with Outliers
        - Basemap with PS Points
        - Cumulative Displacement
        - Relative Displacement
        - Local Control Point Displacement
        """

        def __init__(self):
            self.generate_figure()

        def generate_figure(self):
            """Generates a multi-panel figure with specified layout and titles."""
            fig = plt.figure(figsize=(12, 12), dpi=150)
            layout = [
                3 * ["A"] + 3 * ["C"],  # ["A", "A", "A", "C", "C", "C"],
                3 * ["A"] + 3 * ["C"],  # ["A", "A", "A", "C", "C", "C"],
                3 * ["A"] + 3 * ["D"],  # ["A", "A", "A", "D", "D", "D"],
                3 * ["B"] + 3 * ["D"],  # ["B", "B", "B", "D", "D", "D"],
                3 * ["B"] + 3 * ["E"],  # ["B", "B", "B", "E", "E", "E"],
                3 * ["B"] + 3 * ["E"],  # ["B", "B", "B", "E", "E", "E"],
            ]
            axs = fig.subplot_mosaic(layout, empty_sentinel=".")
            fig.subplots_adjust(wspace=1, hspace=1)
            axs["C"].set_title("Cumulative Displacement", fontsize=10)
            axs["C"].set_ylabel("[mm]", fontsize=8, labelpad=2)
            axs["D"].set_title("Relative Displacement", fontsize=10)
            axs["D"].set_ylabel("[mm]", fontsize=8, labelpad=2)
            axs["E"].set_title("Local Control Point Displacement", fontsize=10)
            axs["E"].set_ylabel("[mm]", fontsize=8, labelpad=2)
            self.fig = fig
            self.axs = [axs["A"], axs["B"], axs["C"], axs["D"], axs["E"]]

        def plot_basemap_outlier(self, center: tuple[float, float]):
            """
            Plots a basemap on the first axis using the provided center point.

            :param center: A tuple representing the center point (x, y).
            :type center: tuple[float, float]
            """
            self.axs[0].set_xlim(center[0][0] - 2000, center[0][0] + 2000)
            self.axs[0].set_ylim(center[1][0] - 2000, center[1][0] + 4000)
            ctx.add_basemap(
                self.axs[0],
                source=ctx.providers.CartoDB.Positron,
                crs="EPSG:3857",
            )

        def plot_basemap_pspoint(self, center: tuple[float, float]):
            """
            Plots a basemap on the second axis using the provided center point.

            :param center: A tuple representing the center point (x, y).
            :type center: tuple[float, float]
            """
            self.axs[1].set_xlim(center[0][0] - 1000, center[0][0] + 1000)
            self.axs[1].set_ylim(center[1][0] - 1000, center[1][0] + 1000)
            ctx.add_basemap(
                self.axs[1],
                source=ctx.providers.CartoDB.Positron,
                crs="EPSG:3857",
            )

        def plot_all_outliers(self, plot_data: list[tuple]) -> None:
            """Plots all outlier data on the first axis.

            :param plot_data: List of tuples containing geometry and outlier velocity value.
            :type plot_data: list[tuple]
            """
            label_store = []
            for geom, vel in plot_data:
                geom = load_wkb(geom)
                color, label = self.outlier_color_label(vel)
                if label not in label_store:
                    label_store.append(label)
                else:
                    label = None

                self.axs[0].scatter(
                    *geom.xy,
                    s=10,
                    c=color,
                    label=label,
                )
            self.axs[0].legend(
                title="Outlier",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_square(self, plot_data: list[tuple]) -> None:
            """Plots a square on the first axis to indicate zoom area.

            :param plot_data: List of tuples containing geometry and outlier velocity value.
            :type plot_data: list[tuple]
            """
            label_store = []
            x, y = plot_data[0][0], plot_data[1][0]
            square = [
                (x - 75, y - 75),
                (x + 75, y - 75),
                (x + 75, y + 75),
                (x - 75, y + 75),
                (x - 75, y - 75),  # Close the square
            ]
            square_x, square_y = zip(*square)
            self.axs[0].fill(
                square_x,
                square_y,
                fc="none",
                ec="black",
                label="Zoom Area",
            )
            self.axs[0].legend(
                title="Outliers",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_pspoint_dist(self, plot_data: list[tuple]) -> None:
            """Plots PS Points on the second axis.

            :param plot_data: List of tuples containing geometry.
            :type plot_data: list[tuple]
            """
            points = []
            for geom in plot_data:
                if isinstance(geom, tuple) and len(geom) > 0:
                    geom = load_wkb(geom[0])
                    points.append(geom.xy)
            x_coords = [p[0][0] for p in points]
            y_coords = [p[1][0] for p in points]

            self.axs[1].scatter(
                x_coords,
                y_coords,
                s=6,
                c="black",
                label="PS Points",
            )
            self.axs[1].legend(
                title="Legend",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_outlier(self, plot_data: list[tuple]) -> None:
            """Plots outlier data on the second axis.

            :param plot_data: List of tuples containing geometry and outlier velocity value.
            :type plot_data: list[tuple]
            """
            label_store = []
            for geom, vel in plot_data:
                geom = load_wkb(geom)
                color, label = self.outlier_color_label(vel)
                if label not in label_store:
                    label_store.append(label)
                else:
                    label = None

                self.axs[1].scatter(
                    *geom.xy,
                    s=16,
                    c=color,
                    label=label,
                )
            self.axs[1].legend(
                title="Legend",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_lcp(self, plot_data: list[tuple]) -> None:
            """Plots LCP data on the second axis.

            :param plot_data: List of tuples containing geometry.
            :type plot_data: list[tuple]
            """
            geom = load_wkb(plot_data[0])
            self.axs[1].scatter(
                *geom.xy,
                s=20,
                marker="^",
                c="lightblue",
                label="LCP",
            )
            self.axs[1].legend(
                title="Legend",
                loc="upper right",
                fontsize=6,
                title_fontsize=6,
                frameon=True,
                facecolor="white",
                edgecolor="black",
            )

        def plot_cum_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots cumulative displacement data on the third axis.

            :param plot_data: List of tuples containing cumulative displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y = plot_data[0][0]
            x = dates
            self.axs[2].scatter(
                x,
                y,
                s=6,
                color="black",
            )

        def plot_avg_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots average cumulative displacement data on the third axis.

            :param plot_data: List of tuples containing average cumulative displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """

            y = plot_data[0][0]
            x = dates
            self.axs[2].plot(
                x,
                y,
                color="red",
                linewidth=1,
            )

        def plot_std_disp_graph(
            self, avg_data: list[tuple], std_data: list[tuple], dates: list[datetime]
        ):
            """Plots standard deviation of cumulative displacement data on the third axis.

            :param avg_data: List of tuples containing average cumulative displacement values.
            :type avg_data: list[tuple]
            :param std_data: List of tuples containing standard deviation of cumulative displacement values.
            :type std_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y_avg = avg_data[0][0]
            y_std = std_data[0][0]
            x = dates
            self.axs[2].fill_between(
                x,
                [y_avg[i] - 2 * y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + 2 * y_std[i] for i in range(len(y_avg))],
                color="dimgray",
                alpha=0.5,
                # label="±2 Std Dev",
            )
            self.axs[2].fill_between(
                x,
                [y_avg[i] - y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + y_std[i] for i in range(len(y_avg))],
                color="lightgrey",
                alpha=0.5,
                # label="±1 Std Dev",
            )

        def plot_lcp_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots LCP displacement data on the fifth axis.

            :param plot_data: List of tuples containing LCP displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y = plot_data[0][0]
            x = dates
            self.axs[4].scatter(
                x,
                y,
                s=6,
                color="black",
            )

        def plot_avg_lcp_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots average LCP displacement data on the fifth axis.

            :param plot_data: List of tuples containing average LCP displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y = plot_data[0][0]
            x = dates
            self.axs[4].plot(
                x,
                y,
                color="red",
                linewidth=1,
            )

        def plot_std_lcp_disp_graph(
            self, avg_data: list[tuple], std_data: list[tuple], dates: list[datetime]
        ):
            """Plots standard deviation of LCP displacement data on the fifth axis.

            :param avg_data: List of tuples containing average LCP displacement values.
            :type avg_data: list[tuple]
            :param std_data: List of tuples containing standard deviation of LCP displacement values.
            :type std_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y_avg = avg_data[0][0]
            y_std = std_data[0][0]
            x = dates
            self.axs[4].fill_between(
                x,
                [y_avg[i] - 2 * y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + 2 * y_std[i] for i in range(len(y_avg))],
                color="dimgray",
                alpha=0.5,
                # label="±2 Std Dev",
            )
            self.axs[4].fill_between(
                x,
                [y_avg[i] - y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + y_std[i] for i in range(len(y_avg))],
                color="whitesmoke",
                alpha=0.5,
                # label="±1 Std Dev",
            )

        def plot_rel_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots relative displacement data on the fourth axis.

            :param plot_data: List of tuples containing relative displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y = plot_data[0][0]
            x = dates
            self.axs[3].scatter(
                x,
                y,
                s=6,
                color="black",
            )

        def plot_avg_rel_disp_graph(
            self, plot_data: list[tuple], dates: list[datetime]
        ) -> None:
            """Plots average relative displacement data on the fourth axis.

            :param plot_data: List of tuples containing average relative displacement values.
            :type plot_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y = plot_data[0][0]
            x = dates
            self.axs[3].plot(
                x,
                y,
                color="red",
                linewidth=1,
            )

        def plot_std_rel_disp_graph(
            self, avg_data: list[tuple], std_data: list[tuple], dates: list[datetime]
        ):
            """Plots standard deviation of relative displacement data on the fourth axis.

            :param avg_data: List of tuples containing average relative displacement values.
            :type avg_data: list[tuple]
            :param std_data: List of tuples containing standard deviation of relative displacement values.
            :type std_data: list[tuple]
            :param dates: List of datetime objects corresponding to the displacement values.
            :type dates: list[datetime]
            """
            y_avg = avg_data[0][0]
            y_std = std_data[0][0]
            x = dates
            self.axs[3].fill_between(
                x,
                [y_avg[i] - 2 * y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + 2 * y_std[i] for i in range(len(y_avg))],
                color="dimgray",
                alpha=0.5,
                # label="±2 Std Dev",
            )
            self.axs[3].fill_between(
                x,
                [y_avg[i] - y_std[i] for i in range(len(y_avg))],
                [y_avg[i] + y_std[i] for i in range(len(y_avg))],
                color="whitesmoke",
                alpha=0.5,
                # label="±1 Std Dev",
            )

        def outlier_color_label(self, value: float) -> tuple[str, str]:
            """Returns color and label based on outlier velocity value.

            :param value: Outlier velocity value.
            :type value: float
            :return: Tuple containing color and label.
            :rtype: tuple[str, str]
            """
            if value <= 7:
                return "yellow", "5<|v|<7 mm/yr"
            elif value <= 9:
                return "orange", "7<|v|<9 mm/yr"
            else:
                return "red", "9<|v|<12 mm/yr"

        def post_process(self):
            """Post-processes the figure for better aesthetics."""
            for i in [0, 1]:
                xticks = self.axs[i].get_xticks()
                yticks = self.axs[i].get_yticks()
                self.axs[i].set_xticks(xticks[::3])  # Keep every other tick
                self.axs[i].set_xticklabels(self.axs[i].get_xticks())
                self.axs[i].set_yticks(yticks[::3])  # Keep every other tick
                self.axs[i].set_yticklabels(self.axs[i].get_yticks())

            ymins, ymaxs = [], []

            for ax in [self.axs[2], self.axs[3], self.axs[4]]:
                ymin, ymax = ax.get_ylim()
                ymins.append(ymin)
                ymaxs.append(ymax)

            for ax in [self.axs[2], self.axs[3], self.axs[4]]:
                ax.set_ylim(min(ymins), max(ymaxs))
                ax.xaxis.set_major_locator(mdates.YearLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
                ax.xaxis.set_minor_locator(mdates.MonthLocator())

        def get_figure(self) -> tuple[plt.Figure, list[plt.Axes]]:
            """Returns the figure and axes.

            :return: Tuple containing the figure and axes.
            :rtype: tuple[plt.Figure, list[plt.Axes]]
            """
            return self.fig, self.axs
