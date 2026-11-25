"""Application settings, read from settings.ini."""

import configparser

_PATH = "settings.ini"


def bus_settings():
    parser = configparser.ConfigParser()
    parser.read(_PATH)
    return {
        "host": parser["bus"]["host"],
        "port": int(parser["bus"]["port"]),
        "timeout": float(parser["bus"]["timeout"]),
    }


def app_name():
    parser = configparser.ConfigParser()
    parser.read(_PATH)
    return parser["app"]["name"]
