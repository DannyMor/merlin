from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = Field(default=5432, gt=0, le=65535)
    database: str = "merlin"
    user: str = "merlin"
    password: str = "merlin"
    pool_min_size: int = Field(default=2, ge=1)
    pool_max_size: int = Field(default=10, ge=1)

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class SchedulerConfig(BaseModel):
    poll_interval_seconds: float = Field(default=60.0, gt=0)
    batch_size: int = Field(default=50, ge=1)


class WorkerConfig(BaseModel):
    poll_interval_seconds: float = Field(default=5.0, gt=0)
    heartbeat_interval_seconds: float = Field(default=15.0, gt=0)
    max_concurrent_tasks: int = Field(default=5, ge=1)


class ReaperConfig(BaseModel):
    poll_interval_seconds: float = Field(default=30.0, gt=0)
    stale_threshold_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class MerlinConfig(BaseModel):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)
    reaper: ReaperConfig = Field(default_factory=ReaperConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
