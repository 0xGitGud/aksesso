import os
import json
from flask import Flask, request, flash, session, url_for, redirect, render_template, jsonify
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sqlalchemy import distinct
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime

app = Flask(__name__)
app.static_folder = 'static'
bcrypt = Bcrypt(app)

app.config['SECRET_KEY'] = 'mysecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aksesso.sqlite3'
app.config['SECRET_KEY'] = "random string"
app.config['UPLOAD_FOLDER'] = 'C:/Users/USER/PycharmProjects/aksesso/static/thumbnail'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    type = db.Column(db.String(50), nullable=False, default='user')
    scores = db.Column(db.String(100), nullable=True)
    finish_time = db.Column(db.DateTime, nullable=True)
    profile_picture = db.Column(db.String(100), nullable=True)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi.id'), nullable=False)
    date_completed = db.Column(db.DateTime, default=datetime.now)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    option1 = db.Column(db.String(255), nullable=False)
    option2 = db.Column(db.String(255), nullable=False)
    option3 = db.Column(db.String(255), nullable=False)
    option4 = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255), nullable=True)

class Preset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=True)

class Materi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    thumbnail = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.now)
    chapter = db.Column(db.Integer)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi.id'), nullable=False)
    materi = db.relationship('Materi', backref=db.backref('attachments', lazy=True))

class Posting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file = db.Column(db.String(255), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    comments = db.relationship('Comment', backref='post', lazy=True)

    @property
    def author_name(self):
        return User.query.get(self.author_id).name

    @property
    def author_profile_picture(self):
        author = User.query.get(self.author_id)
        return author.profile_picture if author else None

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posting.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def comment_name(self):
        return User.query.get(self.author_id).name

    @property
    def comment_profile_picture(self):
        author = User.query.get(self.author_id)
        return author.profile_picture if author else None

db.create_all()

class LoginForm(FlaskForm):
    email = StringField(validators=[
        InputRequired(), Length(min=1, max=40)])

    password = PasswordField(validators=[
        InputRequired(), Length(min=1, max=30)])

    submit = SubmitField('Login')

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('Email belum terdaftar', 'warning')
            return redirect(url_for('login'))
        session['username'] = user.name
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                session['email'] = user.email
                login_user(user)
                if user.type == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('home'))
            else:
                flash('Password salah !', 'danger')

    success_message = request.args.get('success_message')
    return render_template('login.html', form=form, success_message=success_message)

@app.route('/login', methods=['GET', 'POST'])
def loginlagi():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        session['username'] = user.name
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('home'))

    success_message = request.args.get('success_message')
    return render_template('login.html', form=form, success_message=success_message)

@app.route('/formRegister')
def formRegister():
    return render_template('register.html')

