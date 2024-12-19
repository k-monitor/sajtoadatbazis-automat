import logging
import os
from mysql.connector.cursor_cext import CMySQLCursorDict

# partially written by gpt-4o

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('sql_logger')
log_sql = 'LOG_SQL' in os.environ and os.environ['LOG_SQL']

# Define a helper function to safely format the query with parameters
def format_query_with_params(query, params):
    if params is None:
        return query
    # Escape and format parameters for MySQL
    escaped_params = tuple(
        f"'{str(p).replace("'", "''")}'" if isinstance(p, str) else str(p)
        for p in params
    )
    return query % escaped_params

# Define a wrapper function for SQL logging
class LoggingCursor(CMySQLCursorDict):
    def execute(self, operation, params=None, multi=False):
        if log_sql:
            if params:
                formatted_query = format_query_with_params(operation, params)
                logger.info(f"Executing SQL: {formatted_query}")
            else:
                logger.info(f"Executing SQL: {operation}")
        return super().execute(operation, params, multi)

    def executemany(self, operation, seq_params):
        if log_sql:
            for params in seq_params:
                formatted_query = format_query_with_params(operation, params)
                logger.info(f"Executing SQL: {formatted_query}")
        return super().executemany(operation, seq_params)
