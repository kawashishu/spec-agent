import json
import os
import time

import pandas as pd
from azure.identity import DefaultAzureCredential
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from spec.config import logger


class PostgreSQL:
    """
    A class to manage connections and operations with a PostgreSQL database.

    This class provides methods for connecting to a PostgreSQL database, executing SQL commands,
    performing queries, and managing data. It also includes utilities for preprocessing text data
    and generating metadata mappings.
    """

    def __init__(self):
        """
        Initialize the PostgreSQL connection and environment variables.

        Raises:
            EnvironmentError: If required environment variables are missing.
        """
        credential = DefaultAzureCredential()
        token = credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        access_token = token.token

        # os.environ["PGPASSWORD"] = access_token
        os.environ["PGPASSWORD"] = os.environ.get("PGPASSWORD")

        # Load environment variables
        self.user = os.environ.get("PGUSER")
        self.host = os.environ.get("PGHOST")
        self.port = os.environ.get("PGPORT")
        self.database = os.environ.get("PGDATABASE")

        # Check for missing environment variables
        missing_vars = [
            var
            for var in ["PGUSER", "PGHOST", "PGPORT", "PGDATABASE"]
            if os.environ.get(var) is None
        ]
        if missing_vars:
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            raise EnvironmentError(
                f"Missing environment variables: {', '.join(missing_vars)}"
            )

        # Connection string
        self.conn_string = f"postgresql+psycopg2://{self.user}@{self.host}:{self.port}/{self.database}?sslmode=require"

        self.engine = None
        self.Session = None
        self.pool_pre_ping = True  # Enable pool pre-ping to test connection health
        self.TIMEOUT = 360 * 1000  # Timeout for SQL statements in milliseconds
        self.connect()

    def connect(self):
        """
        Establish a connection to the PostgreSQL database and create a session.

        Raises:
            Exception: If the connection to the database fails.
        """
        try:
            self.engine = create_engine(
                self.conn_string,
                pool_pre_ping=self.pool_pre_ping,
            )
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            self.session = self.Session()
            self.session.execute(text(f"SET statement_timeout = {self.TIMEOUT};"))
            logger.info("Connected to PostgreSQL database successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise e

    def close(self):
        """
        Close the database session and dispose of the engine.
        """
        try:
            if self.session:
                self.session.close()
                self.session = None
                logger.info("PostgreSQL session closed.")
            if self.engine:
                self.engine.dispose()
                self.engine = None
                logger.info("PostgreSQL engine disposed.")
        except Exception as e:
            logger.error(f"Failed to close connection: {e}")

    def execute(self, sql_command, params=None):
        """
        Execute an SQL command (INSERT/UPDATE/DELETE/DDL).

        Parameters:
            sql_command (str): The SQL command to execute.
            params (dict, optional): Parameters for the SQL command.

        Returns:
            ResultProxy or Error: The result of the execution or an error object if the execution fails.
        """
        if not self.session:
            logger.error("No session available.")
            return Error(message=f"No session available.")

        try:
            result = self.session.execute(text(sql_command), params)
            self.session.commit()
            logger.info("SQL Command executed and committed successfully.")
            return result
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to execute SQL Command: {e}")
            return Error(message=f"Failed to execute SQL Command: {e}")

    def query_to_df(self, query):
        """
        Execute a SELECT query and return the result as a pandas DataFrame.

        Parameters:
            query (str): The SQL query to execute.

        Returns:
            DataFrame or Error: The query result as a pandas DataFrame, or an error object if the query fails.
        """
        if not self.session:
            logger.error("No session available.")
            return Error(message=f"No session available.")

        try:
            start = time.time()
            df = pd.read_sql(query, con=self.session.connection())
            duration = time.time() - start
            logger.info(f"Query executed in {duration:.4f}s, DataFrame returned.")
            return df
        except Exception as e:
            self.session.rollback()
            if "canceling statement due to statement timeout" in str(e):
                logger.warning(f"Query timed out after {self.TIMEOUT} milliseconds.")
                return Error(
                    message=f"Query timed out after {self.TIMEOUT} milliseconds."
                )
            else:
                logger.error(f"Failed to execute query and return DataFrame: {e}")
                return Error(
                    message=f"Failed to execute query and return DataFrame: {e}. \n\n###Retry"
                )

    def table_exists(self, table_name):
        """
        Check if a table exists in the database.

        Parameters:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        if not self.session:
            logger.error("No session available.")
            return False

        try:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = :table_name
                );
            """
            result = self.session.execute(
                text(query), {"table_name": table_name}
            ).scalar()
            self.session.commit()
            logger.info(f"Table '{table_name}' exists: {result}")
            return result
        except ProgrammingError as e:
            self.session.rollback()
            logger.error(f"Failed to check if table exists: {e}")
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error: {e}")
            return False

    def delete_table(self, table_name):
        """
        Delete a table from the database.

        Parameters:
            table_name (str): The name of the table to delete.
        """
        if not self.session:
            logger.error("No session available.")
            return

        try:
            logger.info(f"Executing: DROP TABLE IF EXISTS {table_name};")
            self.session.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
            self.session.commit()
            logger.info(f"Table '{table_name}' deleted successfully.")
        except (ProgrammingError, SQLAlchemyError) as e:
            self.session.rollback()
            logger.error(f"Failed to delete table '{table_name}': {e}")

    def insert_df_to_table(self, df: pd.DataFrame, table_name: str):
        """
        Insert data from a pandas DataFrame into a table.

        Parameters:
            df (DataFrame): The DataFrame containing data to insert.
            table_name (str): The name of the target table.
        """
        if not self.session:
            logger.error("No session available.")
            return

        try:
            df.to_sql(
                table_name,
                con=self.session.connection(),
                index=False,
                if_exists="append",
                method="multi",
            )
            self.session.commit()
            logger.info(f"Data inserted into table '{table_name}' successfully.")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to insert data into table '{table_name}': {e}")

    def generate_mapping_json(self, table_names: list, output_file: str):
        """
        Generate a JSON file mapping text columns to their unique values for specified tables.

        Parameters:
            table_names (list): List of table names to process.
            output_file (str): The file path to save the JSON mapping.
        """
        if not self.session:
            logger.error("No session available.")
            return

        mapping = {}
        for table in table_names:
            try:
                logger.info(f"Processing table: {table}")
                mapping[table] = {}

                query_columns = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                      AND data_type IN ('character varying', 'text', 'character');
                """
                columns = self.session.execute(
                    text(query_columns), {"table_name": table}
                ).fetchall()

                for column in columns:
                    column_name = column[0]
                    logger.info(
                        f"Processing text column: {column_name} in table '{table}'"
                    )
                    query_unique_values = f"SELECT DISTINCT {column_name} FROM {table};"
                    result = self.session.execute(text(query_unique_values)).fetchall()
                    unique_values = [row[0] for row in result if row[0] is not None]
                    mapping[table][column_name] = unique_values

                logger.info(f"Processed table: {table}")
            except SQLAlchemyError as e:
                logger.error(f"Failed while processing table '{table}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error while processing '{table}': {e}")

        try:
            with open(output_file, "w", encoding="utf-8") as json_file:
                json.dump(mapping, json_file, indent=4, ensure_ascii=False)
            logger.info(f"Mapping JSON saved to '{output_file}'")
        except Exception as e:
            logger.error(f"Error writing JSON file '{output_file}': {e}")

    def explain(self, query):
        """
        Generate an execution plan for a given query using PostgreSQL's EXPLAIN.

        Parameters:
            query (str): The SQL query to analyze.

        Returns:
            str: A detailed explanation of the query plan.
        """
        if not self.session:
            logger.error("No session available.")
            return None

        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = self.session.execute(text(explain_query)).fetchall()
            if not result:
                logger.error("No EXPLAIN output returned.")
                return "No EXPLAIN output returned."

            plan_data = result[0][0]
            if not plan_data:
                logger.error("Empty EXPLAIN output.")
                return "Empty EXPLAIN output."

            top_level = plan_data[0]
            planning_time_ms = top_level.get("Planning Time", 0)
            execution_time_ms = top_level.get("Execution Time", 0)
            plan_info = top_level.get("Plan", {})
            memory_usage_kb = plan_info.get("Peak Memory Usage", None)
            memory_usage_gb = memory_usage_kb / (1024**2) if memory_usage_kb else None

            explanation_str = f"Planning Time: {planning_time_ms} ms\n"
            explanation_str += f"Execution Time: {execution_time_ms} ms\n"
            if memory_usage_gb is not None:
                explanation_str += f"Peak Memory Usage: {memory_usage_gb:.4f} GB\n"

            explanation_str += "\nPlan Detail (JSON):\n"
            explanation_str += json.dumps(plan_info, indent=2)

            logger.info("EXPLAIN executed and parsed successfully.")
            return explanation_str
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Failed to run EXPLAIN: {e}")
            return f"Failed to run EXPLAIN: {e}"
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error during EXPLAIN: {e}")
            return f"Unexpected error during EXPLAIN: {e}"

    def pre_processing(self, table_names):
        """
        Preprocess text columns in specified tables by trimming and converting to lowercase.

        Parameters:
            table_names (list): List of table names to preprocess.
        """
        if not table_names:
            logger.warning("No table names provided for preprocessing.")
            return

        for table in table_names:
            try:
                logger.info(f"Starting preprocessing for table '{table}'.")

                columns_query = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table
                      AND data_type IN ('character varying', 'varchar', 'text', 'char')
                """
                result = self.session.execute(text(columns_query), {"table": table})
                text_columns = [row[0] for row in result.fetchall()]

                if not text_columns:
                    logger.info(f"No text columns found in table '{table}'. Skipping.")
                    continue

                logger.info(f"Text columns in '{table}': {', '.join(text_columns)}")

                set_clauses = [f"{col} = TRIM(LOWER({col}))" for col in text_columns]
                set_statement = ", ".join(set_clauses)

                update_sql = f"UPDATE {table} SET {set_statement};"

                self.execute(update_sql)
                logger.info(f"Preprocessing completed for table '{table}'.")

            except SQLAlchemyError as e:
                logger.error(
                    f"SQLAlchemy error during preprocessing table '{table}': {e}"
                )
                self.session.rollback()
            except Exception as e:
                logger.error(
                    f"Unexpected error during preprocessing table '{table}': {e}"
                )
                self.session.rollback()
