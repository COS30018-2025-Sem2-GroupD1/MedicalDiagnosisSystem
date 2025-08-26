from pydantic_settings import BaseSettings

API_PATH = "/api/v1/endpoints"

class Settings(BaseSettings):
	"""Add values you want to copy from the .env file into here."""
	has_been_copied: str

	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"

	def reload_settings(self):
		global SETTINGS
		SETTINGS = Settings()  # type: ignore

SETTINGS = Settings() # type: ignore
