"""Application configuration package.

Exposes the global :data:`config` instance so that every module can read the
settings via a single import::

    from src.documentation_helper.config import config
"""

from src.documentation_helper.config.config import Config, config

__all__ = ["Config", "config"]
