import requests
import logging
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def send_telegram_notification(
    bot_token: str,
    chat_id: str,
    message: str,
    parse_mode: str = "HTML"
) -> bool:
    """
    Send a message to Telegram chat
    
    Args:
        bot_token: Telegram bot token
        chat_id: Chat ID to send message to
        message: Message text
        parse_mode: Parse mode (HTML or Markdown)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Telegram notification sent successfully to chat {chat_id}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Telegram notification: {e}")
        return False

def format_order_message(
    template: str,
    full_name: str,
    phone: str,
    email: str = "",
    product_id: str = "",
    product_sku: str = "",
    product_name: str = "",
    quantity: int = 1,
    price: str = "",
    order_id: str = "",
    country: str = "",
    office: str = "",
    landing_url: str = "",
    user_ip: str = "",
    transaction_id: str = "",
    block_id: str = "",
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    utm_id: str = "",
    utm_content: str = "",
    utm_term: str = "",
    fbclid: str = "",
    ttclid: str = "",
    comment: str = ""
) -> str:
    """
    Format order message using template with full order details
    
    Args:
        template: Message template with placeholders
        full_name: Customer full name
        phone: Customer phone
        email: Customer email (optional)
        product_id: Product ID (CRM ID) (optional)
        product_sku: Product SKU (optional)
        product_name: Product name (optional)
        quantity: Order quantity
        price: Product price (optional)
        order_id: Order ID (optional)
        country: Country code (optional)
        office: Office ID (optional)
        landing_url: Landing page URL (optional)
        user_ip: User IP address (optional)
        transaction_id: Transaction ID (optional)
        block_id: Block/Record ID (optional)
        utm_source, utm_medium, utm_campaign, utm_id, utm_content, utm_term: UTM parameters (optional)
        fbclid: Facebook click ID (optional)
        ttclid: TikTok click ID (optional)
        comment: Customer comment (optional)
    
    Returns:
        str: Formatted message
    """
    return template.format(
        full_name=full_name,
        phone=phone,
        email=email,
        product_id=product_id,
        product_sku=product_sku,
        product_name=product_name,
        quantity=quantity,
        price=price,
        order_id=order_id,
        country=country,
        office=office,
        landing_url=landing_url,
        user_ip=user_ip,
        transaction_id=transaction_id,
        block_id=block_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_id=utm_id,
        utm_content=utm_content,
        utm_term=utm_term,
        fbclid=fbclid,
        ttclid=ttclid,
        comment=comment
    )

def find_telegram_block(page, form_data: Dict) -> Optional[Dict]:
    """
    Find Telegram notification block on page and return its settings
    
    Args:
        page: Wagtail page object
        form_data: Form submission data
    
    Returns:
        dict: Telegram block settings or None if not found/enabled
    """
    try:
        logger.info(f"Looking for Telegram block on page {page.id}, body has {len(page.body)} blocks")
        
        # Look through page body for telegram_notification blocks
        for i, block in enumerate(page.body):
            logger.info(f"Block {i}: type={block.block_type}")
            if block.block_type == "telegram_notification":
                settings = block.value
                logger.info(f"Found Telegram block with settings: {settings}")
                if settings.get("enable_notifications", True):
                    logger.info(f"Telegram notifications enabled, returning settings")
                    return settings
                else:
                    logger.info(f"Telegram notifications disabled")
                    return None
        
        logger.warning(f"No telegram_notification block found on page {page.id}")
        return None
    except Exception as e:
        logger.error(f"Error finding Telegram block: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
