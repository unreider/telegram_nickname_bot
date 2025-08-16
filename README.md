# Telegram Nickname Bot

A Telegram bot that allows users to set, manage, and view custom nicknames within group chats.

## Features

- Add personal nicknames in group chats
- View all nicknames in a group
- Change existing nicknames
- Remove nicknames
- Group-specific nickname management

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Commands

- `/start` - Introduction and available commands
- `/add <nickname>` - Add a nickname for yourself
- `/all` - List all nicknames in the group
- `/change <nickname>` - Change your existing nickname
- `/remove` - Remove your nickname
- `/help` - Show available commands

## Deployment

### Railway Deployment

This bot is configured for deployment on Railway with automatic webhook setup.

#### Prerequisites

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and get your bot token
2. Have a Railway account at [railway.app](https://railway.app)

#### Deployment Steps

1. **Deploy to Railway:**
   - Connect your GitHub repository to Railway
   - Railway will automatically detect the Python project and use the `railway.json` configuration

2. **Set Environment Variables:**
   In your Railway project settings, add:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   PYTHON_ENV=production
   ```

3. **Optional Environment Variables:**
   ```
   WEBHOOK_URL=https://your-app.railway.app/webhook  # Auto-detected if not set
   STORAGE_FILE=data/nicknames.json                  # Default path
   ```

4. **Verify Deployment:**
   - Check the Railway logs for successful startup
   - Visit `https://your-app.railway.app/health` to verify the health check endpoint
   - Test the bot in a Telegram group chat

#### Railway Configuration

The bot includes:
- **Health Check Endpoint:** `/health` - Monitors bot and storage status
- **Webhook Support:** Automatic webhook setup for production
- **Graceful Shutdown:** Proper signal handling for Railway deployments
- **Error Recovery:** Retry logic for API failures and storage issues

#### Environment Detection

The bot automatically switches between polling (development) and webhook (production) modes:
- **Development:** Uses polling when `PYTHON_ENV` is not set to "production"
- **Production:** Uses webhooks when deployed on Railway with proper environment variables

### Local Development

For local development:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export PYTHON_ENV="development"
python main.py
```

## Development

Run tests:
```bash
pytest
```

## Project Structure

```
telegram-nickname-bot/
├── src/                 # Source code
│   ├── handlers/        # Command handlers
│   ├── bot.py          # Bot initialization
│   ├── config.py       # Configuration management
│   ├── storage.py      # Data storage
│   └── middleware.py   # Bot middleware
├── tests/              # Test files
├── data/               # Data storage directory
├── main.py             # Application entry point
└── requirements.txt    # Python dependencies
```