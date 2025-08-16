# Telegram Bot with Aiogram and SQLite

This is a Telegram bot built using Aiogram (v2.x) and SQLite. It provides a menu-driven interface with nested sections and supports various content types.  Administrators can manage the bot's content directly from Telegram.

## Features

*   **Menu-Driven Interface:**  Easy navigation with a main menu and nested sub-sections.
*   **Back and Home Buttons:**  Intuitive navigation with "Back" and "Home" buttons available throughout the bot.
*   **Content Variety:** Supports displaying text, photos, documents, videos, audio, and animations within sections.
*   **Admin Control Panel:**  Administrators can add, rename, and delete sections, as well as add content directly from within Telegram.
*   **Persistent Data:**  Data is stored in an SQLite database, ensuring persistence across bot restarts.
*   **Arabic Language Support:** The bot's interface and messages are primarily in Arabic.

## Requirements

*   Python 3.7+
*   Aiogram (v2.x)
*   SQLite

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**

    ```bash
    pip install aiogram==2.*
    ```

## Configuration

1.  **Set the Bot Token and Admin ID:**

    You can configure the bot using environment variables or by directly modifying the `bot.py` file.

    *   **Environment Variables (Recommended):**

        *   `BOT_TOKEN`:  Your Telegram bot token (obtained from BotFather).
        *   `ADMIN_ID`: Your Telegram user ID (the ID of the administrator who can manage the bot).
        *   `DB_PATH`: Path to the SQLite database file (defaults to `bot.db`).

        Example (using bash):

        ```bash
        export BOT_TOKEN="YOUR_BOT_TOKEN"
        export ADMIN_ID="YOUR_ADMIN_ID"
        export DB_PATH="my_bot.db"
        ```

    *   **Directly in `bot.py`:**

        Modify the following lines in `bot.py`:

        ```python
        TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Replace with your bot token
        ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_ADMIN_ID"))  # Replace with your Telegram user ID
        DB_PATH = os.getenv("DB_PATH", "bot.db")
        ```

    **Important:**  Replace `"YOUR_BOT_TOKEN"` and `"YOUR_ADMIN_ID"` with your actual bot token and user ID.

## Usage

1.  **Run the bot:**

    ```bash
    python bot.py
    ```

2.  **Interact with the bot on Telegram:**

    *   Start the bot by sending the `/start` command.
    *   Use the `/menu` or `/home` commands to navigate to the main menu.
    *   If you are the administrator, use the `/admin` command to access the admin control panel.

## Database Structure

The bot uses an SQLite database to store sections and items. The database schema consists of two tables:

*   **`sections`:**

    *   `id` (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for the section.
    *   `name` (TEXT NOT NULL): Name of the section.
    *   `parent_id` (INTEGER NULL REFERENCES sections(id) ON DELETE CASCADE): ID of the parent section (NULL for top-level sections).
    *   `position` (INTEGER DEFAULT 0):  Order of the section within its parent.

*   **`items`:**

    *   `id` (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for the item.
    *   `section_id` (INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE): ID of the section the item belongs to.
    *   `type` (TEXT NOT NULL CHECK (type IN ('text','photo','document','video','audio','animation'))): Type of the item.
    *   `text` (TEXT): Text content (for text items).
    *   `file_id` (TEXT): Telegram file ID (for media items).
    *   `caption` (TEXT): Caption for media items.
    *   `position` (INTEGER DEFAULT 0): Order of the item within its section.

## Admin Commands

*   `/admin`: Access the admin control panel.
*   `/list`: Display a tree-like structure of all sections with their IDs.

## Callback Data Structure

The bot uses callback data to handle button presses. Here's a breakdown of the common callback data formats:

*   `home`: Navigates to the main menu.
*   `back:<parent_id or 'root'>`: Navigates back to the parent section.  `root` indicates the main menu.
*   `section:<section_id>`: Opens a specific section.
*   `show:<section_id>:<page>`: Displays a specific item within a section (pagination).
*   `admin:<action>:<target>`:  Admin actions, where:
    *   `<action>` can be `add_section`, `rename`, `delete`, `add_item`.
    *   `<target>` can be a section ID, `root`, or `pick` (to prompt for an ID).

## Error Handling

The bot includes a basic error handler that attempts to display an error message to the user if an unexpected error occurs.

## Contributing

Contributions are welcome!  Feel free to submit pull requests with bug fixes, new features, or improvements to the documentation.

## License

[MIT License](LICENSE) (Replace with the actual license file if you have one)
