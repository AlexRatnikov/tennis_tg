import logging
import os
import time
from datetime import datetime, timedelta
import requests
import schedule
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Application
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
LAT = os.getenv('TING_LAT')
LON = os.getenv('TING_LON')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')  # Replace with your group chat ID


def get_tomorrow_xam_unix_time(xam: int):
    # Get the current time
    now = datetime.now()
    # Calculate tomorrow's date
    tomorrow = now + timedelta(days=1)
    # Set the time to X AM
    tomorrow_xam = datetime(tomorrow.year, tomorrow.month, tomorrow.day, xam, 0, 0)
    # Convert to Unix time
    tomorrow_xam_unix_time = int(tomorrow_xam.timestamp())
    return tomorrow_xam_unix_time


def get_weather(xam: int):
    dt = get_tomorrow_xam_unix_time(xam)

    weather_api_url = (f'https://api.openweathermap.org/data/3.0/onecall/'
                       f'timemachine?lat={LAT}&lon={LON}&dt={dt}&units=metric&appid={WEATHER_API_KEY}')

    try:
        response = requests.get(weather_api_url)
        response.raise_for_status()
        data = response.json()
        temp = round(data['data'][0]['temp'])
        rain = data.get('rain', {}).get('1h', 0)
        return temp, rain
    except requests.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None, None
    except KeyError:
        logger.error(f"Unexpected response structure: {data}")
        return None, None


async def create_poll(context: CallbackContext):
    temp, rain = get_weather(7)
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%B %d %a')
    if temp is None or rain is None:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text="Error fetching weather data.")
        return

    options = await poll_options()

    await context.bot.send_poll(
        chat_id=GROUP_CHAT_ID,
        question=f"🎾 game on {tomorrow}:",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=True
    )


async def poll_options():
    options = []
    for hour in range(7, 12):
        temp, rain = get_weather(hour)
        if temp is None:
            options.append(f"{hour}:00AM")
        else:
            options.append(f"{hour}:00AM 🌡️ {temp}°C ☔ {rain}%")
    options.extend(["+1 (Coming with someone) 👫", "Beer only 🍺", "Pass ❌"])
    return options


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Bot started! Use /createpoll to create a poll on demand.")


def schedule_polls(application):
    async def job():
        context = CallbackContext(application)
        await create_poll(context)

    schedule.every().wednesday.at("09:00").do(lambda: application.create_task(job()))
    schedule.every().sunday.at("09:00").do(lambda: application.create_task(job()))

    while True:
        schedule.run_pending()
        time.sleep(1)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("createpoll", lambda update, context: create_poll(context)))

    # Start the scheduler in a separate thread
    import threading
    scheduler_thread = threading.Thread(target=schedule_polls, args=(application,))
    scheduler_thread.start()

    application.run_polling()

    # Create a simple HTTP server
    # Ensure the server listens on 0.0.0.0 and port 8080
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 8080))
    server_address = (host, port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info('Starting HTTP server on %s:%s', host, port)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