@app.route('/registerProses', methods=['POST'])
def proses_register():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    if user:
        flash('Email Sudah ada', 'danger')
        return redirect(url_for('formRegister'))

    hashed_password = bcrypt.generate_password_hash(password)
    new_user = User(email=email, name=name, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()
    flash('Akun berhasil dibuat', 'success')

    return redirect(url_for('login', success_message='Akun berhasil dibuat'))

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    user = current_user

    if request.method == 'POST':
        new_name = request.form['name']

        if new_name != current_user.name:
            user.name = new_name
            db.session.commit()
            session['username'] = current_user.name
            flash('Akun Anda telah diperbarui!', 'success')
        else:
            flash('Nama yang diinput sama dengan nama saat ini.', 'warning')

        return redirect(url_for('profil'))

    return render_template('akun.html')

@app.route('/profil/picture', methods=['POST'])
@login_required
def profil_picture():
    if 'profile_picture' in request.files:
        # Get the file from the request object
        profile_picture = request.files['profile_picture']

        try:
            # Save the file to a folder on your server
            filename = secure_filename(profile_picture.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(filepath)

            # Store filename in the database
            current_user.profile_picture = filename
            db.session.commit()

            flash('Foto profil berhasil diubah!', 'success')
        except (FileNotFoundError):
            flash('Gagal mengubah foto profil. Mohon pilih file yang valid.', 'danger')
    else:
        flash('Gagal mengubah foto profil. File tidak ditemukan.', 'danger')

    return redirect(url_for('profil'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('admin.html')

@app.route('/adminquiz')
@login_required
def adminquiz():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('menuquiz.html')

@app.route('/soaladd')
@login_required
def soaladd():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('addsoal.html')

@app.route("/addsoal", methods=["POST", "GET"])
@login_required
def add_question():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return

    if request.method == "POST":
        ques = request.form.get('question')
        op1 = request.form.get('op1')
        op2 = request.form.get('op2')
        op3 = request.form.get('op3')
        op4 = request.form.get('op4')
        cor = request.form.get('corop')

        # get the uploaded file
        image = request.files['image']

        if image.filename != '':
            # save the file with a safe filename
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = filename
        else:
            image = None

        new_question = Question(
            question=ques,
            option1=op1,
            option2=op2,
            option3=op3,
            option4=op4,
            correct_option=cor,
            image=image
        )

        try:
            db.session.add(new_question)
            db.session.commit()
            flash('Berhasil menambahkan soal.', 'success')
            return redirect(url_for('adminquiz'))
        except IntegrityError:
            db.session.rollback()
            flash('Gagal menambahkan soal.', 'danger')
            return redirect(url_for('admin'))

    return render_template('menuquiz.html')

@app.route('/editsoal/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return

    question = Question.query.get_or_404(question_id)

    if request.method == 'POST':
        # handle form submission and update question in database
        question.question = request.form['question']
        question.option1 = request.form['op1']
        question.option2 = request.form['op2']
        question.option3 = request.form['op3']
        question.option4 = request.form['op4']
        question.correct_option = request.form['corop']

        # handle image upload
        image = request.files['image']
        if image.filename != '':
            # save the file with a safe filename
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            question.image = filename
        else:
            image = None

        db.session.commit()
        flash('Soal telah diupdate!', 'secondary')
        return redirect(url_for('listsoal'))

    # pre-populate form fields with current values
    question_data = {
        'question': question.question,
        'option1': question.option1,
        'option2': question.option2,
        'option3': question.option3,
        'option4': question.option4,
        'correct_option': question.correct_option
    }

    return render_template('editsoal.html', question=question, question_data=question_data)

@app.route('/deletesoal/<int:question_id>', methods=['GET', 'POST'])
def delete_question(question_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    question = Question.query.get_or_404(question_id)
    # handle delete question logic here
    db.session.delete(question)
    db.session.commit()
    flash('Soal telah dihapus!', 'warning')
    return redirect(url_for('listsoal'))

@app.route('/listsoal')
@login_required
def listsoal():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    questions = Question.query.all()
    presets = Preset.query.all()
    return render_template('daftarsoal.html', questions=questions, presets=presets)

@app.route('/getpreset', methods=['GET', 'POST'])
@login_required
def getpreset():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
        # Update the presets file
        now = datetime.now()
        filename = f"preset_{now.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        presets_file = os.path.join(app.static_folder, 'preset', filename)
        if not os.path.exists(presets_file):
            with open(presets_file, 'w') as f:
                f.write('[]')
        with open(presets_file) as f:
            presets = json.load(f)
        questions = Question.query.all()
        new_preset = []
        for q in questions:
            new_preset.append({
                'id': q.id,
                'question': q.question,
                'option1': q.option1,
                'option2': q.option2,
                'option3': q.option3,
                'option4': q.option4,
                'correct_option': q.correct_option
            })
        presets.append(new_preset)
        new_preset = Preset(filename=filename)
        db.session.add(new_preset)
        db.session.commit()
        with open(presets_file, 'w') as f:
            json.dump(presets, f)
            # Check if a JSON response is requested
            if request.args.get('type') == 'json':
                return jsonify({'success': True})
            # Otherwise, render the template
            flash('Preset disimpan!', 'success')
            return render_template('menuquiz.html')

@app.route('/loadpreset/<int:id>')
@login_required
def load_preset(id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    preset = Preset.query.get_or_404(id)
    presets_file = os.path.join(app.static_folder, 'preset', preset.filename)
    with open(presets_file) as f:
        presets = json.load(f)

    preset_questions = presets[0]  # extract questions from the preset list

    # Delete all existing questions
    db.session.query(Question).delete()

    # Add the new questions to the database
    for question in preset_questions:
        q = Question(
            question=question['question'],
            option1=question['option1'],
            option2=question['option2'],
            option3=question['option3'],
            option4=question['option4'],
            correct_option=question['correct_option']
        )
        db.session.add(q)
    db.session.commit()

    flash('Preset berhasil dimuat!', 'success')
    return redirect(url_for('adminquiz'))

@app.route('/adminmateri')
@login_required
def adminmateri():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('menumateri.html')

@app.route('/materiadd')
@login_required
def materiadd():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('addmateri.html')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/addmateri', methods=['GET', 'POST'])
@login_required
def add_materi():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    if request.method == 'POST':
        # Get the uploaded files
        attachment = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                attachment = filename

        thumbnail = request.files['thumbnail']
        if thumbnail.filename != '' and allowed_file(thumbnail.filename):
            thumbnail_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.jpg"
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)
            thumbnail.save(thumbnail_path)
        else:
            thumbnail_filename = None

        title = request.form['title']
        text = request.form['text']
        chapter = request.form['chapter']
        cms = Materi(title=title, content=text, chapter=chapter, thumbnail=thumbnail_filename)
        if attachment:
            cms.attachments.append(Attachment(file_name=attachment))
        db.session.add(cms)
        db.session.commit()
        flash('Materi telah ditambahkan!', 'success')
        return redirect(url_for('adminmateri'))

    return render_template('addmateri.html')

@app.route('/listmateri', methods=['GET', 'POST'])
@login_required
def listmateri():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    materi = Materi.query.all()
    chapter = db.session.query(distinct(Materi.chapter)).filter(Materi.chapter != None).order_by(Materi.chapter).all()
    return render_template('daftarmateri.html', materi=materi, chapter_numbers=chapter, grid_clicked=session.get('grid_clicked', 'True'))

@app.route('/chapter/<int:chapter>')
def show_materi_by_chapter(chapter):
    print(chapter)
    materi = Materi.query.filter_by(chapter=chapter).all()
    number = db.session.query(distinct(Materi.chapter)).filter(Materi.chapter != None).order_by(Materi.chapter).all()
    return render_template('daftarmateri.html', materi=materi, chapter=chapter, chapter_numbers=number, grid_clicked=session.get('grid_clicked', 'True'))

@app.route('/update_grid_clicked', methods=['POST'])
@login_required
def update_grid_clicked():
  is_grid = request.form.get('is_grid', 'False') == 'True'
  session['grid_clicked'] = is_grid
  print("Grid Clicked:", session['grid_clicked'])
  return redirect(url_for('listmateri'))

@app.route('/editmateri/<int:materi_id>', methods=['GET', 'POST'])
@login_required
def edit_materi(materi_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    materi = Materi.query.get_or_404(materi_id)
    attachments = Attachment.query.filter_by(materi_id=materi_id).all()
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'thumbnail' in request.files:
            thumbnail = request.files['thumbnail']
            # If user does not select file, browser also submit an empty part without filename
            if thumbnail.filename != '' and allowed_file(thumbnail.filename):
                thumbnail_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.jpg"
                thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)
                thumbnail.save(thumbnail_path)
                materi.thumbnail = thumbnail_filename

        materi.chapter = request.form['chapter']
        materi.title = request.form['title']
        materi.content = request.form['text']

        # Save new attachments
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                if materi.attachments:
                    # Delete existing attachment
                    db.session.delete(materi.attachments[0])
                attachment = Attachment(file_name=filename, materi_id=materi_id)
                db.session.add(attachment)

        db.session.commit()
        flash('Materi telah diupdate!', 'success')
        return redirect(url_for('adminmateri'))
    return render_template('editmateri.html', materi=materi, attachments=attachments)

@app.route('/deletemateri/<int:materi_id>', methods=['GET', 'POST'])
def delete_materi(materi_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    materi = Materi.query.get_or_404(materi_id)
    Attachment.query.filter_by(materi_id=materi_id).delete()
    db.session.delete(materi)
    db.session.commit()
    flash('Materi telah dihapus!', 'warning')
    return redirect(url_for('adminmateri'))

@app.route('/materi')
@login_required
def materi():
    materi = Materi.query.all()
    chapter = db.session.query(distinct(Materi.chapter)).filter(Materi.chapter != None).order_by(Materi.chapter).all()
    user_progress = {}
    for m in materi:
        user_progress[m.id] = UserProgress.query.filter_by(user_id=current_user.id, materi_id=m.id).first()
    return render_template('premateri.html', materi=materi, chapter=chapter, chapter_numbers=chapter, user_progress=user_progress)

@app.route('/babmateri/<int:chapter>')
def show_materi_by_bab(chapter):
    print(chapter)
    materi = Materi.query.filter_by(chapter=chapter).all()
    number = db.session.query(distinct(Materi.chapter)).filter(Materi.chapter != None).order_by(Materi.chapter).all()
    user_progress = {}
    for m in materi:
        user_progress[m.id] = UserProgress.query.filter_by(user_id=current_user.id, materi_id=m.id).first()
    return render_template('premateri.html', materi=materi, chapter=chapter, chapter_numbers=number, user_progress=user_progress)

@app.route('/belajar/<int:id>')
@login_required
def belajar(id):
    post = Materi.query.get_or_404(id)

    prev_post = Materi.query.filter(Materi.id < id).order_by(Materi.id.desc()).first()
    next_post = Materi.query.filter(Materi.id > id).order_by(Materi.id.asc()).first()

    # Check if the user has completed this materi before
    user_progress = UserProgress.query.filter_by(user_id=current_user.id, materi_id=post.id).first()

    if prev_post and current_user.type != 'admin':
        prev_materi_progress = UserProgress.query.filter_by(user_id=current_user.id, materi_id=prev_post.id).first()
        if not prev_materi_progress and id != 1:
            flash('Selesaikan materi sebelumnya terlebih dahulu.', 'warning')
            return redirect(url_for('materi'))
    elif next_post and current_user.type != 'admin':
        next_materi_progress = UserProgress.query.filter_by(user_id=current_user.id, materi_id=next_post.id).first()
        if not next_materi_progress and id != 1:
            flash('Selesaikan materi ini terlebih dahulu.', 'warning')
            return redirect(url_for('materi'))

    if not user_progress:
        # If the user hasn't completed this materi before, add a new entry to the UserProgress table
        user_progress = UserProgress(user_id=current_user.id, materi_id=post.id, date_completed=datetime.now())
        db.session.add(user_progress)
        db.session.commit()

    return render_template('materi.html', post=post, prev_post=prev_post, next_post=next_post)

@app.route('/attachment/<int:id>')
@login_required
def attachment(id):
    attachment = Attachment.query.get_or_404(id)
    return render_template('attachment.html', attachment=attachment)

@app.route('/quiz')
@login_required
def quiz():
    session['attempts'] = []
    return render_template('prequiz.html', user=current_user)

@app.route('/mulai')
@login_required
def mulai():
    questions = Question.query.all()
    total_questions = len(questions)

    return render_template('quiz.html', questions=questions, total_questions=total_questions)

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    user = current_user

    # Load questions from the database
    questions = Question.query.all()
    attempts = []
    score = 0

    for question in questions:
        mcq = question.id
        user_answer = request.form.get(f"answer{mcq}")
        print(f"Question {mcq}: user answered {user_answer} (correct answer: {question.correct_option})")
        attempts.append(user_answer)

        if user_answer == question.correct_option:
            score += 1

    totalscore = (score / len(questions)) * 100
    user.scores = totalscore
    user.finish_time = datetime.now()

    db.session.commit()

    results = [(question.question, question.correct_option, attempts[i]) for i, question in enumerate(questions)]
    session['results'] = results

    return render_template('prequiz.html', score=score, user=current_user)

@app.route('/listnilai')
@login_required
def listnilai():
    user = User.query.all()
    return render_template('daftarnilai.html', user=user)

@app.route('/resetnilai/<int:user_id>')
@login_required
def reset_score(user_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    user = User.query.get_or_404(user_id)
    user.scores = None
    user.finish_time = None
    db.session.commit()
    flash('Nilai telah direset!', 'success')
    return redirect(url_for('listnilai'))

@app.route('/totxt')
@login_required
def save_to_txt():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    quiz_dir = r'C:\Users\USER\PycharmProjects\aksesso\quiz'
    quiz_num = len(os.listdir(quiz_dir)) + 1
    filename = os.path.join(quiz_dir, f'quiz{quiz_num}.txt')
    with open(filename, "w") as f:
        for user in User.query.all():
            f.write("{}, {}\n".format(user.name, user.scores))
        flash('Nilai tersimpan!', 'info')
        return redirect(url_for('listnilai'))

@app.route('/resetnilaiall')
@login_required
def reset_scores():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    users = User.query.all()
    for user in users:
        user.scores = None
        user.finish_time = None
    db.session.commit()
    flash('Semua nilai telah direset!', 'warning')
    return redirect(url_for('listnilai'))

@app.route('/deletesoalall')
@login_required
def clear_question():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    # delete all questions
    questions = Question.query.delete()
    # commit the changes to the database
    db.session.commit()
    flash('Semua soal telah dihapus!', 'warning')
    return redirect(url_for('listsoal'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    query = request.args.get('query')
    print(f"Query: {query}")
    results = Materi.query.filter(Materi.title.like(f'%{query}%')).all()
    return render_template('search.html', results=results)

@app.route('/forum')
@login_required
def forum():
    posts = Posting.query.all()
    return render_template('forum.html', posts=posts)

@app.route('/forumin')
@login_required
def adminforum():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    return render_template('menuforum.html')

@app.route('/postingadd', methods=['GET', 'POST'])
@login_required
def add_posting():
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    if request.method == 'POST':
        # Get the form data
        title = request.form['title']
        content = request.form['text']
        attachment = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                attachment = filename

        # Create a new posting object
        posting = Posting(title=title, content=content, file=attachment, author_id=current_user.id)

        # Add the posting to the database
        db.session.add(posting)
        db.session.commit()

        flash('Posting berhasil ditambahkan', 'success')
        return redirect(url_for('adminforum'))

    return render_template('addposting.html')

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Posting.query.get_or_404(post_id)

    # Ensure that only the author of the post can delete it
    if post.author_id != current_user.id:
        flash('Hanya guru yang bersangkutan yang bisa menghapus!', 'warning')
        return redirect(url_for('forum'))

    Comment.query.filter_by(post_id=post_id).delete()

    db.session.delete(post)
    db.session.commit()

    flash('Post telah dihapus!', 'success')
    return redirect(url_for('forum'))

@app.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Posting.query.get_or_404(post_id)

    # Ensure that only the author of the post can delete it
    if post.author_id != current_user.id:
        flash('Hanya guru yang bersangkutan yang bisa mengedit!', 'warning')
        return redirect(url_for('forum'))

    return render_template('editpost.html', post=post)

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Posting.query.get_or_404(post_id)
    content = request.form['content']
    author_id = current_user.id
    comment = Comment(content=content, author_id=author_id, post=post)
    db.session.add(comment)
    db.session.commit()
    flash('Komentar telah ditambahkan!', 'success')
    return redirect(url_for('forum'))

@app.route('/delete_comment/<int:comment_id>', methods=['GET', 'POST'])
def delete_comment(comment_id):
    if not current_user.is_authenticated or current_user.type != 'admin':
        abort(403)  # or any other error code you want to return
    comment = Comment.query.get_or_404(comment_id)
    # handle delete comment logic here
    db.session.delete(comment)
    db.session.commit()
    flash('Komentar telah dihapus!', 'warning')
    return redirect(url_for('forum'))

@app.route('/info')
@login_required
def info():
    return render_template('info.html')

@app.route('/infomin')
@login_required
def infomin():
    return render_template('info.html')

@app.route('/infodiskusi')
@login_required
def infodiskusi():
    return render_template('infodiskusi.html')

@app.route('/infomateri')
@login_required
def infomateri():
    return render_template('infomateri.html')

@app.route('/infoquiz')
@login_required
def infoquiz():
    return render_template('infoquiz.html')

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
