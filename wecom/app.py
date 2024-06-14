# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
from importlib import import_module

from flask import Flask, render_template

from .apps import user, worktool
from .core import commands
from wecom.apps.user.models.user import WecomUser
from .utils.log import get_logger, logger
from .core.extensions import (
    bcrypt,
    cache,
    csrf_protect,
    db,
    login_manager,
    debug_toolbar,
    flask_static_digest,
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
        app.logger.error('register_errorhandlers => error: %s', error)
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
    get_logger(app=app)


@login_manager.user_loader
def load_user(user_id):
    logger.info("load_user user_id: %s", user_id)
    return WecomUser.query.get(1)
