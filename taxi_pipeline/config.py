
import os
from dataclasses import dataclass

from dotenv import load_dotenv

REQUIRED_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


@dataclass(frozen=True)
class Settings:
    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str
    chunk_size: int = 100_000
    data_dir: str = "data/bronze"
    base_url: str = "https://d37ci6vzurychx.cloudfront.net/trip-data"

    @property
    def dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
            f"user={self.pg_user} password={self.pg_password}"
        )


def load_settings() -> Settings:
    load_dotenv()  # picks up .env when running on the host

    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    return Settings(
        pg_host=os.environ["POSTGRES_HOST"],
        pg_port=int(os.environ["POSTGRES_PORT"]),
        pg_db=os.environ["POSTGRES_DB"],
        pg_user=os.environ["POSTGRES_USER"],
        pg_password=os.environ["POSTGRES_PASSWORD"],
        chunk_size=int(os.getenv("CHUNK_SIZE", "100000")),
        data_dir=os.getenv("BRONZE_DATA_PATH", "data/bronze"),
        base_url=os.getenv(
            "TLC_BASE_URL", "https://d37ci6vzurychx.cloudfront.net/trip-data"
        ),
    )