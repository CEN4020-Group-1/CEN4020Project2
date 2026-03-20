import os
from flask import Flask
from .routes import main_routes
from .file_routes import file_routes
from .schedule_routes import schedule_routes


def create_app():
    templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

    app = Flask(__name__, template_folder=templates_path)

    app.register_blueprint(main_routes)
    app.register_blueprint(file_routes)
    app.register_blueprint(schedule_routes)

    return app
