from flask import Blueprint, render_template, request, redirect, url_for, session, send_from_directory
from models import db, Review, Like, Comment, User
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

main = Blueprint('main', __name__)
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'hwp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None

# ── 홈 ──────────────────────────────────────────────
@main.route('/')
def index():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    user = current_user()
    liked_ids = set()
    if user:
        liked_ids = {l.review_id for l in Like.query.filter_by(user_id=user.id).all()}
    return render_template('index.html', reviews=reviews, user=user, liked_ids=liked_ids)

# ── 리뷰 상세 ────────────────────────────────────────
@main.route('/review/<int:review_id>')
def review_detail(review_id):
    review = Review.query.get_or_404(review_id)
    user = current_user()
    liked = False
    if user:
        liked = Like.query.filter_by(review_id=review_id, user_id=user.id).first() is not None
    return render_template('review.html', review=review, user=user, liked=liked)

# ── 리뷰 작성 ────────────────────────────────────────
@main.route('/write', methods=['GET', 'POST'])
def write():
    user = current_user()
    if not user:
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        _save_review(request, review=None, user=user)
        return redirect(url_for('main.index'))
    return render_template('write.html', review=None)

# ── 리뷰 수정 ────────────────────────────────────────
@main.route('/edit/<int:review_id>', methods=['GET', 'POST'])
def edit(review_id):
    user = current_user()
    review = Review.query.get_or_404(review_id)
    if not user or review.user_id != user.id:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        _save_review(request, review=review, user=user)
        return redirect(url_for('main.review_detail', review_id=review.id))
    return render_template('write.html', review=review)

# ── 리뷰 삭제 ────────────────────────────────────────
@main.route('/delete/<int:review_id>', methods=['POST'])
def delete(review_id):
    user = current_user()
    review = Review.query.get_or_404(review_id)
    if user and review.user_id == user.id:
        db.session.delete(review)
        db.session.commit()
    return redirect(url_for('main.index'))

# ── 공감 토글 ────────────────────────────────────────
@main.route('/like/<int:review_id>', methods=['POST'])
def like(review_id):
    user = current_user()
    if not user:
        return redirect(url_for('main.login'))
    existing = Like.query.filter_by(review_id=review_id, user_id=user.id).first()
    if existing:
        db.session.delete(existing)   # 이미 눌렀으면 취소
    else:
        db.session.add(Like(review_id=review_id, user_id=user.id))
    db.session.commit()
    # 상세 페이지에서 왔으면 상세로, 홈에서 왔으면 홈으로
    next_url = request.form.get('next', url_for('main.index'))
    return redirect(next_url)

# ── 댓글 작성 ────────────────────────────────────────
@main.route('/comment/<int:review_id>', methods=['POST'])
def comment(review_id):
    user = current_user()
    if not user:
        return redirect(url_for('main.login'))
    content = request.form.get('content', '').strip()
    if content:
        db.session.add(Comment(review_id=review_id, user_id=user.id, content=content))
        db.session.commit()
    return redirect(url_for('main.review_detail', review_id=review_id))

# ── 검색 ─────────────────────────────────────────────
from flask import send_from_directory

@main.route('/download/<filename>')
def download(filename):
    folder = os.path.join(os.getcwd(), 'uploads')
    return send_from_directory(folder, filename, as_attachment=True)
@main.route('/search')
def search():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        results = Review.query.filter(
            (Review.title.contains(query)) | (Review.author.contains(query))
        ).order_by(Review.created_at.desc()).all()
    return render_template('search.html', results=results, query=query, user=current_user())

# ── 회원가입 ─────────────────────────────────────────
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        nickname = request.form.get('nickname', '').strip()
        password = request.form.get('password', '')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='이미 사용 중인 아이디예요.')
        if User.query.filter_by(nickname=nickname).first():
            return render_template('register.html', error='이미 사용 중인 닉네임이에요.')
        user = User(username=username, nickname=nickname,
                    password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('main.index'))
    return render_template('register.html', error=None)

# ── 로그인 ───────────────────────────────────────────
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return render_template('login.html', error='아이디 또는 비밀번호가 틀렸어요.')
        session['user_id'] = user.id
        return redirect(url_for('main.index'))
    return render_template('login.html', error=None)

# ── 로그아웃 ─────────────────────────────────────────
@main.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))

# ── 헬퍼 ─────────────────────────────────────────────
def _save_review(req, review, user):
    title   = req.form.get('title')
    author  = req.form.get('author')
    genre   = req.form.get('genre')
    diff    = int(req.form.get('star_difficulty', 1))
    worth   = int(req.form.get('star_worth', 1))
    content = req.form.get('content', '')
    file    = req.files.get('attachment')

    filename = review.filename if review else None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(folder, exist_ok=True)
        file.save(os.path.join(folder, filename))

    if review:
        review.title = title; review.author = author; review.genre = genre
        review.star_difficulty = diff; review.star_worth = worth
        review.content = content; review.filename = filename
    else:
        db.session.add(Review(user_id=user.id, title=title, author=author, genre=genre,
                              star_difficulty=diff, star_worth=worth,
                              content=content, filename=filename))
    db.session.commit()