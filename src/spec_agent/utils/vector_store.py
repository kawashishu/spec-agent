import faiss
import numpy as np
import pickle
import os
import pandas as pd
from typing import List, Dict, Any, Optional
from settings.log import logger
import json
from .llm import LLM
from pydantic_types.type import Chunk
import hashlib
from utils.s3 import S3Manager
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


class VectorStore:
    """
    A class to manage FAISS-based vector storage and retrieval.
    """

    def __init__(
        self,
        pickle_path: Optional[str],
        s3: Optional["S3Manager"] = None,  # S3Manager được truyền vào nếu có
        embedding_dimension: int = 3072,
        llm=LLM,
    ):
        """
        Initialize the VectorStore with FAISS index and metadata mapping.
        """
        self.embedding_dimension = embedding_dimension
        self.embedding_dimension_to_model = {
            3072: "text-embedding-3-large",
            1536: "text-embedding-3-small",
        }
        print(embedding_dimension)
        print(self.embedding_dimension_to_model)
        self.model = self.embedding_dimension_to_model[embedding_dimension]
        self.llm: LLM = llm
        self.pickle_path = pickle_path
        self.s3 = s3  # Lưu lại đối tượng S3 nếu được khởi tạo

        # Initialize FAISS index with ID mapping
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.embedding_dimension))

        # Mapping FAISS ID to metadata
        self.faiss_id_to_metadata: Dict[int, Dict[str, Any]] = {}

        # Nếu có pickle_path thì cố gắng load index
        if self.pickle_path:
            try:
                self.load_index()
                logger.info(f"Loaded VectorStore from '{self.pickle_path}'.")
            except Exception as e:
                logger.warning(
                    f"Failed to load VectorStore from '{self.pickle_path}': {e}. Creating a new VectorStore."
                )
        else:
            logger.warning("No pickle_path provided. Creating a new VectorStore.")

    @staticmethod
    def compute_faiss_id(chunk: Chunk) -> int:
        """
        Compute a deterministic FAISS ID from the chunk content and metadata using SHA256.

        The function combines the content and its associated metadata (converted to a JSON string with sorted keys)
        into a single string, then computes a SHA256 hash. Kết quả hash được chuyển thành số nguyên với giới hạn của int64.

        Args:
            content (str): The content of the chunk.
            metadata (Dict[str, Any]): The metadata associated with the chunk.

        Returns:
            int: A number derived from the hash of the combined content and metadata, modulo the int64 limit.
        """
        modulus = 2**63 - 1  # int64 limit
        # Chuyển metadata thành chuỗi JSON với các khóa được sắp xếp để đảm bảo tính nhất quán
        metadata_str = json.dumps(chunk.metadata, sort_keys=True)
        combined_str = chunk.content + metadata_str
        return (
            int(hashlib.sha256(combined_str.encode("utf-8")).hexdigest(), 16) % modulus
        )

    def add_chunk(
        self, chunk: "Chunk", given_embedding: list = None, overwrite: bool = False
    ) -> int:
        """
        Add a single chunk to the VectorStore using hash of its content as FAISS ID.
        If a chunk with the same content (i.e. same FAISS ID) exists, optionally overwrite it.

        Args:
            chunk (Chunk): The chunk object containing content and metadata.
            overwrite (bool): Nếu True, chunk mới sẽ ghi đè (update) chunk cũ có cùng nội dung. Mặc định là False.

        Returns:
            int: The FAISS ID (hash của content) assigned to the chunk.
        """
        # Tính FAISS ID dựa trên nội dung của chunk
        faiss_id = self.compute_faiss_id(chunk)
        chunk.faiss_id = faiss_id

        if faiss_id in self.faiss_id_to_metadata:
            if overwrite:
                self.update_chunk(chunk)
                logger.info(f"Overwritten existing chunk with FAISS ID {faiss_id}.")
            else:
                logger.info(
                    f"Chunk with FAISS ID {faiss_id} already exists, skipping addition."
                )
            return faiss_id

        # Generate embedding and add to FAISS index

        if given_embedding is None:
            embedding = self.llm.embedding(chunk.content, model=self.model)
        else:
            embedding = given_embedding

        embedding_np = np.array(embedding, dtype="float32").reshape(1, -1)
        self.index.add_with_ids(embedding_np, np.array([faiss_id], dtype=np.int64))

        chunk.metadata["embedding"] = embedding

        # Update metadata mapping
        self.faiss_id_to_metadata[faiss_id] = {
            "content": chunk.content,
            "metadata": chunk.metadata,
        }

        # logger.info(f"Added chunk with FAISS ID {faiss_id}.")
        return faiss_id

    def generate_embedding(self, chunk: Chunk):
        embedding = self.llm.embedding(chunk.content, model=self.model)
        return chunk, embedding

    def add_chunks(self, chunks: List["Chunk"], overwrite: bool = False, max_workers: int = 4):

        # Collect chunk not in self.faiss_id_to_metadata
        new_chunks = []
        for chunk in chunks:
            faiss_id = self.compute_faiss_id(chunk)
            if faiss_id in self.faiss_id_to_metadata:
                continue
            new_chunks.append(chunk)

        if len(new_chunks) == 0:
            logger.info("All chunks already in metadata, skipping generation and addition.")
            return

        embeddings = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.generate_embedding, chunk) for chunk in new_chunks]

            # FAISS index is not thread-safe when processing in parallel, especially when calling methods like index.add_with_ids(...) from multiple threads simultaneously.
            # So we need to generate embeddings parallel first, then add to FAISS index sequentially
            for future in tqdm(as_completed(futures), total=len(futures), desc="Generating embeddings"):
                try:
                    chunk, embedding = future.result()
                    embeddings.append((chunk, embedding))
                except Exception as e:
                    logger.error(f"Error generating embedding: {e}")

        # Add embeddings sequentially (safe!)
        for chunk, embedding in tqdm(embeddings, desc="Adding to FAISS"):
            self.add_chunk(chunk, given_embedding=embedding, overwrite=overwrite)

    def update_chunk(self, chunk: "Chunk") -> None:
        """
        Update an existing chunk in the VectorStore.

        This involves:
        - Removing the old embedding from the FAISS index.
        - Adding the updated embedding back to the index.
        - Updating the content and metadata in the mapping.

        Args:
            chunk (Chunk): The updated chunk object.

        Raises:
            ValueError: If the FAISS ID does not exist in the VectorStore.
        """
        # Tính lại FAISS ID dựa trên nội dung (nếu nội dung được update, ID cũng sẽ thay đổi)
        faiss_id = self.compute_faiss_id(chunk.content)
        chunk.faiss_id = faiss_id

        if faiss_id not in self.faiss_id_to_metadata:
            raise ValueError(f"FAISS ID '{faiss_id}' does not exist. Cannot update.")

        # Loại bỏ embedding cũ và thêm embedding mới
        self.index.remove_ids(np.array([faiss_id], dtype=np.int64))
        embedding = self.llm.embedding(chunk.content)
        embedding_np = np.array(embedding, dtype="float32").reshape(1, -1)
        self.index.add_with_ids(embedding_np, np.array([faiss_id], dtype=np.int64))

        # Cập nhật metadata
        self.faiss_id_to_metadata[faiss_id] = {
            "content": chunk.content,
            "metadata": chunk.metadata,
        }

        # logger.info(f"Updated chunk with FAISS ID {faiss_id}.")

    def delete_chunk(self, faiss_id: int) -> None:
        """
        Delete a chunk from the VectorStore by FAISS ID.

        Args:
            faiss_id (int): The FAISS ID of the chunk to be deleted.

        Raises:
            ValueError: If the FAISS ID does not exist in the VectorStore.
        """
        if faiss_id not in self.faiss_id_to_metadata:
            raise ValueError(f"FAISS ID '{faiss_id}' does not exist. Cannot delete.")

        self.index.remove_ids(np.array([faiss_id], dtype=np.int64))
        del self.faiss_id_to_metadata[faiss_id]

        # logger.info(f"Deleted chunk with FAISS ID {faiss_id}.")

    def search(self, query_text: str, top_k: int = 5, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Perform a similarity search on the FAISS index using a query text.

        Args:
            query_text (str): The query text to search for.
            top_k (int, optional): Number of top similar results to return. Defaults to 5.

        Returns:
            List[Dict[str, Any]]: A list of results with FAISS ID, content, metadata, and distance.
        """

        query_embedding = self.llm.embedding(text=query_text, model=self.model)
        query_embedding_np = np.array(query_embedding, dtype="float32").reshape(1, -1)
        distances, faiss_ids = self.index.search(query_embedding_np, top_k)

        results = []
        for distance, faiss_id in zip(distances[0], faiss_ids[0]):
            if faiss_id == -1:
                continue

            score = 1 - (distance / 2)
            if score < threshold:
                continue
            metadata = self.faiss_id_to_metadata.get(faiss_id, {})
            results.append(
                {
                    "faiss_id": faiss_id,   
                    "content": metadata.get("content"),
                    "metadata": metadata.get("metadata"),
                    "score": score,
                }
            )

        logger.info(
            f"Search completed for query: '{query_text}'. Found {len(results)} results."
        )
        return results

    def save_index(self) -> None:
        """
        Save the FAISS index and metadata to a pickle file.
        Nếu self.s3 được khởi tạo, dữ liệu sẽ được upload lên S3.
        """
        if not self.pickle_path:
            logger.error("Pickle path is not specified. Cannot save index.")
            return

        # Serialize the FAISS index and metadata
        faiss_bytes = faiss.serialize_index(self.index)
        data = {
            "faiss_index": faiss_bytes,
            "faiss_id_to_metadata": self.faiss_id_to_metadata,
            "embedding_dimension": self.embedding_dimension,
        }

        # Nếu biến s3 đã được khởi tạo, lưu dữ liệu lên S3
        if self.s3 is not None:
            try:
                import io

                # Chuyển đổi dữ liệu thành pickle bytes
                pickled_data = pickle.dumps(data)
                with io.BytesIO(pickled_data) as buffer:
                    # Upload stream lên S3
                    self.s3.s3_client.upload_fileobj(
                        buffer, self.s3.bucket_name, self.pickle_path
                    )
                logger.info(f"Saved VectorStore to S3 at '{self.pickle_path}'.")
            except Exception as e:
                logger.error(f"Failed to save VectorStore to S3: {e}")
        else:
            # Lưu file cục bộ
            with open(self.pickle_path, "wb") as f:
                pickle.dump(data, f)
            logger.info(f"Saved VectorStore to '{self.pickle_path}'.")

    def load_index(self) -> None:
        """
        Load the FAISS index and metadata from a pickle file.
        Nếu đối tượng s3 được khởi tạo, dùng S3 để đọc file.
        """
        if self.s3 is not None:
            # Load từ S3
            logger.info("Loading index from S3...")
            s3_data = self.s3._get(self.pickle_path)
            if s3_data is None:
                raise FileNotFoundError(
                    f"Pickle file '{self.pickle_path}' not found in S3."
                )
            data = pickle.loads(s3_data)
        else:
            # Load từ hệ thống file cục bộ
            if not os.path.exists(self.pickle_path):
                raise FileNotFoundError(
                    f"Pickle file '{self.pickle_path}' does not exist."
                )
            with open(self.pickle_path, "rb") as f:
                data = pickle.load(f)

        faiss_bytes = data.get("faiss_index")
        if faiss_bytes is None:
            raise ValueError("Missing FAISS index data in pickle file.")

        self.index = faiss.deserialize_index(faiss_bytes)
        self.faiss_id_to_metadata = data.get("faiss_id_to_metadata", {})

        logger.info(f"Loaded VectorStore from '{self.pickle_path}'.")

    def get_total_chunks(self) -> int:
        """
        Get the total number of chunks stored in the VectorStore.

        Returns:
            int: Total number of chunks.
        """
        return len(self.faiss_id_to_metadata)

    def list_chunks(self) -> List[Dict[str, Any]]:
        """
        List all chunks stored in the VectorStore with their metadata.

        Returns:
            List[Dict[str, Any]]: A list of all stored chunks with FAISS ID and metadata.
        """
        return [
            {"faiss_id": key, "chunk": value}
            for key, value in self.faiss_id_to_metadata.items()
        ]

    def get_chunk(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve the content and metadata of a chunk by FAISS ID.

        Args:
            faiss_id (int): The FAISS ID of the chunk.

        Returns:
            Optional[Dict[str, Any]]: The content and metadata of the chunk, or None if not found.
        """
        return self.faiss_id_to_metadata.get(faiss_id)
