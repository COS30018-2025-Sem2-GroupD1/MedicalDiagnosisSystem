# utils/logger.py

import inspect
import logging
import sys

# A more informative default format, including the logger's name and a custom tag.
_DEFAULT_FORMAT = "%(asctime)s — %(levelname)s  \t[%(name)s%(tag)s]  \t%(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class TaggedFormatter(logging.Formatter):
	"""
	A custom formatter that adds a default value for 'tag' if it is not present
	in the LogRecord. This prevents errors if a log is generated without the
	TaggedAdapter, making the logging system more robust.
	"""
	def __init__(
		self,
		fmt=_DEFAULT_FORMAT,
		datefmt=_DEFAULT_DATE_FORMAT,
		**kwargs
	):
		super().__init__(fmt, datefmt, **kwargs)

	def format(self, record: logging.LogRecord) -> str:
		"""
		Adds a default 'tag' to the record before formatting.
		"""
		if not hasattr(record, 'tag'):
			record.tag = ""
		return super().format(record)

def setup_logging(
	level: int = logging.INFO,
	stream=sys.stdout
) -> None:
	"""
	Configures the root logger for the application.

	This function should be called once at application startup. It establishes a
	StreamHandler with the custom TaggedFormatter, ensuring all subsequent logs
	are handled and formatted correctly.

	Args:
		level: The minimum logging level to output (e.g., logging.INFO).
		stream: The stream where logs will be written (e.g., sys.stdout).
	"""
	root_logger = logging.getLogger()

	# Avoid adding duplicate handlers if this function is called multiple times.
	if root_logger.handlers:
		return

	handler = logging.StreamHandler(stream=stream)
	formatter = TaggedFormatter()
	handler.setFormatter(formatter)
	root_logger.addHandler(handler)
	root_logger.setLevel(level)
	root_logger.info("Logger set up")

def logger(
	tag: str | None = None,
	*,
	name: str | None = None
) -> logging.LoggerAdapter:
	"""
	Returns a logger that injects a tag into the LogRecord's context.

	The custom TaggedFormatter must be active for the tag to appear in the output.
	If 'name' is not provided, it defaults to the name of the calling module.

	Example:
	```
		# In a file named 'my_app/database.py'
		setup_logging()
		logger = logger(tag="DATABASE") # Name will be 'my_app.database'
		logger.info("Connection established.")
		# Expected Output:
		# 2025-09-07 22:15:30 — INFO  	[my_app.database:DATABASE]  	Connection established.
	```

	Args:
		tag: The tag to inject into the 'extra' context of log records.
		name: The name for the logger. Defaults to the calling module's name.

	Returns:
		A LoggerAdapter that enriches log records with the specified tag.
	"""
	logger_name = name
	if logger_name is None:
		# inspect.stack()[1] gets the frame of the caller.
		# inspect.getmodule() gets the module from that frame.
		# .__name__ gets the module's name.
		frame = inspect.stack()[1]
		module = inspect.getmodule(frame[0])
		if module:
			logger_name = module.__name__
		else:
			# Fallback if the module can't be determined
			logger_name = "unknown_module"
	base_logger = logging.getLogger(logger_name)

	# A LoggerAdapter is the standard way to pass contextual information to loggers.
	# It wraps the logger and adds the dictionary provided to the 'extra' attribute of each LogRecord.
	return logging.LoggerAdapter(
		base_logger,
		{"tag": f":{tag}" if tag is not None else ""}
	)
