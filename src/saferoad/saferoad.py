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
