from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

from config import Config
from utils.data_manager import DataManager

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация менеджера логина
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация менеджера данных
data_manager = DataManager(app.config)


# Модель пользователя
class User:
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.role = user_data['role']
        self.password_hash = user_data['password_hash']

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    users = data_manager.load_users()
    for user in users:
        if str(user['id']) == user_id:
            return User(user)
    return None


# ========== РОУТЫ ==========

# Главная страница
@app.route('/')
def index():
    games = data_manager.load_games()
    return render_template('index.html', games=games)


# Просмотр инструкции (только для мат биржи)
@app.route('/instruction/<int:game_id>')
def view_instruction(game_id):
    if game_id != 1:
        flash('Инструкция доступна только для игры "Математическая биржа"', 'error')
        return redirect(url_for('index'))

    games = data_manager.load_games()
    game = next((g for g in games if g['id'] == game_id), None)

    if not game:
        flash('Игра не найдена', 'error')
        return redirect(url_for('index'))

    return render_template('instruction.html', game=game)


# Страница игры
@app.route('/game/<int:game_id>')
def game_page(game_id):
    games = data_manager.load_games()
    game = next((g for g in games if g['id'] == game_id), None)

    if not game:
        flash('Игра не найдена', 'error')
        return redirect(url_for('index'))

    tournaments = data_manager.load_tournaments()
    game_tournaments = [t for t in tournaments if t['game_id'] == game_id]

    return render_template('game.html', game=game, tournaments=game_tournaments)


# Табло турнира (публичное)
@app.route('/tournament/<int:tournament_id>/leaderboard')
def tournament_leaderboard(tournament_id):
    tournaments = data_manager.load_tournaments()
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)

    if not tournament:
        flash('Турнир не найден', 'error')
        return redirect(url_for('index'))

    submissions = data_manager.load_submissions()
    tournament_submissions = [s for s in submissions if s['tournament_id'] == tournament_id]

    # Получаем уникальные команды
    teams = list(set([s['team_name'] for s in tournament_submissions]))

    # Подсчет баллов для каждой команды
    team_scores = {}
    team_details = {}
    for team in teams:
        team_subs = [s for s in tournament_submissions if s['team_name'] == team]
        total_score = sum(s.get('points', 0) for s in team_subs)
        team_scores[team] = total_score
        team_details[team] = {
            'total': total_score,
            'submissions': sorted(team_subs, key=lambda x: x['task_number'])
        }

    # Сортируем команды по баллам
    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)

    return render_template('leaderboard.html',
                           tournament=tournament,
                           submissions=tournament_submissions,
                           teams=teams,
                           team_scores=dict(sorted_teams),
                           team_details=team_details)


# Страница ввода пароля для жюри
@app.route('/tournament/<int:tournament_id>/jury', methods=['GET', 'POST'])
@login_required
def jury_tournament(tournament_id):
    if current_user.role not in ['jury', 'organizer']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))

    tournaments = data_manager.load_tournaments()
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)

    if not tournament:
        flash('Турнир не найден', 'error')
        return redirect(url_for('index'))

    # Если GET запрос - показываем форму ввода пароля
    if request.method == 'GET':
        return render_template('jury_password.html', tournament=tournament)

    # Если POST запрос - проверяем пароль
    password = request.form.get('tournament_password')

    if not tournament.get('password') or tournament['password'] != password:
        flash('Неверный пароль турнира', 'error')
        return render_template('jury_password.html', tournament=tournament)

    # Пароль верный - показываем панель жюри
    return render_template('jury_panel.html', tournament=tournament)


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([username, email, password, role]):
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))

        users = data_manager.load_users()

        if any(u['username'] == username for u in users):
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('register'))

        if any(u['email'] == email for u in users):
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('register'))

        new_user = {
            'id': len(users) + 1,
            'username': username,
            'email': email,
            'role': role,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now().isoformat()
        }

        users.append(new_user)
        data_manager.save_users(users)

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        users = data_manager.load_users()
        user_data = next((u for u in users if u['username'] == username), None)

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            flash('Вход выполнен успешно', 'success')

            if user.role == 'organizer':
                return redirect(url_for('organizer_dashboard'))
            else:
                return redirect(url_for('jury_dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


# Панель организатора (только свои турниры)
@app.route('/organizer')
@login_required
def organizer_dashboard():
    if current_user.role != 'organizer':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))

    games = data_manager.load_games()
    all_tournaments = data_manager.load_tournaments()

    # Фильтруем турниры только созданные текущим организатором
    my_tournaments = [t for t in all_tournaments if t.get('created_by') == current_user.id]

    return render_template('organizer.html', games=games, tournaments=my_tournaments)


