"""
Main application file for the Groovoo service desk.

This Flask application implements a very small service‑desk style tool for
handling customer support tickets.  Each ticket can be created by an
authenticated user, assigned to a user and updated with comments and
attachments.  A simple dashboard shows counts of tickets by status and
provides filters and search functionality.  Tickets may also be exported
to CSV or Markdown formats.

The visual design is inspired by Groovoo's dark theme.  Most of the
colour palette lives in ``static/css/style.css``; the templates assume
the presence of this file for layout and styling.

Usage::

    export FLASK_APP=groovoo_service_desk/app.py
    flask run

The application will create a SQLite database in the package directory
on first run.  Uploaded files are stored under ``static/uploads``.  See
``config.py`` for more configuration options.
"""

import csv
import io
import os
from datetime import datetime

from flask import (Flask, abort, flash, redirect, render_template,
                   request, send_file, url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Create the Flask application and load configuration
app = Flask(__name__)
app.config.from_pyfile('config.py')

# Initialise the database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


###############################################################################
# Models
###############################################################################

class User(UserMixin, db.Model):
    """Model representing support staff users who log into the system."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tickets = db.relationship('Ticket', backref='assignee', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

    def set_password(self, password: str) -> None:
        """Hash and store the given plain‑text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plain‑text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover - repr used only for debugging
        return f'<User {self.username}>'


class Ticket(db.Model):
    """Model representing a support ticket."""

    id = db.Column(db.Integer, primary_key=True)
    
    # --- Novos campos da v1.2 ---
    title = db.Column(db.String(200), nullable=False, default='Ticket sem título')
    priority = db.Column(db.String(20), nullable=False, default='Low')
    tags = db.Column(db.String(200), nullable=True)
    organizer = db.Column(db.String(120), nullable=True)
    event = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)

    # --- Campos originais mantidos ---
    client_name = db.Column(db.String(120), nullable=False)
    client_contact = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    channel = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    
    # --- Status (preparado para as novas opções) ---
    status = db.Column(db.String(20), nullable=False, default='Aberto')
    
    # --- Campos de sistema que permanecem ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attachments = db.relationship('Attachment', backref='ticket', lazy=True)
    comments = db.relationship('Comment', backref='ticket', lazy=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f'<Ticket {self.id}: {self.title}>'


class Attachment(db.Model):
    """Model representing files attached to a ticket."""

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f'<Attachment {self.filename}>'


class Comment(db.Model):
    """Model representing comments added to a ticket."""

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f'<Comment {self.id} on Ticket {self.ticket_id}>'


###############################################################################
# Login manager configuration
###############################################################################

@login_manager.user_loader
def load_user(user_id: str):
    """Flask‑Login callback to load a user from the database by ID."""
    return User.query.get(int(user_id))


###############################################################################
# Helper functions
###############################################################################

def allowed_file(filename: str) -> bool:
    """Check whether a filename has an allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in app.config['ALLOWED_EXTENSIONS']


def save_attachments(files, ticket: Ticket) -> None:
    """
    Persist uploaded files to the server and create Attachment records.
    """
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
            file_path = os.path.join(upload_folder, unique_name)
            file.save(file_path)
            attachment = Attachment(filename=filename, filepath=unique_name, ticket=ticket)
            db.session.add(attachment)


###############################################################################
# Routes
###############################################################################

@app.route('/')
def home():
    """Redirect to the dashboard if authenticated, otherwise login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Allow a new user to create an account."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Usuário e senha são obrigatórios.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'error')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login realizado com sucesso.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Log the current user out and return to the login page."""
    logout_user()
    flash('Você saiu da aplicação.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Render the main dashboard.
    """
    query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    tag_filter = request.args.get('tag', '').strip() # NOVO: Obter o filtro de tag

    # Base query: Filtra tickets do utilizador que não estão arquivados
    tickets_query = Ticket.query.filter(
        Ticket.assignee_id == current_user.id,
        Ticket.status != 'Arquivado'
    )

    # Apply search across several fields
    if query:
        like_query = f"%{query}%"
        tickets_query = tickets_query.filter(
            db.or_(Ticket.title.ilike(like_query),
                   Ticket.client_name.ilike(like_query),
                   Ticket.description.ilike(like_query),
                   Ticket.tags.ilike(like_query))
        )

    # Apply category filter
    if category_filter:
        tickets_query = tickets_query.filter_by(category=category_filter)
        
    # NOVO: Apply tag filter
    if tag_filter:
        # Procura a tag dentro do campo de texto 'tags'
        tickets_query = tickets_query.filter(Ticket.tags.ilike(f"%{tag_filter}%"))

    # Execute query
    tickets = tickets_query.order_by(Ticket.created_at.desc()).all()

    # Gather unique categories for the filter dropdown
    categories = sorted({t.category for t in Ticket.query.with_entities(Ticket.category).filter_by(assignee_id=current_user.id)})
    
    # NOVO: Gather all unique tags for the filter dropdown
    all_tags = set()
    all_user_tickets = Ticket.query.filter_by(assignee_id=current_user.id).all()
    for ticket in all_user_tickets:
        if ticket.tags:
            # Separa as tags por vírgula e adiciona ao conjunto
            tags_list = [tag.strip() for tag in ticket.tags.split(',')]
            all_tags.update(tags_list)
    sorted_tags = sorted(list(all_tags))


    # Compute counters by status
    statuses = { 'Aberto': 0, 'Aguardando': 0, 'Resolvido': 0, 'Fechado': 0 }
    for t in Ticket.query.filter(Ticket.assignee_id == current_user.id, Ticket.status != 'Arquivado'):
        if t.status in statuses:
            statuses[t.status] += 1
    
    return render_template(
        'dashboard.html',
        tickets=tickets,
        categories=categories,
        all_tags=sorted_tags, # NOVO: Passa as tags para o template
        query=query,
        category_filter=category_filter,
        tag_filter=tag_filter, # NOVO: Passa o filtro atual para o template
        statuses=statuses
    )

@app.route('/tickets/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new support ticket."""
    if request.method == 'POST':
        # Extrair todos os dados do formulário (novos e antigos)
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        tags = request.form.get('tags')
        organizer = request.form.get('organizer')
        event = request.form.get('event')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        client_name = request.form.get('client_name')
        client_contact = request.form.get('client_contact')
        channel = request.form.get('channel')
        category = request.form.get('category')

        # Validar campos obrigatórios
        if not all([title, description, client_name, client_contact, channel, category]):
            flash('Os campos marcados com * são obrigatórios.', 'error')
            return render_template('create_ticket.html', form_data=request.form)

        # Criar a instância do ticket com todos os novos campos
        ticket = Ticket(
            title=title,
            description=description,
            priority=priority,
            tags=tags,
            organizer=organizer,
            event=event,
            email=email,
            telefone=telefone,
            client_name=client_name,
            client_contact=client_contact,
            channel=channel,
            category=category,
            assignee_id=current_user.id
        )
        db.session.add(ticket)
        db.session.flush()

        # Lidar com os anexos de ficheiros
        files = request.files.getlist('attachments')
        save_attachments(files, ticket)

        db.session.commit()
        flash('Ticket criado com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_ticket.html', form_data={})




@app.route('/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_detail(ticket_id: int):
    """
    Display a ticket with its details, comments and attachments.
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.assignee_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        content = request.form.get('comment')
        if content:
            comment = Comment(content=content, ticket=ticket, author=current_user)
            db.session.add(comment)

        new_status = request.form.get('status')
        if new_status and new_status in {'Aberto', 'Aguardando', 'Resolvido', 'Fechado', 'Arquivado'}:
            ticket.status = new_status

        files = request.files.getlist('attachments')
        save_attachments(files, ticket)

        db.session.commit()
        flash('Atualização aplicada.', 'success')
        return redirect(url_for('ticket_detail', ticket_id=ticket.id))

    return render_template('ticket_detail.html', ticket=ticket)


@app.route('/tickets/<int:ticket_id>/archive', methods=['POST'])
@login_required
def archive_ticket(ticket_id: int):
    """
    Muda o status de um ticket para 'Arquivado'.
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.assignee_id != current_user.id:
        abort(403)
    
    ticket.status = 'Arquivado'
    db.session.commit()
    
    flash(f'Ticket #{ticket.id} arquivado com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/tickets/archived')
@login_required
def archived_tickets():
    """
    Exibe uma lista de todos os tickets arquivados do utilizador.
    """
    tickets_arquivados = Ticket.query.filter_by(
        assignee_id=current_user.id,
        status='Arquivado'
    ).order_by(Ticket.created_at.desc()).all()
    
    return render_template('archived_tickets.html', tickets=tickets_arquivados)


@app.route('/tickets/<int:ticket_id>/reopen', methods=['POST'])
@login_required
def reopen_ticket(ticket_id: int):
    """
    Muda o status de um ticket de 'Arquivado' para 'Aberto'.
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.assignee_id != current_user.id:
        abort(403)
    
    ticket.status = 'Aberto'
    db.session.commit()
    
    flash(f'Ticket #{ticket.id} reaberto com sucesso!', 'success')
    return redirect(url_for('archived_tickets'))

@app.route('/tickets/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id: int):
    """
    Exibe um formulário para editar um ticket existente e guarda as alterações.
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.assignee_id != current_user.id:
        abort(403) # Apenas o dono do ticket pode editar

    if request.method == 'POST':
        # Recolher os dados atualizados do formulário
        ticket.title = request.form.get('title')
        ticket.description = request.form.get('description')
        ticket.priority = request.form.get('priority')
        ticket.tags = request.form.get('tags')
        ticket.organizer = request.form.get('organizer')
        ticket.event = request.form.get('event')
        ticket.email = request.form.get('email')
        ticket.telefone = request.form.get('telefone')
        ticket.client_name = request.form.get('client_name')
        ticket.client_contact = request.form.get('client_contact')
        ticket.channel = request.form.get('channel')
        ticket.category = request.form.get('category')
        
        db.session.commit()
        flash('Ticket atualizado com sucesso!', 'success')
        return redirect(url_for('ticket_detail', ticket_id=ticket.id))

    # Para o método GET, exibe o formulário pré-preenchido
    return render_template('edit_ticket.html', ticket=ticket)

@app.route('/export/csv')
@login_required
def export_csv():
    """
    Export open tickets to CSV.
    """
    tickets = Ticket.query.filter_by(assignee_id=current_user.id, status='Aberto').order_by(Ticket.created_at).all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Título', 'Cliente', 'Contato', 'Canal', 'Categoria', 'Descrição', 'Status', 'Criado em'])
    for t in tickets:
        writer.writerow([t.id, t.title, t.client_name, t.client_contact, t.channel, t.category, t.description, t.status, t.created_at.isoformat()])
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    filename = f'tickets_abertos_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.csv'
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/export/markdown')
@login_required
def export_markdown():
    """
    Export open tickets to Markdown.
    """
    tickets = Ticket.query.filter_by(assignee_id=current_user.id, status='Aberto').order_by(Ticket.created_at).all()
    md_lines = []
    md_lines.append('# Tickets Abertos')
    for t in tickets:
        md_lines.append(f'\n## Ticket {t.id} - {t.title}')
        md_lines.append(f'- **Cliente:** {t.client_name}')
        md_lines.append(f'- **Contato:** {t.client_contact}')
        md_lines.append(f'- **Canal:** {t.channel}')
        md_lines.append(f'- **Categoria:** {t.category}')
        md_lines.append(f'- **Descrição:** {t.description}')
        md_lines.append(f'- **Criado em:** {t.created_at.isoformat()}')
        md_lines.append(f'- **Status:** {t.status}')
    md_content = '\n'.join(md_lines)
    output = io.BytesIO(md_content.encode('utf-8'))
    filename = f'tickets_abertos_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.md'
    return send_file(
        output,
        mimetype='text/markdown',
        as_attachment=True,
        download_name=filename
    )


###############################################################################
# Error handlers
###############################################################################

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


###############################################################################
# Main entry point
###############################################################################

if __name__ == '__main__':  # pragma: no cover
    with app.app_context():
        db.create_all()
    app.run(debug=True)