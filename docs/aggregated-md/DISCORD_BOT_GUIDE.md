# Discord Bot Integration Guide

This guide covers the Discord bot implementation, configuration, and deployment for the RAG system.

## 🤖 Bot Overview

The Discord bot provides a conversational interface to the RAG system,
allowing users to query the knowledge base directly within Discord channels.

### Key Features

- **Slash Commands**: Modern Discord slash command interface
- **Reaction Feedback**: 👍👎 emoji-based feedback collection
- **Context Awareness**: Channel and user ID tracking
- **Error Handling**: Graceful fallback mechanisms
- **Async Processing**: Non-blocking request handling

## 🚀 Setup & Configuration

### 1. Discord Developer Portal Setup

#### Create Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter application name (e.g., "RAG Bot")
4. Go to "Bot" section
5. Click "Add Bot"

#### Bot Configuration

```yaml
# Required Bot Settings
Public Bot: ✅ (unchecked for private bots)
Requires OAuth2 Code Grant: ❌ (unchecked)
Privileged Gateway Intents:
  - Presence Intent: ❌ (optional)
  - Server Members Intent: ❌ (optional)
  - Message Content Intent: ✅ (required for message content)
```

#### Bot Permissions

```yaml
# Required Permissions (Decimal: 67584)
General Permissions:
  - View Channels: ✅
  - Send Messages: ✅
  - Use Slash Commands: ✅
  - Embed Links: ✅
  - Attach Files: ✅
  - Read Message History: ✅
  - Mention Everyone: ❌
  - Use External Emojis: ✅
  - Add Reactions: ✅
  - Moderate Members: ❌
```

### 2. Environment Configuration

```bash
# .env file configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_server_id_here  # Optional: for guild-specific deployment
```

### 3. Bot Invitation

#### OAuth2 URL Generator

```yaml
Scopes:
  - bot: ✅
  - applications.commands: ✅

Bot Permissions:
  - Send Messages: ✅
  - Use Slash Commands: ✅
  - Embed Links: ✅
  - Attach Files: ✅
  - Read Message History: ✅
  - Add Reactions: ✅
```

#### Invitation URL

```bash
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=67584&scope=bot%20applications.commands
```

## 📡 Bot Commands

### Slash Commands

#### `/ask <question>`

Query the RAG system with a natural language question.

**Parameters:**

- `question` (required): The question to ask the RAG system

**Example:**

```bash
/ask What is the demo day schedule?
```

**Response Format:**

```json
{
  "content": "Based on the available information...",
  "embeds": [
    {
      "title": "Demo Day Schedule",
      "description": "The demo day is scheduled for...",
      "color": 0x00ff00,
      "fields": [
        {
          "name": "Date",
          "value": "October 15, 2024",
          "inline": true
        }
      ]
    }
  ],
  "components": [
    {
      "type": 1,
      "components": [
        {
          "type": 2,
          "style": 2,
          "label": "👍",
          "custom_id": "feedback_positive"
        },
        {
          "type": 2,
          "style": 2,
          "label": "👎",
          "custom_id": "feedback_negative"
        }
      ]
    }
  ]
}
```

#### `/feedback [days]`

View feedback statistics for the bot.

**Parameters:**

- `days` (optional): Number of days to show feedback for (default: 7)

**Example:**

```bash
/feedback 30
```

**Response Format:**

```json
{
  "embeds": [
    {
      "title": "Bot Feedback Statistics",
      "description": "Feedback summary for the last 30 days",
      "color": 0x0099ff,
      "fields": [
        {
          "name": "👍 Positive",
          "value": "85 (73%)",
          "inline": true
        },
        {
          "name": "👎 Negative",
          "value": "31 (27%)",
          "inline": true
        },
        {
          "name": "Total Responses",
          "value": "116",
          "inline": true
        }
      ]
    }
  ]
}
```

### Reaction Feedback

Users can provide feedback by clicking 👍 or 👎 reactions on bot responses.

**Feedback Collection:**

- **Positive (👍)**: User found the response helpful
- **Negative (👎)**: User found the response unhelpful

**Data Collected:**

```json
{
  "query_id": "uuid",
  "user_id": "discord_user_id",
  "channel_id": "discord_channel_id",
  "rating": "positive|negative",
  "timestamp": "2024-01-01T00:00:00Z",
  "query": "original_question",
  "response": "bot_response"
}
```

## 🔧 Technical Implementation

### Bot Architecture

```python
# Core bot structure
class RAGBot:
    def __init__(self):
        self.client = interactions.Client(token=DISCORD_BOT_TOKEN)
        self.rag_service = RAGService()
        self.feedback_service = FeedbackService()

    async def handle_ask_command(self, ctx, question):
        # Process RAG query
        # Send response with feedback buttons
        # Handle user interactions

    async def handle_feedback_command(self, ctx, days=7):
        # Retrieve feedback statistics
        # Format and send response

    async def handle_reaction(self, ctx):
        # Process user feedback
        # Store in database
        # Send confirmation
```

### Error Handling

#### Common Error Scenarios

1. **RAG Service Unavailable**

```python
# Fallback response
await ctx.send("Sorry, I'm having trouble accessing the knowledge base right now. Please try again later.")
```

1. **Invalid Query**

```python
# Validation error
await ctx.send("Please provide a valid question. For example: `/ask What is the demo day schedule?`")
```

