# Security

- Never commit `.env`, bot tokens, cookies, or personal account credentials.
- Keep the bot allowlist restricted to trusted Telegram user IDs.
- Run the service as a dedicated unprivileged Linux user.
- Keep Python dependencies, yt-dlp, FFmpeg, and the operating system updated.
- Do not expose the bot's download directory or SQLite database through a public web server.
- Report suspected vulnerabilities privately to the repository owner rather than posting secrets or exploit details in public issues.
