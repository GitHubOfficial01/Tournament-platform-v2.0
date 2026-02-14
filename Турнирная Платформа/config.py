import os
from datetime import datetime


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATA_DIR = 'data'
    UPLOAD_FOLDER = 'instructions'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Пути к файлам данных
    GAMES_FILE = os.path.join(DATA_DIR, 'games.json')
    TOURNAMENTS_FILE = os.path.join(DATA_DIR, 'tournaments.json')
    USERS_FILE = os.path.join(DATA_DIR, 'users.json')
    SUBMISSIONS_FILE = os.path.join(DATA_DIR, 'submissions.json')