from pathlib import Path


class Pipeline:
    class Processing:
        """Processing class for processing road data.

        This class provides methods to load files into a database, dissolve features,
        split lines into segments, generate patches, and save tables as GeoJSON files.
        It assumes that the database connection is already established and that the
        necessary SQL functions for spatial operations are available.
        The methods in this class generate SQL queries that can be executed against
        a spatial database, such as DuckDB.

        The class does not handle database connections or query execution directly;
        it only generates the SQL queries as strings.
        The methods are static and can be called without instantiating the class.
        The class is designed to be used in a pipeline for processing road data,
        where each method can be chained together to perform a series of operations
        on the road data.

        The methods assume that the input data is already in a suitable format for
        processing, such as a GIS vector file for loading into a database or a table
        containing road geometries for dissolving and segmenting.
        The class is intended to be used in conjunction with a spatial database
        that supports SQL queries for spatial operations, such as DuckDB with
        the Spatial extension or PostGIS.
        The methods are designed to be flexible and can be adapted to different
        use cases by modifying the parameters passed to them.
        """

        @staticmethod
        def load_file(file_path: str, table_name: str) -> str:
            """Load a file into a database table.

            Method validates the provided file path and determines if existing
            and determines the appropriate loading method based on the file type.


            :param file_path: The path to the file to be loaded.
            :type file_path: str
            :param table_name: The name of the table to create or replace in the database.
            :type table_name: str

            :raises AssertionError: If the file does not exist.
            :return: SQL query string to create or replace the table with the file data.
            :rtype: str

            """

            assert Path(file_path).exists(), f"File {file_path} does not exist."

            loader_method = (
                "read_csv_auto" if Path(file_path).suffix == ".csv" else "ST_Read"
            )
            query = f"""
            CREATE OR REPLACE TABLE '{table_name}' AS SELECT * FROM {loader_method}('{file_path}');
            CREATE OR REPLACE SEQUENCE {table_name}_id;
            ALTER TABLE '{table_name}' ADD COLUMN uid INTEGER DEFAULT nextval('{table_name}_id');
            """
            return query

        @staticmethod
        def dissolve_features(attribute: str, table_name: str) -> str:
            """Dissolve features in a table based on a specified attribute.

            This method generates an SQL query to dissolve features in a table
            based on the provided attribute. It assumes the table is already loaded
            into the database.

            :param attribute: The attribute to dissolve features by.
            :type attribute: str
            :param table_name: The name of the table containing the features, default is "road".
            :type table_name: str

            :return: SQL query string to dissolve features.
            :rtype: str
            """

            group_expression = f"GROUP BY {attribute}, " if attribute else ""

            return f"""
                CREATE OR REPLACE TABLE dissolved AS
                SELECT UNNEST(ST_Dump(ST_LineMerge(ST_Union_Agg(geom))), recursive := true) as geom
                FROM {table_name} {group_expression}
                """

        @staticmethod
        def split_to_segments(
            segment_length: float, table_name: str = "dissolved"
        ) -> str:
            """Split lines into segments of a specified length.

            This method generates an SQL query to split lines in a table into segments
            of a specified length. It transforms the geometries to a computational
            coordinate reference system (CRS) and calculates the lengths in meters.
            The segments are created by generating windows of fixed length along the lines.
            The resulting segments are stored in a new table named "segments".
            The method assumes that the input table is already dissolved and contains
            geometries in a suitable format.

            The segments are created by cutting the lines into fixed-length segments
            and filtering out any empty geometries.
            This method is useful for preparing road segments for further analysis or processing.
            It is particularly useful in road network analysis, where roads need to be
            divided into manageable segments for tasks such as traffic analysis, road condition
            assessment, or infrastructure planning.

            :param segment_length: The length of each segment in meters.
            :type segment_length: float
            :param computational_crs: The coordinate reference system to use for calculations.
            :type computational_crs: str
            :param table_name: The name of the table containing the lines, default is "dissolved".
            :type table_name: str
            :return: SQL query string to create or replace the segments table.
            :rtype: str
            """
            computational_crs = None
            query = f"""
            CREATE OR REPLACE TABLE segments AS
            -- transform to local projection system
            -- and calculate length in meters
            WITH measured AS (
            SELECT  
                -- ST_Transform(geom, 'EPSG:4326', '{computational_crs}', always_xy := true) AS geom_m,
                -- ST_Length(ST_Transform(geom, 'EPSG:4326', '{computational_crs}', always_xy := true)) AS len_m
                geom,
                ST_Length(geom) AS len_m
            FROM {table_name}
            ),
            -- generate windows of fixed length
            windows AS (
            SELECT
                
                m.geom,
                m.len_m,
                -- start distance (meters)
                (i * CAST({segment_length} AS DOUBLE)) AS s,
                -- end distance (meters), capped at total length
                LEAST((i + 1) * CAST({segment_length} AS DOUBLE), m.len_m) AS e
            FROM measured AS m
            JOIN LATERAL generate_series(
                0,
                CAST(CEIL(m.len_m / CAST({segment_length} AS DOUBLE)) AS BIGINT) - 1
            ) AS g(i) ON TRUE
            WHERE m.len_m > 0
            ),
            -- cut the lines into segments
            cut AS (
            SELECT
                
                ST_LineSubstring(
                geom,
                s / NULLIF(len_m, 0),
                e / NULLIF(len_m, 0)
                ) AS geom
            FROM windows
            WHERE len_m > 0
            )
            -- filter out empty geometries
            SELECT
            geom
            FROM cut
            WHERE NOT ST_IsEmpty(geom);
            """
            return query

        @staticmethod
        def generate_patches(
            width: float, length: float, table_name: str = "segments"
        ) -> str:
            """Generate patches from segments.

            This method generates patches from segments by creating a rectangular
            envelope around each segment, rotated to align with the segment's direction.
            The patches are created by translating and rotating the envelope to the
            start point of the segment, ensuring that each patch is oriented correctly
            along the segment's direction.

            :param width: The width of the patches in meters.
            :type width: float
            :param length: The length of the patches in meters.
            :type length: float
            :param table_name: The name of the table containing the segments, default is "segments".
            :type table_name: str
            :return: SQL query string to create or replace the patches table.
            :rtype: str
            """
            assert width > 0, "Width must be greater than 0."
            assert length > 0, "Length must be greater than 0."
            query = f"""
            CREATE OR REPLACE TABLE patches AS
            SELECT 
                ST_Translate(
                ST_RotateZ(
                    ST_MakeEnvelope(-{width} / 2, 0, {width} / 2, {length}),
                    -ST_Azimuth(ST_StartPoint(geom), ST_EndPoint(geom))
                ),
                ST_X(ST_StartPoint(geom)), ST_Y(ST_StartPoint(geom))
                ) AS geom
            FROM {table_name};
            CREATE OR REPLACE SEQUENCE patches_id;
            ALTER TABLE patches ADD COLUMN uid INTEGER DEFAULT nextval('patches_id');
            """
            return query

        # @staticmethod
        # def save_table_as_geojson(table_name: str, output_path: str) -> str:
        #     """Save a table as a GeoJSON file.
        #     This method generates an SQL query to save the contents of a table
        #     as a GeoJSON file. It assumes that the table contains geometries in a
        #     format compatible with GeoJSON and that the output path is a valid file path.

        #     :param table_name: The name of the table to save as GeoJSON.
        #     :type table_name: str
        #     :param output_path: The path where the GeoJSON file will be saved.
        #     :type output_path: str
        #     :raises AssertionError: If the output path does not exist.
        #     :return: SQL query string to save the table as a GeoJSON file.
        #     :rtype: str
        #     """
        #     assert Path(
        #         output_path
        #     ).parent.exists(), f"Directory {Path(output_path).parent} does not exist."

        #     return f"""
        #     COPY (SELECT * FROM {table_name}) TO '{output_path}' (FORMAT GDAL, DRIVER 'GeoJSON', OVERWRITE TRUE);
        #     """

        @staticmethod
        def spatial_tranformation(
            source_epsg: str, target_epsg: str, table_name: str
        ) -> str:
            """Transform geometries from one EPSG code to another.

            This method generates an SQL query to transform geometries in a table
            from one EPSG code to another. It assumes that the input table contains
            geometries in the source EPSG code and that the target EPSG code is valid.

            :param source_epsg: The source EPSG code of the geometries.
            :type source_epsg: str
            :param target_epsg: The target EPSG code to transform the geometries to.
            :type target_epsg: str
            :param table_name: The name of the table containing the geometries, default is "patches".
            :type table_name: str

            :return: SQL query string to transform the geometries.
            :rtype: str
            """

            return f"""
            UPDATE '{table_name}' SET geom = ST_Transform(geom, '{source_epsg}', '{target_epsg}', always_xy := true);
            """

        @staticmethod
        def build_geometry(latitude: str, longitude: str, table_name: str) -> str:
            """Build a geometry from latitude and longitude coordinates.

            This method generates an SQL query to build a geometry column in a table
            from latitude and longitude coordinates. It assumes that the input table
            contains columns for latitude and longitude.

            :param latitude: The name of the column containing latitude values.
            :type latitude: str
            :param longitude: The name of the column containing longitude values.
            :type longitude: str
            :param table_name: The name of the table to add the geometry column to.
            :type table_name: str
            :return: SQL query string to build the geometry column.
            :rtype: str
            """
            return f"""
            ALTER TABLE {table_name} ADD COLUMN geom GEOMETRY;
            UPDATE {table_name} SET geom = ST_Point({longitude}, {latitude});    
            """

        @staticmethod
        def relate_point_patches(point_name: str, patch_name: str = "patches") -> str:
            """Relate points to patches by assigning patch IDs to points.

            This method generates an SQL query to relate points in one table to patches
            in another table by assigning patch IDs to points based on their spatial
            relationship. It assumes that the point table contains a geometry column
            and that the patch table contains a geometry column and a unique identifier
            for each patch.

            :param point_name: The name of the table containing the points.
            :type point_name: str
            :param patch_name: The name of the table containing the patches, default is "patches".
            :type patch_name: str
            :return: SQL query string to relate points to patches.
            :rtype: str
            """
            return f"""
            ALTER TABLE {point_name} ADD COLUMN patch_id INTEGER;
            UPDATE {point_name}
            SET patch_id = subquery.uid
            FROM (
                SELECT first.uid AS point_uid, second.uid AS uid
                FROM {point_name} AS first
                JOIN {patch_name} AS second
                ON ST_Within(first.geom, second.geom)
            ) AS subquery
            WHERE {point_name}.uid = subquery.point_uid;
            """

        @staticmethod
        def calc_point_density(point_name: str, patch_name: str = "patches") -> str:
            """Calculate point density per patch.

            This method generates an SQL query to calculate the point density per patch
            by counting the number of points within each patch and dividing by the area
            of the patch in square kilometers. It assumes that the point table contains
            a geometry column and that the patch table contains a geometry column and
            a unique identifier for each patch.

            :param point_name: The name of the table containing the points.
            :type point_name: str
            :param patch_name: The name of the table containing the patches, default is "patches".
            :type patch_name: str
            :return: SQL query string to calculate point density per patch.
            :rtype: str
            """
            return f"""
            -- calculate the point count and density per patch
            ALTER TABLE {patch_name} ADD COLUMN point_count INTEGER;
            ALTER TABLE {patch_name} ADD COLUMN ps_density FLOAT DEFAULT 0.0;

            UPDATE {patch_name}
            SET point_count = subquery.point_count,
                ps_density = subquery.point_count / (ST_Area(subquery.geom) / 1_000_000.0)
            FROM (
                SELECT second.uid AS patch_id, COUNT(first.uid) AS point_count, second.geom
                FROM {point_name} AS first
                JOIN {patch_name} AS second
                ON ST_Within(first.geom, second.geom)
                GROUP BY second.uid, second.geom
            ) AS subquery
            WHERE {patch_name}.uid = subquery.patch_id;
            """

        @staticmethod
        def get_column_names(table_name: str) -> str:
            """Get column names from a table.

            This method generates an SQL query to retrieve the column names from a specified table.

            :param table_name: The name of the table to retrieve column names from.
            :type table_name: str
            :return: SQL query string to get the column names.
            :rtype: str
            """
            return f"""
            SELECT column_name FROM (DESCRIBE {table_name});
            """

        @staticmethod
        def calc_cum_disp(dates: list[str], table_name: str = "pspoint") -> str:
            """Calculate cumulative displacement.

            This method generates an SQL query to calculate the cumulative displacement
            for each point in a table based on the provided date fields. It assumes that
            the input table contains columns for displacement values at different dates.

            :param dates: List of column names representing dates.
            :type dates: list[str]
            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate cumulative displacement.
            :rtype: str
            """
            return f"""
            ALTER TABLE {table_name} ADD COLUMN displacement FLOAT;
            UPDATE {table_name}
            SET displacement = first.disp
            FROM (
                SELECT uid, {dates[-1]} - {dates[0]} as disp 
                FROM {table_name}
            ) as first
            JOIN {table_name} as second
            ON first.uid = second.uid
            WHERE {table_name}.uid = first.uid;            
            """

        @staticmethod
        def calc_avg_cum_disp() -> str:
            """Calculate average cumulative displacement per patch.

            This method generates an SQL query to calculate the average cumulative
            displacement for each patch by averaging the displacement values of points
            within each patch. It assumes that the point table contains a geometry column,
            a displacement column, and that the patch table contains a geometry column
            and a unique identifier for each patch.

            :return: SQL query string to calculate average cumulative displacement per patch.
            :rtype: str
            """
            return f"""
            ALTER TABLE patches ADD COLUMN avg_cum_disp DOUBLE DEFAULT 0.0;
            UPDATE patches
            SET avg_cum_disp = (
                SELECT AVG(displacement)
                FROM pspoint
                WHERE patch_id = patches.uid
            );
            """

        @staticmethod
        def calc_avg_velocity(
            time_vector: list[float],
            field_names: list[str],
            table_name: str = "pspoint",
        ) -> str:
            """Calculate average velocity using linear regression.

            This method generates an SQL query to calculate the average velocity for
            each point in a table using linear regression on displacement values over time.
            It assumes that the input table contains columns for displacement values at different dates and that the time vector is provided in days.

            :param time_vector: List of time differences in days from the first date.
            :type time_vector: list[float]
            :param field_names: List of column names representing displacement values at different dates.
            :type field_names: list[str]
            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate average velocity.
            :rtype: str
            """
            x_vals_sql = "[" + ", ".join(map(str, time_vector)) + "]::DOUBLE[]"

            y_fields_sql = (
                "[" + ", ".join(f"CAST({c} AS DOUBLE)" for c in field_names) + "]"
            )

            return f"""
            ALTER TABLE {table_name} ADD COLUMN avg_velocity_gcp DOUBLE;
            WITH pairs AS (
                SELECT 
                    uid,
                    list_element({y_fields_sql}, idx) as y,
                    list_element({x_vals_sql}, idx) as x,
                    patch_id
                FROM {table_name}
                CROSS JOIN UNNEST(range(1, {len(field_names)} + 1)) AS u(idx)
                WHERE patch_id IS NOT NULL
            ),
            slopes AS (
                SELECT 
                    uid,
                    regr_slope(y, x) AS slope
                FROM pairs
                WHERE y IS NOT NULL AND x IS NOT NULL
                GROUP BY uid
            )
            UPDATE {table_name} AS t
            SET avg_velocity_gcp = s.slope * 365.25 -- convert from per day to per year
            FROM slopes AS s
            WHERE t.uid = s.uid;
            """

        @staticmethod
        def calc_avg_disp_ts_gcp(date_fields: list[str]):
            """Calculate average displacement time series for patches (Average Local Displacement (ALD)).

            This method generates an SQL query to calculate the average displacement
            time series for each patch by averaging the displacement values of points within each patch for the specified date fields.
            It assumes that the point table contains a geometry column, displacement columns for each date field, and that the patch table contains a geometry column and a unique identifier for each patch.

            :param date_fields: List of column names representing displacement values at different dates.
            :type date_fields: list[str]
            :return: SQL query string to calculate average displacement time series per patch.
            :rtype: str
            """
            expression = ", ".join([f"AVG({i})" for i in (date_fields)])

            return f"""
            ALTER TABLE patches ADD COLUMN avg_disp_ts_gcp DOUBLE[];
            UPDATE patches
            SET avg_disp_ts_gcp = subquery.disp_ts
            FROM (
                SELECT 
                    patch_id,
                    ARRAY[{expression}] AS disp_ts
                FROM pspoint
                WHERE patch_id IS NOT NULL
                GROUP BY patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def calc_std_disp_ts_gcp(date_fields: list[str]):
            """Calculate standard deviation of displacement time series for patches based on global control point (GCP).

            This method generates an SQL query to calculate the standard deviation
            of displacement time series for each patch by computing the standard deviation of displacement values of points within each patch for the specified date fields.

            :param date_fields: List of column names representing displacement values at different dates.
            :type date_fields: list[str]
            :return: SQL query string to calculate standard deviation of displacement time series per patch.
            :rtype: str
            """

            expression = ", ".join([f"stddev_pop({i})" for i in (date_fields)])

            return f"""
            ALTER TABLE patches ADD COLUMN std_disp_ts_gcp DOUBLE[];
            UPDATE patches
            SET std_disp_ts_gcp = subquery.disp_ts
            FROM (
                SELECT 
                    patch_id,
                    ARRAY[{expression}] AS disp_ts
                FROM pspoint
                WHERE patch_id IS NOT NULL
                GROUP BY patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def select_lcps(table_name: str = "pspoint") -> str:
            """Select linear control points (LCPs) for patches.

            This method generates an SQL query to select linear control points (LCPs) for each patch by identifying the point with the minimum absolute average velocity within each patch.

            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to select LCPs for patches.
            :rtype: str
            """

            return f"""
            ALTER TABLE patches ADD COLUMN lcp_uid INTEGER;
            WITH min_velocities AS (
                SELECT 
                    patch_id,
                    MIN(ABS(avg_velocity_gcp)) AS min_velocity
                FROM {table_name}
                WHERE patch_id IS NOT NULL
                GROUP BY patch_id
            )
            UPDATE patches
            SET lcp_uid = subquery.uid
            FROM (
                SELECT
                    p.patch_id,
                    p.uid
                FROM {table_name} AS p
                JOIN min_velocities AS mv 
                ON p.patch_id = mv.patch_id 
                AND ABS(p.avg_velocity_gcp) = mv.min_velocity
            ) AS subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def calc_lcp_velocity() -> str:
            """Calculate LCP velocity for patches.

            This method generates an SQL query to calculate the velocity of the linear control point (LCP) for each patch by retrieving the average velocity of the point identified as the LCP.

            :return: SQL query string to calculate LCP velocity for patches.
            :rtype: str
            """
            return f""" 
            ALTER TABLE patches ADD COLUMN lcp_velocity FLOAT;
            WITH subquery AS (
                SELECT patch_id, avg_velocity_gcp
                FROM pspoint
                WHERE uid IN (
                    SELECT lcp_uid 
                    FROM patches 
                    WHERE lcp_uid IS NOT NULL
                )
            )
            UPDATE patches
            SET lcp_velocity = subquery.avg_velocity_gcp
            FROM subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def calc_avg_velocity_gcp(table_name: str = "pspoint") -> str:
            """Calculate average velocity based on ground control points (GCPs) for patches.

            This method generates an SQL query to calculate the average velocity for each patch based on the average velocities of points within each patch.

            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate average velocity based on GCPs for patches.
            :rtype: str
            """

            return f""" 
            ALTER TABLE patches ADD COLUMN avg_gcp_velocity FLOAT;
            UPDATE patches
            SET avg_gcp_velocity = subquery.avg_vel 
            FROM (
                SELECT
                    patch_id,
                    AVG(avg_velocity_gcp) AS avg_vel
                FROM {table_name}
                WHERE patch_id IS NOT NULL
                GROUP BY patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id 
            """

        @staticmethod
        def calc_avg_std_disp_ts_lcp(
            date_fields: list[str], table_name: str = "pspoint"
        ) -> str:
            """Calculate average and standard deviation of displacement time series based on LCPs.

            This method generates an SQL query to calculate the average and standard
            deviation of displacement time series for each patch based on the displacement
            values of points within each patch relative to the local control point (LCP).
            It assumes that the point table contains columns for displacement values at
            different dates and that the patch table contains a geometry column and a unique
            identifier for each patch.

            :param date_fields: List of column names representing displacement values at different dates.
            :type date_fields: list[str]
            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate average and standard deviation of displacement time series based on LCPs.
            :rtype: str
            """
            expression_to_select_date_fields = (
                "[" + ", ".join([i for i in date_fields]) + "]"
            )
            indices = range(1, len(date_fields) + 1)
            expression_to_explode = ",".join(
                f"list_extract(displacement, {i}) as {date_fields[i-1]}"
                for i in indices
            )
            expresion_for_avg_per_date = ", ".join([f"AVG({i})" for i in date_fields])
            expresion_for_std_per_date = ", ".join(
                [f"stddev_pop({i})" for i in date_fields]
            )
            return f"""
            ALTER TABLE patches ADD COLUMN avg_disp_ts_lcp DOUBLE[];
            ALTER TABLE patches ADD COLUMN std_disp_ts_lcp DOUBLE[];
            WITH y as (
                SELECT patch_id, {expression_to_select_date_fields} as y
                FROM {table_name}
                WHERE patch_id IS NOT NULL
            ),
            x as (
                SELECT patch_id, {expression_to_select_date_fields} as x
                FROM {table_name}
                WHERE uid IN (SELECT lcp_uid FROM patches WHERE lcp_uid IS NOT NULL)
            ),
            process as (
                SELECT
                    x.patch_id,
                    list_transform(list_zip(y.y, x.x), arr -> arr[1] - arr[2]) as displacement
                FROM x
                JOIN y
                ON x.patch_id = y.patch_id
            ),
            exploded AS (
                SELECT
                    patch_id,
                    {expression_to_explode}
                FROM process
            ),
            final AS (
                SELECT 
                    patch_id,
                    ARRAY[{expresion_for_avg_per_date}] AS avg_disp_ts_lcp,
                    ARRAY[{expresion_for_std_per_date}] AS std_disp_ts_lcp
                FROM exploded
                GROUP BY patch_id
            )
            UPDATE patches
            SET avg_disp_ts_lcp = final.avg_disp_ts_lcp,
                std_disp_ts_lcp = final.std_disp_ts_lcp
            FROM final
            WHERE patches.uid = final.patch_id;
            """

        @staticmethod
        def calc_avg_velocity_lcp(table_name: str = "pspoint") -> str:
            """Calculate average velocity based on local control points (LCPs) for points.

            This method generates an SQL query to calculate the average velocity for each point
            based on the average velocity of the local control point (LCP) associated with the patch
            to which the point belongs. It assumes that the point table contains a geometry column,
            an average velocity column based on ground control points (GCPs), and that the patch table
            contains a geometry column, a unique identifier for each patch, and the average velocity
            of the LCP.

            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate average velocity based on LCPs for points.
            :rtype: str
            """
            return f"""
            ALTER TABLE {table_name} ADD COLUMN avg_velocity_lcp DOUBLE;
            WITH y AS (
                SELECT uid, patch_id, avg_velocity_gcp
                FROM {table_name}
                WHERE patch_id IS NOT NULL
            ),
            x AS (
                SELECT uid, lcp_velocity, lcp_uid
                FROM patches
                WHERE lcp_uid IS NOT NULL
            )
            UPDATE {table_name}
            SET avg_velocity_lcp = subquery.avg_velocity_lcp
            FROM (
                SELECT 
                    y.avg_velocity_gcp - x.lcp_velocity AS avg_velocity_lcp, 
                    y.uid as uid
                FROM x
                JOIN y ON x.uid = y.patch_id
            ) AS subquery
            WHERE {table_name}.uid = subquery.uid;
            """

        @staticmethod
        def calc_avg_lcp_velocity(table_name: str = "pspoint") -> str:
            """Calculate average LCP velocity per patch.

            This method generates an SQL query to calculate the average velocity of
            local control points (LCPs) for each patch by averaging the average velocities
            of points within each patch based on their LCP velocities.

            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :return: SQL query string to calculate average LCP velocity per patch.
            :rtype: str
            """
            return f"""
            ALTER TABLE patches ADD COLUMN avg_lcp_velocity FLOAT;
            UPDATE patches
            SET avg_lcp_velocity = subquery.avg_vel
            FROM (
                SELECT
                    patch_id,
                    AVG(avg_velocity_lcp) as avg_vel
                FROM {table_name}
                WHERE patch_id IS NOT NULL
                GROUP BY patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id
            """

        @staticmethod
        def calc_outliers(scaling_factor: float, table_name: str = "pspoint") -> str:
            """Identify outlier points based on absolute average velocity.

            This method generates an SQL query to identify outlier points based on their
            average velocity relative to local control points (LCPs). Points with an absolute
            average LCP velocity exceeding a specified threshold (5 mm/year) are
            marked as outliers by assigning their unique identifier to a new column in the
            patches table. The unit parameter allows for specifying the measurement unit
            (meters, centimeters, or millimeters) to appropriately scale the threshold.

            :param unit: The measurement unit for velocity ("m", "cm", or "mm").
            :type unit: str
            :param table_name: The name of the table containing the points, default is "pspoint".
            :type table_name: str
            :raises ValueError: If the provided unit is not recognized.
            :return: SQL query string to identify outlier points.
            :rtype: str
            """

            return f""" 
            ALTER TABLE patches ADD COLUMN outlier_uid INTEGER;
            WITH subquery AS (
                SELECT
                    patch_id,
                    uid,
                FROM {table_name}
                WHERE ABS(avg_velocity_lcp) > 5 / {scaling_factor} 
                QUALIFY ROW_NUMBER() OVER 
                (         
                    PARTITION BY patch_id
                    ORDER BY ABS(avg_velocity_lcp) DESC
                ) = 1
            )
            UPDATE patches
            SET outlier_uid = subquery.uid
            FROM subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def lcp_ts_patch(date_fields: list[str], table_name: str = "pspoint"):
            date_fields_str = "[" + ", ".join(date_fields) + "]"
            return f"""
            ALTER TABLE patches ADD COLUMN lcp_disp_ts DOUBLE[];
            UPDATE patches
            SET lcp_disp_ts = subquery.disp_ts
            FROM (
                SELECT 
                    p.patch_id,
                    {date_fields_str} AS disp_ts
                FROM {table_name} AS p
                JOIN patches AS pa
                ON p.uid = pa.lcp_uid
                WHERE p.patch_id IS NOT NULL
                -- GROUP BY p.patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id;
            """

        def outlier_ts_patch(date_fields: list[str], table_name: str = "pspoint"):
            date_fields_str = "[" + ", ".join(date_fields) + "]"
            return f"""
            ALTER TABLE patches ADD COLUMN outlier_disp_ts DOUBLE[];
            UPDATE patches
            SET outlier_disp_ts = subquery.disp_ts
            FROM (
                SELECT 
                    p.patch_id,
                    {date_fields_str} AS disp_ts
                FROM {table_name} AS p
                JOIN patches AS pa
                ON p.uid = pa.outlier_uid
                WHERE p.patch_id IS NOT NULL
                -- GROUP BY p.patch_id
            ) AS subquery
            WHERE patches.uid = subquery.patch_id;
            """

        @staticmethod
        def outlier_rel_ts_patch():
            return f"""
            ALTER TABLE patches ADD COLUMN outlier_rel_ts DOUBLE[];
            UPDATE patches
            SET outlier_rel_ts = list_transform(
                outlier_disp_ts, 
                (value, idx) -> value - list_element(lcp_disp_ts, idx)
            )
            WHERE outlier_disp_ts IS NOT NULL AND lcp_disp_ts IS NOT NULL;          
            """

    class Visualisation:
        """SQL queries for visualisation of results.

        2D visualisation is done in Web Mercator (EPSG:3857).
        """

        projection = "EPSG:3857"

        @staticmethod
        def get_table_bbox(table_name: str, source_crs: str) -> str:
            """Get the bounding box of a table in a specified projection.

            This method generates an SQL query to retrieve the bounding box of geometries
            from a specified table, transforming the geometries from a source CRS to
            a target projection defined in the Visualisation class.

            :param table_name: The name of the table to get the bounding box from.
            :type table_name: str
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the bounding box of the table.
            :rtype: str"""
            return f"""
            with transformed as (
                SELECT 
                ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true) as geom 
                FROM {table_name}
            )
            SELECT
                MIN(ST_XMIN(geom)) AS min_x,
                MIN(ST_YMIN(geom)) AS min_y,
                MAX(ST_XMAX(geom)) AS max_x,
                MAX(ST_YMAX(geom)) AS max_y
            FROM transformed;
            """

        @staticmethod
        def get_ps_density(source_crs: str) -> str:
            """Get point density per patch.

            This method generates an SQL query to retrieve the point density for each patch,
            transforming the geometries from a source CRS to a target projection defined
            in the Visualisation class.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the point density per patch.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                ps_density
            FROM patches
            """

        @staticmethod
        def get_outliers_map(source_crs: str, scaling_factor: float) -> str:
            """Get outlier points based on absolute average LCP velocity.

            This method generates an SQL query to retrieve outlier points based on their
            average velocity relative to local control points (LCPs). Points with an absolute
            average LCP velocity exceeding a specified threshold (5 mm/year) are
            marked as outliers by assigning their unique identifier to a new column in the
            patches table. The unit parameter allows for specifying the measurement unit
            (meters, centimeters, or millimeters) to appropriately scale the threshold.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :param unit: The measurement unit for velocity ("m", "cm", or "mm").
            :type unit: str
            :return: SQL query string to identify outlier points.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                ABS(avg_velocity_lcp) * {scaling_factor} AS velocity,
            FROM pspoint
            WHERE uid IN (
                SELECT
                    outlier_uid,
                FROM patches
                WHERE outlier_uid IS NOT NULL
            )
            ORDER BY velocity ASC;
            """

        @staticmethod
        def get_cum_disp_map(source_crs: str, scaling_factor: float) -> str:
            """Get cumulative displacement per patch.

            This method generates an SQL query to retrieve the cumulative displacement
            for each patch, transforming the geometries from a source CRS to a target
            projection defined in the Visualisation class.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :param unit: The measurement unit for displacement ("m", "cm", or "mm").
            :type unit: str
            :return: SQL query string to get the cumulative displacement per patch.
            :rtype: str
            """
            # scaling_factor = [1, 100, 1000][["m", "cm", "mm"].index(unit)]
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                avg_cum_disp * {scaling_factor} AS cum_disp
            FROM patches
            WHERE avg_cum_disp IS NOT NULL
            ORDER BY cum_disp ASC;
            """

        @staticmethod
        def get_ps_vel_gcp(source_crs: str, scaling_factor: float) -> str:
            """Get average velocity based on ground control points (GCPs).
            This method generates an SQL query to retrieve the average velocity for
            each point based on ground control points (GCPs), transforming the geometries
            from a source CRS to a target projection defined in the Visualisation class.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :param unit: The measurement unit for velocity ("m", "cm", or "mm").
            :type unit: str
            :return: SQL query string to get the average velocity based on GCPs.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                avg_velocity_gcp * {scaling_factor} AS velocity
            FROM pspoint
            WHERE patch_id IS NOT NULL
            ORDER BY velocity ASC;
            """

        @staticmethod
        def get_ps_vel_lcp(source_crs: str, scaling_factor: float) -> str:
            """Get average velocity based on local control points (LCPs).

            This method generates an SQL query to retrieve the average velocity for
            each point based on local control points (LCPs), transforming the geometries
            from a source CRS to a target projection defined in the Visualisation class.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :param unit: The measurement unit for velocity ("m", "cm", or "mm").
            :type unit: str
            :return: SQL query string to get the average velocity based on LCPs.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                ABS(avg_velocity_lcp) * {scaling_factor} AS velocity
            FROM pspoint
            WHERE patch_id IS NOT NULL
            ORDER BY velocity ASC;
            """

        @staticmethod
        def get_outlier_zoom(source_crs: str) -> str:
            """Get outlier points for zoomed-in view.

            This method generates an SQL query to retrieve outlier points based on their
            average velocity relative to local control points (LCPs). Points with an absolute
            average LCP velocity are retrieved, transforming the geometries from a source CRS
            to a target projection defined in the Visualisation class.

            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the outlier points.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
                ABS(avg_velocity_lcp) AS velocity
            FROM pspoint
            WHERE uid IN (
                SELECT
                    outlier_uid,
                FROM patches
                WHERE outlier_uid IS NOT NULL
            )
            ORDER BY velocity DESC;
            """

        @staticmethod
        def get_ps_points(patch_id: float, source_crs: str, table_name: str) -> str:
            """Get points within a specific patch.
            This method generates an SQL query to retrieve points within a specific patch,
            transforming the geometries from a source CRS to a target projection defined
            in the Visualisation class.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :param table_name: The name of the table containing the points.
            :type table_name: str
            :return: SQL query string to get the points within the specified patch.
            :rtype: str
            """
            return f"""
            SELECT
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom,
            FROM {table_name}
            WHERE patch_id = {patch_id}            
            """

        @staticmethod
        def get_center(patch_id: float, source_crs: str) -> str:
            """Get the center point of the outlier within a specific patch.

            This method generates an SQL query to retrieve the center point of the outlier
            within a specific patch, transforming the geometry from a source CRS to a target
            projection defined in the Visualisation class.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the center point of the outlier within the specified patch.
            """
            return f"""
            SELECT 
                ST_AsWKB(ST_TRANSFORM(ST_Centroid(geom), '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom
            FROM pspoint
            WHERE uid = (
                SELECT outlier_uid 
                FROM patches
                WHERE uid = {patch_id}
            )
            """

        def get_patch_center(patch_id: float, source_crs: str) -> str:
            """Get the center point of a specific patch.

            This method generates an SQL query to retrieve the center point of a specific
            patch,
            transforming the geometry from a source CRS to a target projection defined in the Visualisation class.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the center point of the specified patch.
            """
            return f"""
            SELECT 
                ST_AsWKB(ST_TRANSFORM(ST_Centroid(geom), '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_lcp_point(patch_id: float, source_crs: str) -> str:
            """Get the local control point (LCP) within a specific patch.

            This method generates an SQL query to retrieve the local control point (LCP)
            within a specific patch, transforming the geometry from a source CRS to a target
            projection defined in the Visualisation class.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the LCP within the specified patch.
            """
            return f"""
            SELECT 
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom
            FROM pspoint
            WHERE uid = (
                SELECT lcp_uid 
                FROM patches
                WHERE uid = {patch_id}
            )
            """

        @staticmethod
        def get_outlier_point(patch_id: float, source_crs: str) -> str:
            """Get the outlier point within a specific patch.

            This method generates an SQL query to retrieve the outlier point within a specific patch,
            transforming the geometry from a source CRS to a target projection defined in the Visualisation class.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param source_crs: The source coordinate reference system of the geometries.
            :type source_crs: str
            :return: SQL query string to get the outlier point within the specified patch.
            """
            return f"""
            SELECT 
                ST_AsWKB(ST_TRANSFORM(geom, '{source_crs}', '{Pipeline.Visualisation.projection}', always_xy := true)) AS geom
            FROM pspoint
            WHERE uid = (
                SELECT outlier_uid 
                FROM patches
                WHERE uid = {patch_id}
            )
            """

        @staticmethod
        def get_cum_disp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get outlier displacement time series.

            This method generates an SQL query to retrieve the outlier displacement time series
            for a specific patch, scaling the displacement values by a specified factor.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the outlier displacement time series for the specified patch.
            """
            return f"""
            SELECT
                list_transform(outlier_disp_ts, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_avg_cum_disp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get average cumulative displacement time series.

            This method generates an SQL query to retrieve the average cumulative displacement
            time series for a specific patch, scaling the displacement values by a specified factor.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the average cumulative displacement time series for the specified patch.
            """
            return f"""
            SELECT
                list_transform(avg_disp_ts_gcp, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_std_cum_disp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get standard deviation of cumulative displacement time series.

            This method generates an SQL query to retrieve the standard deviation of cumulative
            displacement time series for a specific patch, scaling the displacement values by a specified factor.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the standard deviation of cumulative displacement time series for the specified patch.
            """
            return f"""
            SELECT
                list_transform(std_disp_ts_gcp, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_lcp_disp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get local control point (LCP) displacement time series.

            This method generates an SQL query to retrieve the local control point (LCP)
            displacement time series for a specific patch, scaling the displacement values by a specified factor.

            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the LCP displacement time series for the specified patch.
            """
            return f"""
            SELECT
                list_transform(lcp_disp_ts, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_avg_disp_lcp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get average displacement time series based on local control points (LCPs).
            This method generates an SQL query to retrieve the average displacement time series
            based on local control points (LCPs) for a specific patch, scaling the displacement
            values by a specified factor.
            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the average displacement time series based on LCPs for the specified patch.
            """
            return f"""
            SELECT
                list_transform(avg_disp_ts_lcp, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def get_std_disp_lcp_graph(patch_id: float, scaling_factor: float) -> str:
            """Get standard deviation of displacement time series based on local control points (LCPs).
            This method generates an SQL query to retrieve the standard deviation of displacement
            time series based on local control points (LCPs) for a specific patch, scaling the
            displacement values by a specified factor.
            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the standard deviation of displacement time series based on LCPs for the specified patch.
            """
            return f"""
            SELECT
                list_transform(std_disp_ts_lcp, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        def get_outlier_rel_ts_graph(patch_id: float, scaling_factor: float) -> str:
            """Get outlier relative displacement time series.
            This method generates an SQL query to retrieve the outlier relative displacement
            time series for a specific patch, scaling the displacement values by a specified factor.
            :param patch_id: The unique identifier of the patch.
            :type patch_id: float
            :param scaling_factor: The factor to scale the displacement values.
            :type scaling_factor: float
            :return: SQL query string to get the outlier relative displacement time series for the specified patch.
            """
            return f"""
            SELECT
                list_transform(outlier_rel_ts, x -> x * {scaling_factor})
            FROM patches
            WHERE uid = {patch_id}
            """

        @staticmethod
        def patch_uids() -> str:
            """Get all patch UIDs that have outliers.

            This method generates an SQL query to retrieve all unique identifiers (UIDs)
            of patches that have been identified as containing outliers.

            :return: SQL query string to get all patch UIDs with outliers.
            :rtype: str
            """
            return """
            SELECT uid 
            FROM patches
            WHERE outlier_uid IS NOT NULL
            ORDER BY uid ASC;
            """
