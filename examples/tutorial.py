from saferoad import SafeRoad, PsData, Road

# define the SafeRoad object

SR = SafeRoad(
    road=Road(filepath="./fixtures/A10_ams.geojson", crs_code="EPSG:4326", name="road"),
    ps_data=PsData(
        filepath="./fixtures/psdata_synthetisch.csv",
        latitude="pnt_lat",
        longitude="pnt_lon",
        unit="m",
        crs_code="EPSG:4326",
    ),
    computational_crs="EPSG:28992",
)

# laoding the data into database
SR.load_files()

# applying preprocess steps
SR.preprocess()

# generating patches
SR.generate_rectangles(road_width=8, segment_length=500)

# run the analysis
SR.run_analysis()

# generate the report
SR.generate_report(output_name="./SafeRoadDB/SafeRoadReport.pdf")
