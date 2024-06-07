# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
import sys
import logging
from logging.handlers import RotatingFileHandler
from importlib import import_module

from flask import Flask, render_template

from .apps import user, worktool
from .core import commands
from .core.extensions import (
    bcrypt,
    cache,
    csrf_protect,
    db,
    debug_toolbar,
    flask_static_digest,
    login_manager,
    migrate,
)


def create_app(config_object="config.settings"):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    configure_logger(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    bcrypt.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    csrf_protect.init_app(app)
    login_manager.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    flask_static_digest.init_app(app)
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(worktool.views.blueprint)

    # Register celery_helper.beat package
    beat_pkg = import_module(__package__ + ".celery_helper.beat")
    beat_bp = getattr(beat_pkg, 'blueprint', None)
    beat_bp and app.register_blueprint(beat_bp)

    return None


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        print(f'register_errorhandlers => error_code: {error_code}')
        return render_template(f"{error_code}.html"), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """Register shell context objects."""

    def shell_context():
        """Shell context objects."""
        return {"db": db, "User": user.models.User}

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)


def configure_logger(app):
    """Configure loggers."""
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # 创建一个RotatingFileHandler，当文件达到200MB时分割，最多保留5个备份文件
    file_handler = RotatingFileHandler('app.log', maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    # 创建一个StreamHandler用于输出到控制台
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # 设置日志级别为INFO
    file_handler.setLevel(logging.INFO)
    stream_handler.setLevel(logging.INFO)

    # 添加处理器到日志记录器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
