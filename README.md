# telegram-card-bot

## About

- **Purpose**: Facilitate the exchange of discount cards between users via a Telegram bot.
- **Key Features**:
  - Users can upload a photo of their discount card and assign it a unique name.
  - Other users can browse available cards and download them.
  - Cards are stored securely in a SQLite database.
  - Easy-to-use interface with inline buttons for card selection.

### Technologies

* Language: **Python**
* Libraries: **python-telegram-bot, SQLite3**
* Database: **SQLite**
* Deployment: **Docker, Docker Compose**
* API: **Telegram Bot API**

## Installing

### Clone the Project

```shell
git clone https://github.com/l1ve4code/telegram-card-bot.git
```

### Set Your Values in `docker-compose.yml`

Replace the placeholder with your Telegram Bot token:

```yaml
services:
  discount-card-bot:
    container_name: discount-card-bot
    build: .
    network_mode: host
    environment:
      - BOT_TOKEN=YOUR_BOT_TOKEN
      - ADMIN_PASSWORD=your_admin_password
    volumes:
      - ./photos:/app/photos
      - ./discount_cards.db:/app/discount_cards.db
    restart: unless-stopped
```

### Replace Placeholders in the Script

If you're not using Docker, update the following variable in the script (`main.py`):

```python
application = Application.builder().token("BOT_TOKEN").build()
```

## Running the Project

### Using Docker Compose

1. Build and start the container:

```shell
docker-compose up --build
```

2. Stop the container:

```shell
docker-compose down
```

### Running Locally

1. Install dependencies:

```shell
pip install -r requirements.txt
```

2. Run the script:

```shell
python main.py
```

## How It Works

1. **Uploading a Discount Card**:
   - Users send a photo of their discount card to the bot.
   - The bot saves the photo with a unique filename (using a timestamp) and prompts the user to assign a name to the card.
   - The card's name and file path are stored in the SQLite database.

2. **Browsing Available Cards**:
   - Users can use the `/list` command to view all available cards.
   - The bot displays a list of cards with inline buttons for selection.

3. **Downloading a Card**:
   - When a user selects a card from the list, the bot sends the corresponding photo.

4. **Persistent Storage**:
   - The SQLite database (`discount_cards.db`) stores all card information, ensuring data persistence even after the bot is restarted.

## Author

* Telegram: **[@live4code](https://t.me/live4code)**
* Email: **steven.marelly@gmail.com**

Good luck with your Telegram discount card exchange bot! 🚀