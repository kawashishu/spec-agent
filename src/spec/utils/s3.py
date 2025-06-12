import io
import os
import threading
from typing import List, Optional

import boto3
import pandas as pd
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()


class S3:
    def __init__(self, bucket_name: Optional[str] = "vf-prd-bom-structure-detection"):
        """
        Initialize the S3 with the specified bucket name.

        Args:
            bucket_name (Optional[str]): The S3 bucket name.
        """
        if "ACCESS_KEY_ID" not in os.environ or "SECRET_ACCESS_KEY" not in os.environ:
            raise ValueError("Missing required environment variables: ACCESS_KEY_ID and/or SECRET_ACCESS_KEY")
            
        self.client = boto3.client(
            "s3",
            aws_access_key_id=os.environ["ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["SECRET_ACCESS_KEY"],
        )
        self.bucket_name = bucket_name

    def get_df(self, s3_path: str, usecol: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Read a file from S3 and return a DataFrame based on the file extension.

        Args:
            s3_path (str): The path to the file in the S3 bucket.
            usecol (Optional[List[str]]): List of columns to read for Parquet files.

        Returns:
            pd.DataFrame: The file content as a DataFrame.

        Raises:
            ValueError: If the file extension is not supported.
        """
        file_extension = os.path.splitext(s3_path)[1].lower()
        if file_extension == ".parquet":
            return self._get_df_from_parquet(s3_path, usecol=usecol)
        elif file_extension == ".csv":
            return self._get_df_from_csv(s3_path)
        else:
            raise ValueError("Unsupported file extension. Use '.csv' or '.parquet'.")

    def get_concat_df_from_folder(
        self, folder_path: str, usecol: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Read all files in a folder from S3 and concatenate them into a single DataFrame.

        Args:
            folder_path (str): The path to the folder in the S3 bucket.
            usecol (Optional[List[str]]): List of columns to read for Parquet files.

        Returns:
            pd.DataFrame: Concatenated DataFrame of all valid files in the folder.
        """
        try:
            all_files = self.list_files(prefix=folder_path)

            if not all_files:
                print(f"No files found in folder '{folder_path}'.")
                return pd.DataFrame()

            dataframes = []
            for file in all_files:
                file_extension = os.path.splitext(file)[1].lower()
                if file_extension in [".parquet", ".csv"]:
                    df = self.get_df(file, usecol)
                    dataframes.append(df)
                else:
                    print(f"Skipping unsupported file type: {file}")

            if dataframes:
                return pd.concat(dataframes, ignore_index=True)
            else:
                print("No valid dataframes found to concatenate.")
                return pd.DataFrame()
        except Exception as e:
            raise RuntimeError(f"Error in get_concat_df_from_folder: {e}")

    def upload_file(self, local_path: str, s3_path: str):
        """
        Upload a file from a local path to the S3 bucket.

        Args:
            local_path (str): The path to the local file.
            s3_path (str): The destination path in the S3 bucket.
        """
        try:
            self.client.upload_file(local_path, self.bucket_name, s3_path)
            print(
                f"File {local_path} uploaded to S3 bucket {self.bucket_name} as {s3_path}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")

    def upload_stream(self, data: pd.DataFrame, s3_path: str):
        """
        Upload a DataFrame as a Parquet or CSV stream to the S3 bucket.

        Args:
            data (pd.DataFrame): The DataFrame to upload.
            s3_path (str): The destination path in the S3 bucket.

        Raises:
            ValueError: If the file extension is not supported.
        """
        try:
            if not isinstance(data, pd.DataFrame):
                raise ValueError("Data must be a pandas DataFrame.")

            file_extension = os.path.splitext(s3_path)[1].lower()
            if file_extension == ".parquet":
                parquet_buffer = io.BytesIO()
                data.to_parquet(parquet_buffer, index=False)
                parquet_buffer.seek(0)
                input_stream = parquet_buffer
            elif file_extension == ".csv":
                csv_buffer = io.StringIO()
                data.to_csv(csv_buffer, index=False)
                input_stream = io.BytesIO(csv_buffer.getvalue().encode("utf-8"))
                input_stream.seek(0)
            else:
                raise ValueError(
                    "Unsupported file extension. Use '.csv' or '.parquet'."
                )

            self.client.upload_fileobj(input_stream, self.bucket_name, s3_path)
            print(f"Stream uploaded to S3 bucket {self.bucket_name} as {s3_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to upload stream to S3: {e}")

    def list_files(self, prefix: str = "") -> List[str]:
        """
        List all objects in the S3 bucket with an optional prefix.

        Args:
            prefix (str, optional): The prefix for filtering objects. Defaults to "".

        Returns:
            List[str]: List of object keys in the S3 bucket matching the prefix.
        """
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            files = []
            for page in page_iterator:
                if "Contents" in page:
                    files.extend([obj["Key"] for obj in page["Contents"]])
            return files
        except Exception as e:
            raise RuntimeError(f"Error in list_files: {e}")

    def delete_file(self, s3_path: str):
        """
        Delete a specific object from the S3 bucket.

        Args:
            s3_path (str): The path to the object in the S3 bucket.
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_path)
            print(f"Object {s3_path} deleted from {self.bucket_name} bucket.")
        except Exception as e:
            raise RuntimeError(f"Error in delete_file: {e}")

    def download_file(self, s3_path: str, local_path: str):
        """
        Download a file from S3 to a local path.

        Args:
            s3_path (str): The path to the file in the S3 bucket.
            local_path (str): The destination path on the local filesystem.
        """
        try:
            self.client.download_file(self.bucket_name, s3_path, local_path)
            print(f"Downloaded '{s3_path}' to local path '{local_path}'")
        except Exception as e:
            raise RuntimeError(f"Failed to download file from S3: {e}")


    def file_exists(self, s3_path: str) -> bool:
        """
        Check if an object exists in the S3 bucket.

        Args:
            s3_path (str): The path to the object in the S3 bucket.

        Returns:
            bool: True if the object exists, False otherwise.
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_path)
            return True
        except self.client.exceptions.NoSuchKey:
            return False
        except self.client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise RuntimeError(f"Error in file_exists: {e}")

    def get_latest_df(
        self, filepath: str, usecol: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get the DataFrame from the latest file based on size, filtered by base filename and directory.

        Args:
            filepath (str): The base file path (directory and filename) to search for.
            usecol (Optional[List[str]]): List of columns to read for Parquet files.

        Returns:
            pd.DataFrame: The DataFrame of the latest file, or an empty DataFrame if no files are found.
        """
        s3_dir = os.path.dirname(filepath)
        base_name = os.path.basename(filepath)
        try:
            all_files = self.list_files(s3_dir)
            filtered_files = [
                file
                for file in all_files
                if os.path.basename(file) == base_name and file.startswith(f"{s3_dir}/")
            ]

            if not filtered_files:
                print(
                    f"No files found with base_name '{base_name}' in s3_dir '{s3_dir}'."
                )
                return pd.DataFrame()

            file_sizes = []
            for file in filtered_files:
                response = self.client.head_object(Bucket=self.bucket_name, Key=file)
                file_sizes.append((file, response["ContentLength"]))

            largest_file = max(file_sizes, key=lambda x: x[1])[0]
            print(f"Largest file found: {largest_file}")

            return self.get_df(largest_file, usecol)
        except Exception as e:
            raise RuntimeError(f"Error in get_latest_df: {e}")

    def _get_df_from_parquet(
        self, s3_path: str, usecol: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Read a Parquet file from S3 and return a DataFrame.

        Args:
            s3_path (str): The path to the Parquet file in the S3 bucket.
            usecol (Optional[List[str]]): List of columns to read.

        Returns:
            pd.DataFrame: The Parquet file content as a DataFrame.
        """
        try:
            s3_data = self._get(s3_path)
            if s3_data is None:
                return pd.DataFrame()

            table = (
                pq.read_table(io.BytesIO(s3_data), columns=usecol)
                if usecol
                else pq.read_table(io.BytesIO(s3_data))
            )
            return table.to_pandas()
        except Exception as e:
            raise RuntimeError(f"Error reading Parquet data from S3: {e}")

    def _get_df_from_csv(self, s3_path: str) -> pd.DataFrame:
        """
        Read a CSV file from S3 and return a DataFrame.

        Args:
            s3_path (str): The path to the CSV file in the S3 bucket.

        Returns:
            pd.DataFrame: The CSV file content as a DataFrame.
        """
        try:
            s3_data = self._get(s3_path)
            if s3_data is None:
                return pd.DataFrame()
            csv_buffer = io.StringIO(s3_data.decode("utf-8"))
            return pd.read_csv(csv_buffer)
        except Exception as e:
            raise RuntimeError(f"Error reading CSV data from S3: {e}")

    def _get(self, s3_path: str) -> Optional[bytes]:
        """
        Fetch the content of an object from S3.

        Args:
            s3_path (str): The path to the object in the S3 bucket.

        Returns:
            Optional[bytes]: The content of the S3 object, or None if the object does not exist.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_path)
            return response["Body"].read()
        except self.client.exceptions.NoSuchKey:
            print(f"S3 path {s3_path} does not exist.")
            return None
        except Exception as e:
            raise RuntimeError(f"Error in get: {e}")
