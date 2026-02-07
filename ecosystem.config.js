module.exports = {
    apps: [
        {
            name: "tradesigx-bot",
            script: "main.py",
            interpreter: "python",
            watch: false,
            autorestart: true,
            max_restarts: 10,
            min_uptime: "10s",
            error_file: "logs/bot-error.log",
            out_file: "logs/bot-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            env: {
                NODE_ENV: "production",
                PORT: 5000
            }
        }
    ]
};
