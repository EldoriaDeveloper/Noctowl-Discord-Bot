import discord
from discord.ext import commands
import asyncio
import os
from colorama import Fore, Back, Style, init
import globals
from datetime import datetime
import time

# Initialize colorama
init(autoreset=True)

class CustomBot(commands.Bot):
    async def process_commands(self, message):
        ctx = await self.get_context(message)
        if ctx.command is None:
            return
        await self.invoke(ctx)

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print an attractive banner"""
    banner = f"""
{Fore.CYAN + Style.BRIGHT}
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║  ██████╗ ██╗███████╗ ██████╗ ██████╗ ██████╗ ██████╗     ██████╗  ██████╗ ██████╗ ║
║  ██╔══██╗██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔═══██╗╚══██╔╝ ║
║  ██║  ██║██║███████╗██║     ██║   ██║██████╔╝██║  ██║    ██████╔╝██║   ██║   ██║  ║
║  ██║  ██║██║╚════██║██║     ██║   ██║██╔══██╗██║  ██║    ██╔══██╗██║   ██║   ██║  ║
║  ██████╔╝██║███████║╚██████╗╚██████╔╝██║  ██║██████╔╝    ██████╔╝╚██████╔╝   ██║  ║
║  ╚═════╝ ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝     ╚═════╝  ╚═════╝    ╚═╝  ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)

def print_section_header(title, color=Fore.CYAN):
    """Print a styled section header"""
    print(f"\n{color + Style.BRIGHT}╔{'═' * (len(title) + 4)}╗")
    print(f"║  {title}  ║")
    print(f"╚{'═' * (len(title) + 4)}╝{Style.RESET_ALL}")

def print_status_line(status, message, color=Fore.GREEN):
    """Print a formatted status line"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icon = "✓" if color == Fore.GREEN else "✗" if color == Fore.RED else "●"
    print(f"{Fore.WHITE}[{timestamp}] {color + Style.BRIGHT}{status_icon} {status:<15} {Fore.WHITE}→ {color}{message}{Style.RESET_ALL}")

def print_info_box(title, content, color=Fore.BLUE):
    """Print information in a box format"""
    max_width = max(len(title), max(len(line) for line in content)) + 4
    
    print(f"\n{color + Style.BRIGHT}┌{'─' * max_width}┐")
    print(f"│ {title:<{max_width-2}} │")
    print(f"├{'─' * max_width}┤")
    
    for line in content:
        print(f"│ {line:<{max_width-2}} │")
    
    print(f"└{'─' * max_width}┘{Style.RESET_ALL}")

def print_loading_animation(message, duration=2):
    """Print a loading animation"""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for i in range(duration * 10):
        print(f"\r{Fore.YELLOW}{chars[i % len(chars)]} {message}...", end="", flush=True)
        time.sleep(0.1)
    print(f"\r{Fore.GREEN}✓ {message} complete!{Style.RESET_ALL}")

# Bot setup
intents = discord.Intents.all()
intents.presences = False
bot = commands.Bot(command_prefix="?", intents=intents)
bot.help_command = None
bot.case_insensitive = True
bot_start = False

@bot.event
async def on_ready():
    global bot_start
    
    if not bot_start:
        clear_screen()
        print_banner()
    
    if bot_start:
        print_section_header("🔄 BOT RECONNECTION", Fore.YELLOW)
        print_status_line("RECONNECT", "Bot reconnected successfully!", Fore.GREEN)
    else:
        print_section_header("🚀 BOT INITIALIZATION", Fore.MAGENTA)
        
        await load_cogs()
        bot_start = True

        print_section_header("✅ STARTUP COMPLETE", Fore.GREEN)
        print_status_line("READY", "Bot is now online and ready!", Fore.GREEN)

async def load_cogs():
    """Load cogs from the Cogs folder with enhanced output"""
    cogs_folder = "./Cogs"
    
    if not os.path.isdir(cogs_folder):
        print_status_line("COGS", "Cogs folder not found", Fore.RED)
        return
    
    folder = os.listdir(cogs_folder)
    cog_files = [f for f in folder if f.endswith(".py")]
    
    if not cog_files:
        print_status_line("COGS", "No cog files found", Fore.YELLOW)
        return

    for file in cog_files:
        try:
            await bot.load_extension(f"Cogs.{file[:-3]}")
            print_status_line("COG", f"Loaded {file}", Fore.GREEN)
        except commands.ExtensionError as e:
            print_status_line("COG", f"Extension error in {file}: {e}", Fore.RED)
        except Exception as e:
            print_status_line("COG", f"Failed to load {file}: {e}", Fore.RED)
    try:
        synced = await bot.tree.sync()
        print_status_line("SLASH", f"Synced {len(synced)} slash commands", Fore.MAGENTA)
    except Exception as e:
        print_status_line("SLASH", f"Failed to sync commands: {e}", Fore.RED)


async def main():
    """Main function with error handling"""
    try:
        print_section_header("🔑 AUTHENTICATION", Fore.YELLOW)
        print_status_line("TOKEN", "Authenticating with Discord...", Fore.YELLOW)
        
        await bot.start(globals.Secrets.TOKEN)
        
    except discord.LoginFailure:
        print_status_line("TOKEN", "Invalid bot token provided", Fore.RED)
    except discord.HTTPException as e:
        print_status_line("NETWORK", f"HTTP error: {e}", Fore.RED)
    except Exception as e:
        print_status_line("ERROR", f"Unexpected error: {e}", Fore.RED)
    finally:
        print_section_header("🛑 SHUTDOWN", Fore.RED)
        print_status_line("SHUTDOWN", "Bot has been terminated", Fore.RED)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Bot shutdown requested by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}💥 Critical error: {e}{Style.RESET_ALL}")