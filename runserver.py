# -*- coding: utf-8 -*-
"""Create an application instance."""

from wecom.app import create_app

app = create_app()


if __name__ == '__main__':
    # flask --app runserver db [init, migrate, upgrade, ...]
    with app.app_context():
        app.run(host='0.0.0.0', port=9999, debug=True, use_reloader=True)  # 非命令启动
