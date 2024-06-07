# -*- coding: utf-8 -*-
"""Create an application instance."""

from fkcookiecutter.app import create_app

app = create_app()


if __name__ == '__main__':
    # flask --app runserver db [init, migrate, upgrade, ...]
    app.run(host='127.0.0.1', port=8080, debug=True)  # 非命令启动
