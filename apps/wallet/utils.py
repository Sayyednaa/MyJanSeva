import logging
import threading
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def send_telegram_message_sync(text):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
    
    if not token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=8)
        if not response.ok:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")

def send_telegram_message(text):
    # Run in a separate thread so it doesn't block Django request/response lifecycle
    thread = threading.Thread(target=send_telegram_message_sync, args=(text,))
    thread.daemon = True
    thread.start()
