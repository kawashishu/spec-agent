import io
import os
from typing import List, Optional

import pandas as pd
import pyarrow.parquet as pq
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from spec.config import settings


class Blob:
    def __init__(self, container_name: Optional[str] = None, account_name: Optional[str] = "blob3dmse", connection_string: str = os.getenv("AZURE_CONNECTION_STRING")):
        if connection_string:
            print(f"Using connection string: {connection_string}")
            self.svc = BlobServiceClient.from_connection_string(connection_string)
        else:
            credential = DefaultAzureCredential()
            self.svc = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=credential
            )
        self.cn = container_name
        self.cc = self.svc.get_container_client(self.cn)

    def upload_file(self, local_path: str, path: str):
        """Upload local file to blob."""
        bc = self.cc.get_blob_client(path)
        with open(local_path, "rb") as f:
            bc.upload_blob(f, overwrite=True)

    def list_files(self, prefix: str = "") -> List[str]:
        """List blob names."""
        return [b.name for b in self.cc.list_blobs(name_starts_with=prefix)]

    def delete_file(self, path: str):
        """Delete a blob."""
        bc = self.cc.get_blob_client(path)
        bc.delete_blob()

    def file_exists(self, path: str) -> bool:
        """Check if blob exists."""
        try:
            bc = self.cc.get_blob_client(path)
            bc.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def _fetch(self, path: str) -> bytes:
        bc = self.cc.get_blob_client(path)
        try:
            return bc.download_blob().readall()
        except ResourceNotFoundError:
            raise ValueError(f"File {path} not found.")

	# for Dataframe
    def get_latest_df(self, filepath: str, use_cols: Optional[List[str]] = None) -> pd.DataFrame:
        """Get DataFrame from largest matching blob (by size)."""
        directory = os.path.dirname(filepath)
        base = os.path.basename(filepath)
        all_files = self.list_files(prefix=directory)
        matches = [x for x in all_files if os.path.basename(x) == base and x.startswith(f"{directory}/")]
        if not matches:
            return pd.DataFrame()
        sizes = []
        for m in matches:
            bc = self.cc.get_blob_client(m)
            sizes.append((m, bc.get_blob_properties().size))
        largest = max(sizes, key=lambda x: x[1])[0]
        return self.get_df(largest, use_cols)

    def _read_parquet(self, path: str, cols: Optional[List[str]] = None) -> pd.DataFrame:
        data = self._fetch(path)
        if not data:
            return pd.DataFrame()
        table = pq.read_table(io.BytesIO(data), columns=cols) if cols else pq.read_table(io.BytesIO(data))
        return table.to_pandas()

    def _read_csv(self, path: str) -> pd.DataFrame:
        data = self._fetch(path)
        if not data:
            return pd.DataFrame()
        return pd.read_csv(io.StringIO(data.decode("utf-8")))

    def upload_df_stream(self, df: pd.DataFrame, path: str):
        """Upload DataFrame to blob (CSV/Parquet)."""
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Data must be a DataFrame.")
        ext = os.path.splitext(path)[1].lower()
        bc = self.cc.get_blob_client(path)
        if ext == ".parquet":
            buf = io.BytesIO()
            df.to_parquet(buf, index=False)
            buf.seek(0)
            bc.upload_blob(buf, overwrite=True)
        elif ext == ".csv":
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            bdata = io.BytesIO(buf.getvalue().encode("utf-8"))
            bdata.seek(0)
            bc.upload_blob(bdata, overwrite=True)
        else:
            raise ValueError("Only .csv or .parquet supported.")
