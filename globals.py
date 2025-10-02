import discord
from datetime import datetime, timezone
import traceback
from colorama import Fore
import os
import json
from typing import Mapping, Any

WORKING_DIR = os.getcwd().replace("\\", "/")

def load_json(file_path: str) -> Mapping[str, Any]:
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"base.py file error: {e}")

_secrets = load_json(os.path.join(WORKING_DIR, "secrets.json"))

class Secrets:
    TOKEN = _secrets["BOT_TOKEN"]

def log_message(message=None, action="debug", error=None):
    """
    Logs a formatted log message with a specified action type.

    Parameters:
        message (str): The message to log.
        action (str): The type of action (e.g., 'debug', 'info', 'warn', 'error').
                     Default is 'debug'.
        error (optional): The error object or message to log.
    """
    action = action.lower()

    emojis = {
        "debug": "🐛",
        "info": "ℹ️",
        "warn": "⚠️",
        "error": "❌",
    }

    colors = {
        "debug": Fore.BLUE,
        "info": Fore.GREEN,
        "warn": Fore.YELLOW,
        "error": Fore.RED,
    }

    emoji = emojis.get(action, "🔍")
    color = colors.get(action, Fore.CYAN)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if error:
        if isinstance(error, discord.errors.NotFound):
            action = 'warn'
            color = Fore.YELLOW
            error_message = "Unrecognized interaction detected; event safely ignored!"
        else:    
            color = Fore.RED
            action = 'error'
            if isinstance(error, str):
                error_message = f"The error is in String format so couldn't do traceback.\nError: {error}"
            else:
                error_message = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        formatted_message = (
            f"{color}╔════════════════════════════════════════════════════════════╗\n"
            f"║ {emoji} [{action.upper()}] {timestamp} - [BOT] ║\n"
            f"╟────────────────────────────────────────────────────────────╢\n"
            f"║ {error_message}\n"
            f"╚════════════════════════════════════════════════════════════╝"
        )
    elif message:
        formatted_message = (
            f"{color}╔════════════════════════════════════════════════════════════╗\n"
            f"║ {emoji} [{action.upper()}] {timestamp} - [BOT] ║\n"
            f"╟────────────────────────────────────────────────────────────╢\n"
            f"║ {message}\n"
            f"╚════════════════════════════════════════════════════════════╝"
        )
    else:
        formatted_message = f"{Fore.RED}╔════════════════════════════════════════════════════════════╗\n║ ❌ [ERROR] {timestamp} - No Log Message has been passed in the function - ║\n╚════════════════════════════════════════════════════════════╝"

    print(formatted_message)