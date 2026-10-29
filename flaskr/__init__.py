import importlib
import os
from pathlib import Path

from flask import Blueprint, Flask
from sqlalchemy import select

from flaskr.core.config import config_by_name
from flaskr.core.error_handler import ErrorHandler
from flaskr.core.extensions import cors, db, jwt, migrate

DEFAULT_CONFIG = "development"

base_path = Path(__file__).resolve().parent
domains_path = base_path / "domains"


def load_all_models():  # Necessary for migrate command
    for path in domains_path.glob("*/models.py"):
        domain_name = path.parent.name
        domain_path = f"flaskr.domains.{domain_name}.models"

        try:
            importlib.import_module(domain_path)
        except Exception as e:
            print(f"Error with models loading, domain name: {domain_name}. {e}")
        print(f"Successfully entity loaded: {domain_name}")


def register_blueprints(app: Flask):  # Registration to endpoints. --SOLID--
    for path in domains_path.glob("*/__init__.py"):
        domain_name = path.parent.name
        domain_path = f"flaskr.domains.{domain_name}"

        try:
            domain = importlib.import_module(domain_path)
            if hasattr(domain, "bp") and isinstance(domain.bp, Blueprint):
                blueprint = domain.bp
                app.register_blueprint(blueprint)
                print(f"Successfully registered blueprint: {blueprint.name}")
            else:
                print("domain has not a bp object")
        except Exception as e:
            print(f"Error with blueprints loading, domain name: {domain_name}. {e}")


def create_app(config_name: str = DEFAULT_CONFIG):
    config_class = config_by_name.get(config_name)
    if config_class is None:
        raise ValueError(f"Invalid configuration name: {config_name}")

    if config_name == "prod":
        if not os.environ.get("SECRET_KEY") or not os.environ.get("JWT_SECRET_KEY"):
            raise ValueError(
                "SECRET_KEY and JWT_SECRET_KEY environment variables must be set in production."
            )

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    ErrorHandler.init_app(app)
    app.json.sort_keys = False

    with app.app_context():
        load_all_models()

    register_blueprints(app)
    jwt.init_app(app)

    from flaskr.domains.auth.models import TokenBlocklist

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = db.session.execute(
            select(TokenBlocklist).filter_by(jti=jti)
        ).scalar_one_or_none()
        return token is not None

    return app
