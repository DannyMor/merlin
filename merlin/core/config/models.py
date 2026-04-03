from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "merlin"
    user: str = "merlin"
    password: str = "merlin"
    pool_min_size: int = 2
    pool_max_size: int = 10

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class SchedulerConfig(BaseModel):
    poll_interval_seconds: float = 60.0
    batch_size: int = 50


class WorkerConfig(BaseModel):
    poll_interval_seconds: float = 5.0
    heartbeat_interval_seconds: float = 15.0
    max_concurrent_tasks: int = 5


class ReaperConfig(BaseModel):
    poll_interval_seconds: float = 30.0
    stale_threshold_seconds: float = 60.0
    max_retries: int = 3


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class MerlinConfig(BaseModel):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)
    reaper: ReaperConfig = Field(default_factory=ReaperConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
