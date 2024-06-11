# -*- coding: utf-8 -*-
"""Create an application instance."""

from wecom.app import create_app

app = create_app()


if __name__ == '__main__':
    # flask --app runserver db [init, migrate, upgrade, ...]
    # gunicorn --log-level debug  -w 1 --threads 10  --timeout 120 -b 0.0.0.0:9999 runserver:app -D
    # gunicorn --worker-class=gthread --log-level debug  -w 1 --threads 10  --timeout 120 -b 0.0.0.0:9999 runserver:app -D
    with app.app_context():
        app.run(host='0.0.0.0', port=9999, debug=True, use_reloader=True)  # 非命令启动