1. **Rate Limiting**

```python
# Rate limit handling
await ctx.send("You're asking questions too quickly. Please wait a moment before asking another question.")
```

### Performance Optimization

#### Caching Strategy

```python
# Query result caching
cache_ttl = 300  # 5 minutes
cached_results = {}

async def get_cached_response(self, query):
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in cached_results:
        return cached_results[cache_key]
    return None
```

#### Async Processing

```python
# Non-blocking request handling
async def process_rag_query(self, query):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/v1/rag",
            json={"query": query}
        ) as response:
            return await response.json()
```

## 📊 Monitoring & Analytics

### Bot Metrics

#### Performance Metrics

- **Response Time**: Average time to process queries
- **Success Rate**: Percentage of successful queries
- **Error Rate**: Percentage of failed queries
- **Uptime**: Bot availability percentage

#### Usage Metrics

- **Query Volume**: Number of queries per day/hour
- **User Engagement**: Active users and queries per user
- **Command Usage**: Most used commands
- **Feedback Distribution**: Positive vs negative feedback ratio

#### Business Metrics

- **User Satisfaction**: Feedback-based satisfaction score
- **Query Success**: Percentage of queries with helpful responses
- **Channel Activity**: Usage across different channels
- **Peak Usage Times**: When users are most active

### Logging & Debugging

#### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Query logging
logger.info(
    "rag_query_processed",
    user_id=ctx.user.id,
    channel_id=ctx.channel.id,
    query=question,
    response_time=response_time,
    success=True
)

# Error logging
logger.error(
    "rag_query_failed",
    user_id=ctx.user.id,
    query=question,
    error=str(e),
    traceback=traceback.format_exc()
)
```

#### Health Checks

```python
async def health_check(self):
    try:
        # Check backend connectivity
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/health") as response:
                if response.status == 200:
                    return True
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
    return False
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
# Dockerfile for Discord bot
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy bot code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}

# Run bot
CMD ["python", "run_bot.py"]
```

### Docker Compose Integration

```yaml
# docker-compose.yaml
services:
  bot:
    build: ./bots
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - BACKEND_URL=http://api:8001
    depends_on:
      - api
    restart: unless-stopped
    profiles:
      - discord
```

### Production Considerations

#### Scaling

- **Single Instance**: Bot runs as single instance per Discord server
- **Load Balancing**: Not applicable (Discord handles routing)
- **Redundancy**: Deploy multiple instances for high availability

#### Security

- **Token Security**: Store bot token securely, never commit to version control
- **Permission Scope**: Use minimum required permissions
- **Rate Limiting**: Implement client-side rate limiting
- **Input Validation**: Sanitize all user inputs

#### Monitoring

- **Health Checks**: Monitor bot connectivity and responsiveness
- **Error Tracking**: Track and alert on errors
- **Performance Monitoring**: Monitor response times and success rates
- **User Feedback**: Track user satisfaction metrics

## 🔍 Troubleshooting

### Common Issues

#### 1. "An improper token was passed"

**Symptoms:**

- Bot fails to start
- Error in logs: `LoginError: An improper token was passed`

**Solutions:**

1. Verify token format (should be 59+ characters)
2. Check token in Discord Developer Portal
3. Ensure token is correctly set in environment variables
4. Reset token if necessary

#### 2. Bot Not Responding to Commands

**Symptoms:**

- Bot appears online but doesn't respond to slash commands
- Commands not visible in Discord

**Solutions:**

1. Check bot permissions in server
2. Verify slash commands are registered
3. Check bot is in the correct server
4. Restart bot service

#### 3. High Response Times

**Symptoms:**

- Slow responses to user queries
- Timeout errors

**Solutions:**

1. Check backend API performance
2. Monitor network connectivity
3. Optimize query processing
4. Implement caching

#### 4. Rate Limiting Issues

**Symptoms:**

- Bot temporarily stops responding
- 429 HTTP errors in logs

**Solutions:**

1. Implement exponential backoff
2. Reduce query frequency
3. Add client-side rate limiting
4. Monitor Discord API limits

### Debug Commands

```bash
# Check bot status
docker compose logs bot

# Check backend connectivity
curl http://localhost:8001/health

# Test bot commands manually
docker compose exec bot python -c "
import asyncio
from run_bot import RAGBot
bot = RAGBot()
asyncio.run(bot.test_connection())
"
```

## 📚 Best Practices

### Command Design

1. **Clear Naming**: Use descriptive command names
2. **Helpful Descriptions**: Provide clear command descriptions
3. **Parameter Validation**: Validate all input parameters
4. **Error Messages**: Provide helpful error messages

### User Experience

1. **Response Formatting**: Use embeds for rich responses
2. **Feedback Collection**: Make feedback easy and intuitive
3. **Loading Indicators**: Show progress for long operations
4. **Context Preservation**: Maintain conversation context

### Performance

1. **Async Operations**: Use async/await for all I/O operations
2. **Caching**: Cache frequently accessed data
3. **Rate Limiting**: Implement appropriate rate limiting
4. **Error Handling**: Gracefully handle all error conditions

### Security

1. **Input Sanitization**: Sanitize all user inputs
2. **Permission Checks**: Verify user permissions
3. **Token Security**: Protect bot tokens
4. **Logging**: Log security-relevant events
