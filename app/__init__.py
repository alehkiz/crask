from flask import Flask
from app.core.configure import init
from app.core.db import fake_db_command
from config.config import config


def create_app(mode='production'):
    app = Flask(__name__)
    app.config.from_object(config[mode])
    init(app)
    app.cli.add_command(fake_db_command)
    return app