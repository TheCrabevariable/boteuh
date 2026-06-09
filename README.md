# EU News Discord Bot

Compiles news from EU defence, economy, ecology, and federalism/integration sources into a Discord channel.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a Discord bot at https://discord.com/developers/applications
   - Enable Message Content Intent
   - Invite bot with `Send Messages` and `Embed Links` permissions

3. Edit `config.json`:
   - Set `token` to your bot token
   - Set `channel_id` to the target Discord channel ID
   - Adjust `poll_interval_minutes` as desired

4. Run:
   ```
   python bot.py
   ```

## Commands

- `!eu roundup` — fetch one headline per category on demand

## Categories

| Category   | Sources                                                    |
|------------|------------------------------------------------------------|
| Defence    | NATO, EDA, SIPRI                                           |
| Economy    | EC Economy, ECB, Eurostat                                  |
| Ecology    | EEA, EU Climate, EC Environment                            |
| Integration| Politico EU, Euractiv, European Parliament                 |
