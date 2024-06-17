# -*- coding: utf-8 -*-
"""Create an application instance."""
from flask_security.utils import hash_password
from flask_security import Security, SQLAlchemySessionUserDatastore

from wecom.app import create_app
from wecom.core.database import db
from wecom.apps.user.models.user import WecomUser, Role

app = create_app()

user_datastore = SQLAlchemySessionUserDatastore(db.session, WecomUser, Role)
# security = Security(app, user_datastore)


# @app.before_first_request
def create_user():
    db.create_all()
    if not user_datastore.find_user(email="test@example.com"):
        user_datastore.create_user(email="test@example.com", password=hash_password("password"))
        db.session.commit()


if __name__ == '__main__':
    # flask --app runserver db [init, migrate, upgrade, ...]
    # gunicorn --log-level debug  -w 1 --threads 10  --timeout 120 -b 0.0.0.0:9999 runserver:app -D
    # gunicorn --worker-class=gthread --log-level debug  -w 1 --threads 10  --timeout 120 -b 0.0.0.0:9999 runserver:app -D
    with app.app_context():
        app.run(host='0.0.0.0', port=9999, debug=True, use_reloader=True)  # 非命令启动
