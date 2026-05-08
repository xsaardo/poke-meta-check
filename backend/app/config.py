from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://poke:poke_secret@localhost:5432/poke_meta"
    allow_manual_scrape: bool = False
    scraper_workers: int = 1
    scraper_delay_seconds: float = 6.0
    scraper_months_lookback: int = 3
    # Only scrape tournaments with at least this many players (filters out local league events)
    scraper_min_players: int = 32
    openapi_enabled: bool = False
    allowed_origins: str = ""
    # Optional pokemontcg.io API key (increases rate limits from 1k/day to higher)
    pokemontcg_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
