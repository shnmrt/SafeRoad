# SafeRoad

## About

**SafeRoad** is an open-source Python library designed to monitor the structural condition of the road network by providing tools for data analysis and visualisation.
It aims to assist researchers, policymakers, and developers in understanding and mitigating structural safety issues of road networks.
**SafeRoad** is built with a focus on usability, performance, and extensibility. It uses modern Python libraries such as [duckdb](https://duckdb.org/),
[shapely](https://shapely.readthedocs.io/en/stable/), [matplotlib](https://matplotlib.org/) and [contextily](https://contextily.readthedocs.io/en/latest/) to provide a robust framework for road network safety analyses.

You can access the more detailed description of the methodology from the [paper](https://doi.org/10.1177/14759217211045912).

The library is modular, user-friendly, and well-documented, making it suitable for both beginners and experts in the field of structural safety.

## Installation

1. Create a virtual environment and activate it

```bash
# conda
conda create --name saferoad_env python=3.10
# activate environment
conda activate saferoad_env
```

2. Clone the reposity to your current directory

```bash
git clone https://github.com/SafeStruct/SafeRoad.git
```

3. Install the library from directory using pip

```bash
pip install -e ./SafeRoad
```

4. Testing the installation using tutorial

```bash
# before testing one extension needs to be installed
python -c "import duckdb; duckdb.install_extension('spatial')"
# change the directory to examples and run the tutorial
cd SafeRoad/examples
python tutorial.py
```

If everything works correctly, you should see a folder called **`SafeRoadDB`** inside the example folder. Inside that folder, you will find the generated **PDF** report for the entire dataset provided.

# Disclaimer

The Multi-Temporal SAR data provided in the repository is not real; it is synthetic. It is produced to demonstrate how the tool works and what kind of report it generates.
