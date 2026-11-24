from flask import Blueprint

bp = Blueprint("check", __name__, url_prefix="/checks")

from . import routes  # noqa F401
