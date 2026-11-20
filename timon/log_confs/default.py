"""
Create some kind of default log settings for timon debugging
"""
import mytb.logging.configs.console as console


def get_log_settings(**kwargs):
    """
    get default settings from mytb and add timon specific loggers
    """
    LOGGING = console.get_log_settings(**kwargs)
    loggers = LOGGING["loggers"]
    handlers = list(LOGGING["handlers"])
    warn = dict(level='WARNING', handlers=handlers, propagate=False)
    info = dict(warn)
    info["level"] = 'INFO'
    loggers.update({
        'asyncio': info,
        'peewee': warn,
        'httpcore.connection': info,
        'timon.state': info,
        'timon.resources': info,
        'timon.db': info,
        'root': info,
    })
    return LOGGING
