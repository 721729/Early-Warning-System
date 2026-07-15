"""应用配置管理 —— 所有配置从环境变量读取, 有默认值"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120   # 2小时
    refresh_token_expire_minutes: int = 480  # 8小时

    # Database
    database_url: str = "mysql+pymysql://gps_user:gps_pass@localhost:3306/green_power_sentinel?charset=utf8mb4"

    # InfluxDB
    influx_url: str = "http://localhost:8086"
    influx_org: str = "green_power_sentinel"
    influx_bucket: str = "sensor_data"

    # Redis
    redis_url: str = "redis://:redis123@localhost:6379/0"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
