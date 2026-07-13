from pyspark.sql.functions import col, to_date


def get_trip_duration_mins(spark, df, started_col, ended_col, new_col):
    return df.withColumn(new_col, (col(ended_col).cast("long") - col(started_col).cast("long")) / 60.0)


def timestamp_to_date_col(spark, df, timestamp_col, new_col):
    """
    Extracts the date from a timestamp column and adds it as a new column in the DataFrame.

    Parameters:
        spark: Spark Session.
        df (DataFrame): Input PySpark DataFrame containing the timestamp.
        timestamp_col (str): The name of the column containing the timestamp.
        output_col (str): The name for the output column with the ride date.

    Returns:
        DataFrame: A new DataFrame with the additional ride date column.
    """
    # Use to_date to extract the date part of the timestamp
    return df.withColumn(new_col, to_date(col(timestamp_col)))
