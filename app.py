import sqlite3
import os
from flask import Flask, render_template, request, g, flash, redirect, url_for, session, abort
from DataBase import DataBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from UserLogin import UserLogin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, validators, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length




# Конфигурация приложения
DATABASE = '/tmp/kokos.db'
DEBUG = True
SECRET_KEY = 'kokos_secret_key_123'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'kokos.db')))

# Инициализация Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите в аккаунт для доступа к страницам'


@login_manager.user_loader
def load_user(user_id):
    return UserLogin().fromDB(user_id, dbase)

def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def create_db():
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

dbase = None
@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = DataBase(db)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


# WTForms для регистрации
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

# WTForms для авторизации
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

# WTForms для сброса пароля
class PasswordResetForm(FlaskForm):
    email = StringField('Ваш Email', validators=[DataRequired(), Email()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired()])
    submit = SubmitField('Сменить пароль')

# WTForms для обновления профиля
class ProfileForm(FlaskForm):
    username = StringField('Имя', validators=[DataRequired()])
    email = StringField('Почта', validators=[DataRequired(), Email()])
    password = PasswordField('Новый пароль (если нужно сменить)')
    submit = SubmitField('Обновить данные')
    
# Форма для новостей
class NewsForm(FlaskForm):
    title = StringField('Заголовок', validators=[validators.DataRequired(), validators.Length(min=5, max=100)])
    image_url = StringField('Ссылка на изображение', validators=[validators.DataRequired(), validators.Length(min=5, max=255)])
    short_description = TextAreaField('Краткое описание', validators=[validators.DataRequired(), validators.Length(min=10, max=255)])
    category = SelectField('Category', choices=[('team', 'Team'),('matches', 'Matches'),('store', 'Store'),('events', 'Events')
    ], validators=[DataRequired()])
    full_text = TextAreaField('Полный текст', validators=[validators.DataRequired()])
    submit = SubmitField('Добавить новость')

# Форма для магазина
class ProductForm(FlaskForm):
    title = StringField('Наименование', validators=[validators.DataRequired(), validators.Length(min=5, max=100)])
    image_url = StringField('Ссылка на изображение', validators=[validators.DataRequired(), validators.Length(min=5, max=255)])
    info = TextAreaField('Краткое описание', validators=[validators.DataRequired(), validators.Length(min=10, max=255)])
    category = SelectField('Category', choices=[('clothes', 'Clothes'),('accessories', 'Accessories'),('other', 'Other')], validators=[DataRequired()])
    submit = SubmitField('Создать товар')


@app.route('/')
def index():
    return render_template('index.html', title='Главная')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user_exists = dbase.getUserByEmail(form.email.data)
        if not user_exists:
            dbase.addUser(form.username.data, form.email.data, hashed_password)
            flash('Регистрация прошла успешно! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким email уже существует', 'error')
    return render_template('register.html', form=form, title='Регистрация')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user_row = dbase.getUserByEmail(form.email.data)  # получаем строку из базы данных
        if user_row and check_password_hash(user_row['password'], form.password.data):
            user_login = UserLogin().create(user_row)  # создаем объект UserLogin
            login_user(user_login, remember=True if form.remember_me.data else False)  # передаем объект UserLogin в login_user
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверный email или пароль', 'error')
    return render_template('login.html', form=form, title='Авторизация')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта')
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(username=current_user.username, email=current_user.email)

    if form.validate_on_submit():
        updated = dbase.updateUser(current_user.get_id(), form.username.data, form.email.data)
        updated_password = dbase.updatePassword(current_user.get_id(), generate_password_hash(form.password.data))
        if updated:
            flash('Данные обновлены!', 'success')
        elif updated_password:
            flash('Пароль обновлен!', 'success')
        else:
            flash('Ошибка обновления данных или пароля', 'error')
    return render_template('profile.html', form=form, title='Профиль')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = dbase.getUserByEmail(form.email.data)
        if user:
            new_password_hash = generate_password_hash(form.new_password.data)
            dbase.updatePassword(user['id'], new_password_hash)
            flash('Пароль успешно изменен!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким email не найден', 'error')
    return render_template('forgot_password.html', form=form, title='Восстановление пароля')


@app.route('/news')
def news():
    category_filter = request.args.get('category', 'all')
    news_list = dbase.getAllNews() if category_filter == 'all' else dbase.getNewsByCategory(category_filter)

    if not news_list:  # Если функция вернула False или пустой список
        news_list = []  # Пустой список, чтобы избежать ошибки
        flash('Нет доступных новостей', 'info')

    return render_template('news.html', news_list=news_list)


@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news_item = dbase.getNewsById(news_id)
    return render_template('news_detail.html', news=news_item)


@app.route('/admin/delete/<int:news_id>', methods=['GET'])
@login_required
def delete_news(news_id):
    if not current_user.is_admin():
        abort(403)  # Доступ запрещен

    if dbase.deleteNews(news_id):
        flash('Новость удалена!', 'success')
    else:
        flash('Ошибка при удалении новости', 'error')

    return redirect(url_for('admin'))


@app.route('/products')
def products():
    category_filter = request.args.get('category', 'all')
    product_list = dbase.getAllProducts() if category_filter == 'all' else dbase.getProductsByCategory(category_filter)

    if not product_list:  # Если функция вернула False или пустой список
        product_list = []  # Пустой список, чтобы избежать ошибки
        flash('Нет доступных новостей', 'info')

    return render_template('products.html', product_list=product_list)


@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product_item = dbase.getProductsById(product_id)
    return render_template('product_detail.html', product=product_item)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)  # Доступ запрещен

    formNews = NewsForm()
    formProduct = ProductForm()
    if formNews.validate_on_submit():
        # Добавление новости в базу данных
        dbase.addNews(formNews.title.data, formNews.image_url.data, formNews.short_description.data, formNews.category.data, formNews.full_text.data)
        flash('Новость добавлена!', 'success')
        return redirect(url_for('admin'))
    
    if formProduct.validate_on_submit():
        #Добавление продукта в базу данных
        dbase.addProduct(formProduct.title.data, formProduct.image_url.data, formProduct.info.data, formProduct.category.data)
        flash('Продукт добавлен!', 'success')

    # Получаем список всех новостей для отображения
    news_list = dbase.getAllNews()
    return render_template('admin.html', formNews=formNews, news_list=news_list, formProduct=formProduct)



if __name__ == '__main__':
    create_db() #Временное решение для более быстрой разработки. Далее Создание новых таблиц в БД будет осуществлятся либо в терминале, либо в отдельном файле
    app.run(debug=True)