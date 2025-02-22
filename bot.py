
import asyncio
import logging
import sys
import os
from pathlib import Path
from discord import Intents, Activity, ActivityType, Status, Message
from discord.errors import ConnectionClosed
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_FILE = './debug.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    style='%',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

TOKEN = BOT_TOKEN

if TOKEN is None:
    raise ValueError("BOT_TOKEN not found in the environment variables.")


class Client(commands.Bot):
    def __init__(self, command_prefix=None, intents=Intents.all()):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        cogs_dir = Path(__file__).parent / 'cogs'

        if not cogs_dir.exists():
            logger.warning(f"Cogs directory not found: {cogs_dir}")
            return

        for file in cogs_dir.glob('*.py'):
            if file.name.startswith('__'):
                continue
            extension_name = f'cogs.{file.stem}'
            try:
                await self.load_extension(extension_name)
                logger.info(f"Loaded extension: {file.stem}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension_name}: {e}")

        try:
            await self.tree.sync()
            logger.info("Successfully synced application commands.")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user.name}")
        try:
            activity = Activity(type=ActivityType.playing, name="Zk Bridge")
            await self.change_presence(status=Status.online, activity=activity)
            logger.info("Presence set successfully.")
        except Exception as e:
            logger.error(f"Error setting presence: {e}")

    async def on_disconnect(self):
        logger.warning("Bot has been disconnected. Attempting to reconnect...")

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"An error occurred during event {event}: {args} {kwargs}")
        if isinstance(args[0], ConnectionClosed):
            logger.error(f"WebSocket closed with code {args[0].code}. Trying to reconnect...")

    async def on_message(self, message:Message):
        if message.author.bot:
            return


async def main():
    client = Client()

    try:
        await client.start(TOKEN)
    except ConnectionClosed as e:
        logger.error(f"WebSocket closed with code {e.code}. Reconnecting in 5 seconds...")
        await asyncio.sleep(5)
        await main()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        logger.info("Bot is shutting down...")


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted. Shutting down gracefully...")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            logger.warning("Event loop was closed prematurely.")
        else:
            logger.error(f"Unexpected runtime error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        try:
            loop.close()
        except Exception as close_error:
            logger.error(f"Error closing the event loop: {close_error}")
