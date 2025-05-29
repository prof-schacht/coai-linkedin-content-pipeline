#!/bin/bash
# Setup script for daily arXiv paper collection cron job

echo "📅 Setting up daily arXiv paper collection cron job..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create cron job file
CRON_FILE="/tmp/coai_arxiv_cron"

# Daily at 2 AM UTC (adjust as needed)
echo "0 2 * * * cd $PROJECT_DIR && source .venv/bin/activate && python scripts/fetch_arxiv_papers.py >> logs/cron.log 2>&1" > $CRON_FILE

echo "Proposed cron job:"
cat $CRON_FILE

echo ""
echo "To install this cron job, run:"
echo "  crontab $CRON_FILE"
echo ""
echo "To view current cron jobs:"
echo "  crontab -l"
echo ""
echo "To edit cron jobs manually:"
echo "  crontab -e"
echo ""
echo "To remove all cron jobs:"
echo "  crontab -r"

# Alternative: systemd timer (more modern approach)
cat > /tmp/coai-arxiv.service << EOF
[Unit]
Description=COAI arXiv Paper Collection
After=network.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/scripts/fetch_arxiv_papers.py
StandardOutput=append:$PROJECT_DIR/logs/systemd.log
StandardError=append:$PROJECT_DIR/logs/systemd.log
EOF

cat > /tmp/coai-arxiv.timer << EOF
[Unit]
Description=Run COAI arXiv collection daily
Requires=coai-arxiv.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo ""
echo "Alternative: systemd timer files created in /tmp/"
echo "To use systemd instead of cron:"
echo "  sudo cp /tmp/coai-arxiv.{service,timer} /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable coai-arxiv.timer"
echo "  sudo systemctl start coai-arxiv.timer"