# Создание турнира
@app.route('/organizer/create_tournament', methods=['POST'])
@login_required
def create_tournament():
    if current_user.role != 'organizer':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))

    name = request.form.get('name')
    game_id = request.form.get('game_id')
    location = request.form.get('location')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    password = request.form.get('password')

    if not all([name, game_id, location, start_date, end_date, password]):
        flash('Все поля обязательны для заполнения', 'error')
        return redirect(url_for('organizer_dashboard'))

    tournaments = data_manager.load_tournaments()

    new_tournament = {
        'id': len(tournaments) + 1,
        'name': name,
        'game_id': int(game_id),
        'location': location,
        'status': 'upcoming',
        'start_date': start_date,
        'end_date': end_date,
        'password': password,
        'created_by': current_user.id,
        'created_at': datetime.now().isoformat()
    }

    tournaments.append(new_tournament)
    data_manager.save_tournaments(tournaments)

    flash(f'Турнир "{name}" успешно создан! Пароль для жюри: {password}', 'success')
    return redirect(url_for('organizer_dashboard'))


# Удаление турнира (только свои)
@app.route('/organizer/delete_tournament/<int:tournament_id>', methods=['POST'])
@login_required
def delete_tournament(tournament_id):
    if current_user.role != 'organizer':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))

    tournaments = data_manager.load_tournaments()
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)

    if not tournament:
        flash('Турнир не найден', 'error')
        return redirect(url_for('organizer_dashboard'))

    # Проверяем, что турнир создан текущим организатором
    if tournament.get('created_by') != current_user.id:
        flash('Вы можете удалять только свои турниры', 'error')
        return redirect(url_for('organizer_dashboard'))

    # Удаляем турнир
    tournaments = [t for t in tournaments if t['id'] != tournament_id]
    data_manager.save_tournaments(tournaments)

    # Также удаляем все результаты этого турнира
    submissions = data_manager.load_submissions()
    submissions = [s for s in submissions if s['tournament_id'] != tournament_id]
    data_manager.save_submissions(submissions)

    flash(f'Турнир "{tournament["name"]}" удален', 'success')
    return redirect(url_for('organizer_dashboard'))


# Панель жюри
@app.route('/jury')
@login_required
def jury_dashboard():
    if current_user.role not in ['jury', 'organizer']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))

    tournaments = data_manager.load_tournaments()
    active_tournaments = [t for t in tournaments if t['status'] in ['active', 'upcoming']]

    return render_template('jury_dashboard.html', tournaments=active_tournaments)


# API для добавления результата жюри
@app.route('/api/submit_result', methods=['POST'])
@login_required
def submit_result():
    if current_user.role not in ['jury', 'organizer']:
        return jsonify({'error': 'Доступ запрещен'}), 403

    data = request.get_json()

    required_fields = ['tournament_id', 'team_name', 'task_number', 'bet', 'is_correct']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Не все поля заполнены'}), 400

    tournaments = data_manager.load_tournaments()
    tournament = next((t for t in tournaments if t['id'] == data['tournament_id']), None)
    if not tournament:
        return jsonify({'error': 'Турнир не найден'}), 404

    # Проверяем, может ли команда сделать такую ставку
    submissions = data_manager.load_submissions()
    team_submissions = [s for s in submissions if
                        s['tournament_id'] == data['tournament_id'] and s['team_name'] == data['team_name']]
    current_score = sum(s.get('points', 0) for s in team_submissions)

    # Проверяем, хватит ли баллов для ставки
    if not data['is_correct'] and abs(current_score) < data['bet']:
        return jsonify(
            {'error': f'У команды недостаточно баллов. Текущий счет: {current_score}, ставка: {data["bet"]}'}), 400

    # Новая логика подсчета: правильно = +ставка, неправильно = -ставка
    if data['is_correct']:
        points = data['bet']
    else:
        points = -data['bet']

    new_submission = {
        'id': data_manager.get_next_submission_id(),
        'tournament_id': data['tournament_id'],
        'team_name': data['team_name'],
        'task_number': data['task_number'],
        'bet': data['bet'],
        'is_correct': data['is_correct'],
        'points': points,
        'judge_id': current_user.id,
        'submitted_at': datetime.now().isoformat()
    }

    submissions.append(new_submission)
    data_manager.save_submissions(submissions)

    return jsonify({'success': True, 'submission': new_submission})


# Получение данных для таблицы
@app.route('/api/tournament_data/<int:tournament_id>')
def get_tournament_data(tournament_id):
    submissions = data_manager.load_submissions()
    tournament_submissions = [s for s in submissions if s['tournament_id'] == tournament_id]

    # Получаем текущие счета команд
    team_scores = {}
    for sub in tournament_submissions:
        team = sub['team_name']
        if team not in team_scores:
            team_scores[team] = 0
        team_scores[team] += sub.get('points', 0)

    teams_data = {}
    for sub in tournament_submissions:
        team = sub['team_name']
        if team not in teams_data:
            teams_data[team] = {
                'total': team_scores[team],
                'tasks': {},
                'current_score': team_scores[team]
            }

        task_key = f"task_{sub['task_number']}"
        if task_key not in teams_data[team]['tasks']:
            teams_data[team]['tasks'][task_key] = 0

        teams_data[team]['tasks'][task_key] += sub.get('points', 0)

    return jsonify({
        'submissions': tournament_submissions,
        'teams_data': teams_data,
        'team_scores': team_scores
    })


# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Только создаем игры, без пользователей
    data_manager.initialize_games_only()

    app.run(debug=True, port=5000)