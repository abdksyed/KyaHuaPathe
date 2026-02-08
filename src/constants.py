import os

DB_URL = (
    f"postgresql+psycopg://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_CONTAINER_NAME']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)
