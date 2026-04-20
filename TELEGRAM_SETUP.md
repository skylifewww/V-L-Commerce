# Telegram Notifications Setup Guide

## 1. Create Telegram Bot

1. Open Telegram and find **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Save the **Bot Token** (looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 2. Get Chat ID

**Option 1: Private Chat**
1. Start a chat with your bot
2. Send any message to the bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your `chat_id` in the response (usually a positive number)

**Option 2: Group Chat**
1. Add your bot to the group
2. Send a message in the group mentioning the bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find the `chat_id` (usually negative for groups, starts with `-100`)

## 3. Configure in Wagtail CMS

1. Go to your landing page in Wagtail CMS
2. Add **"Telegram Notification"** block from the available blocks
3. Fill in the fields:
   - **Bot Token**: Your bot token from step 1
   - **Chat ID**: Chat ID from step 2
   - **Message Template**: Customize message format
   - **Enable Notifications**: Keep checked

## 4. Message Template Variables

Available variables for message template:
- `{full_name}` - Customer full name
- `{phone}` - Customer phone number
- `{email}` - Customer email (if provided)
- `{product_name}` - Product name
- `{quantity}` - Order quantity
- `{comment}` - Customer comment (if provided)

**Default Template:**
```
New order!

Customer: {full_name}
Phone: {phone}
Product: {product_name}
Quantity: {quantity}
```

**Advanced Template (HTML):**
```
<b>NEW ORDER!</b>

<b>Customer:</b> {full_name}
<b>Phone:</b> {phone}
<b>Email:</b> {email}
<b>Product:</b> {product_name}
<b>Quantity:</b> {quantity}
<b>Comment:</b> {comment}
```

## 5. Test Configuration

1. Submit a test order through your landing page
2. Check if you receive the notification in Telegram
3. Check Django logs for any errors if notification fails

## 6. Troubleshooting

**Common Issues:**
- **404 Bad Request**: Check if bot token is correct
- **400 Bad Request**: Check if chat ID is correct
- **403 Forbidden**: Bot might not have permission to send messages
- **No message received**: Check if notifications are enabled in block settings

**Debug Steps:**
1. Verify bot token: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe`
2. Check bot can send messages: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test`
3. Check Django logs: `python manage.py runserver --verbosity=2`

## 7. Security Tips

- Never share your bot token publicly
- Use environment variables for production deployments
- Consider creating a separate bot for each environment
- Regularly rotate bot tokens if compromised
