import json
import os
from datetime import datetime


class DataManager:
    def __init__(self, config):
        self.config = config

    def load_data(self, file_path, default_data=None):
        if default_data is None:
            default_data = []

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return default_data.copy()
        return default_data.copy()

    def save_data(self, file_path, data):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_games(self):
        return self.load_data(self.config['GAMES_FILE'], [])

    def save_games(self, games):
        self.save_data(self.config['GAMES_FILE'], games)

    def load_tournaments(self):
        return self.load_data(self.config['TOURNAMENTS_FILE'], [])

    def save_tournaments(self, tournaments):
        self.save_data(self.config['TOURNAMENTS_FILE'], tournaments)

    def load_users(self):
        return self.load_data(self.config['USERS_FILE'], [])

    def save_users(self, users):
        self.save_data(self.config['USERS_FILE'], users)

    def load_submissions(self):
        return self.load_data(self.config['SUBMISSIONS_FILE'], [])

    def save_submissions(self, submissions):
        self.save_data(self.config['SUBMISSIONS_FILE'], submissions)

    def get_next_submission_id(self):
        submissions = self.load_submissions()
        if submissions:
            return max(s['id'] for s in submissions) + 1
        return 1

    def initialize_games_only(self):
        """Инициализация только игр, без тестовых пользователей и турниров"""
        games = self.load_games()
        if not games:
            games = [
                {
                    'id': 1,
                    'name': 'Математическая биржа',
                    'description': 'Экономическая игра, основанная на математических моделях',
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 2,
                    'name': 'Экономический прорыв',
                    'description': 'Стратегическая игра по управлению экономикой',
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 3,
                    'name': 'Логический лабиринт',
                    'description': 'Игра на развитие логического мышления',
                    'created_at': datetime.now().isoformat()
                }
            ]
            self.save_games(games)