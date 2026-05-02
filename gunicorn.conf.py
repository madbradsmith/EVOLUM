import os

workers = 2
timeout = 120
worker_class = "sync"
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
