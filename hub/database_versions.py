"""Two SQLite slots; serialize requests from authentication to session saving.

Stop CLI writers during admin operations. Staging is bounded and memory-only,
except the transient file used to atomically replace the backup.
"""
import hashlib
import os
import sqlite3
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone as utc_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import HttpResponse
from django.utils import timezone

from .models import DatabaseVersion
from .models import ConfigurationGenerale, Secteur, Nouvelle, LienNouvelle, missing_text, social_host_errors

_lock = threading.RLock()


@contextmanager
def database_lock():
    with _lock:
        directory = Path(settings.DATABASE_BACKUP_DIR)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (directory / 'access.lock').open('a+b') as handle:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == 'nt':
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class DatabaseAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/admin/database/' and request.method == 'POST':
            try:
                length = int(request.META.get('CONTENT_LENGTH') or 0)
            except ValueError:
                return HttpResponse('Taille de requête invalide.', status=400)
            # Include a small allowance for multipart headers, reject before
            # Django can spool an oversized upload to the hosting filesystem.
            if length > settings.DATABASE_MAX_BYTES + 65536:
                response = HttpResponse('Base trop volumineuse : 20 Mio maximum.', status=413)
                response['Cache-Control'] = 'no-store'
                return response
        with database_lock():
            return self.get_response(request)


def open_readonly(path):
    return sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True)


def sha256_tree(root, exclude=()):
    """Empreinte SHA-256 de chaque fichier sous root, clé = chemin relatif POSIX."""
    root = Path(root)
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.name not in exclude}


def page_bytes(db):
    return db.execute('PRAGMA page_count').fetchone()[0] * db.execute('PRAGMA page_size').fetchone()[0]


def utc_now_text():
    """Horodatage UTC naïf, au format des colonnes DateTime de SQLite."""
    return timezone.now().astimezone(utc_timezone.utc).replace(tzinfo=None).isoformat(' ')


def version_row(db):
    return db.execute('SELECT uuid, created_at FROM hub_databaseversion WHERE id=1').fetchone()


def in_memory(fill):
    """Base SQLite en mémoire remplie par fill(db) ; fermée si le remplissage échoue."""
    db = sqlite3.connect(':memory:')
    try:
        fill(db)
        return db
    except Exception:
        db.close()
        raise


def backup_path():
    return Path(settings.DATABASE_BACKUP_DIR) / 'backup.sqlite3'


def version():
    return DatabaseVersion.objects.get_or_create(pk=1)[0]


def snapshot():
    if connection.in_atomic_block:
        raise ValidationError('Opération indisponible dans une transaction ouverte.')
    version()
    connection.ensure_connection()
    if page_bytes(connection.connection) > settings.DATABASE_MAX_BYTES:
        raise ValidationError('Base trop volumineuse pour la gestion en ligne ; utiliser la sauvegarde manuelle.')
    return in_memory(connection.connection.backup)


def schema(db):
    return dict(db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"))


def validate(db):
    db.execute('PRAGMA trusted_schema=OFF')
    if schema(db) != schema(connection.connection):
        raise ValidationError('Base incompatible : schéma différent. Migrer hors ligne avec cette version du code.')
    if page_bytes(db) > settings.DATABASE_MAX_BYTES:
        raise ValidationError('Base trop volumineuse.')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValidationError('Intégrité SQLite ou associations invalides.')
    if set(db.execute('SELECT app, name FROM django_migrations')) != set(connection.connection.execute('SELECT app, name FROM django_migrations')):
        raise ValidationError('Base incompatible : migrations différentes.')
    for model in (ConfigurationGenerale, Secteur, Nouvelle, LienNouvelle):
        fields = model._meta.concrete_fields
        names = [field.column for field in fields]
        for row in db.execute(f'SELECT {", ".join(names)} FROM {model._meta.db_table}'):
            obj = model(**dict(zip((field.attname for field in fields), row)))
            # FK integrity is checked against the candidate database by SQLite,
            # not against the currently active content via Django's validators.
            obj.clean_fields(exclude=[field.name for field in fields if field.is_relation])
            if model == ConfigurationGenerale:
                if any(not getattr(obj, name).strip() for name in model.required_texts()):
                    raise ValidationError('Présentation générale bilingue incomplète.')
                if social_host_errors(obj, model.profile_fields):
                    raise ValidationError('Lien de réseau social hors du domaine attendu.')
                if obj.image_accueil:
                    path = (Path(settings.MEDIA_ROOT).resolve() / obj.image_accueil.name).resolve()
                    if (Path(settings.MEDIA_ROOT).resolve() not in path.parents or not path.is_file()
                            or not obj.alt_accueil_fr.strip() or not obj.alt_accueil_en.strip()):
                        raise ValidationError("Image d'accueil manquante ou invalide. Restaurer les médias séparément avant de charger la base.")
            if model in (Nouvelle, Secteur) and obj.publie and not obj.premiere_publication:
                raise ValidationError('Horodatage de première publication manquant.')
            if model == Nouvelle and obj.publie and not obj.date_jalon:
                raise ValidationError('Date du jalon obligatoire pour une nouvelle publiée.')
            if model == Nouvelle and obj.link_errors():
                raise ValidationError('Vidéo ou lien de réseau social invalide.')
            if (model == Nouvelle and obj.publie and (obj.compte_rendu_fr.strip() or obj.compte_rendu_en.strip())
                    and missing_text(obj, ('compte_rendu_fr', 'compte_rendu_en'), '')):
                raise ValidationError('Compte rendu traduit obligatoire pour une nouvelle publiée.')
            if model == LienNouvelle and db.execute('SELECT publie FROM hub_nouvelle WHERE id=?', (obj.nouvelle_id,)).fetchone() == (1,):
                obj.validate_publication()
    for table, fields in [('hub_secteur', ('nom', 'slug', 'description', 'apprentissages', 'prochaine_etape')),
                          ('hub_nouvelle', ('titre', 'slug', 'corps'))]:
        names = [f'{field}_{lang}' for field in fields for lang in ('fr', 'en')]
        for row in db.execute(f"SELECT {', '.join(names)} FROM {table} WHERE publie=1"):
            if any(not isinstance(value, str) or not value.strip() for value in row):
                raise ValidationError('Base incompatible : publication bilingue incomplète.')
    root = Path(settings.MEDIA_ROOT).resolve()
    for name, fr, en, published in db.execute("SELECT image, alt_fr, alt_en, publie FROM hub_nouvelle WHERE image != ''"):
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file() or (published and (not fr.strip() or not en.strip())):
            raise ValidationError('Illustration manquante ou invalide. Restaurer les médias séparément avant de charger la base.')
    row = version_row(db)
    if row:
        UUID(row[0])
        datetime.fromisoformat(row[1])


def read_upload(upload):
    if not upload or upload.size > settings.DATABASE_MAX_BYTES:
        raise ValidationError('Choisir une base SQLite de 20 Mio maximum.')
    def fill(db):
        db.deserialize(upload.read())
        db.execute('PRAGMA trusted_schema=OFF')
        validate(db)
        db.execute('DELETE FROM hub_databaseversion')
        db.execute('INSERT INTO hub_databaseversion (id, uuid, created_at) VALUES (1, ?, ?)', (uuid4().hex, utc_now_text()))
        db.commit()
    return in_memory(fill)


def read_backup():
    path = backup_path()
    if not path.is_file():
        raise ValidationError('Aucune base backup disponible.')
    if path.stat().st_size > settings.DATABASE_MAX_BYTES:
        raise ValidationError('Backup trop volumineux.')
    def fill(db):
        with closing(open_readonly(path)) as source:
            source.backup(db)
        validate(db)
    return in_memory(fill)


def store_backup(db, new_version=False):
    path = backup_path()
    previous_images = set()
    if path.exists():
        try:
            with closing(open_readonly(path)) as old:
                previous_images = {row[0] for row in old.execute("SELECT image FROM hub_nouvelle WHERE image != ''")}
        except sqlite3.DatabaseError:
            pass  # Do not guess which images a corrupt backup used.
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    try:
        with closing(sqlite3.connect(temporary)) as target:
            db.backup(target)
            if new_version:
                target.execute('UPDATE hub_databaseversion SET uuid=?, created_at=? WHERE id=1', (uuid4().hex, utc_now_text()))
                target.commit()
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return previous_images


def cleanup_images(candidates):
    from .models import schedule_image_cleanup
    storage = Nouvelle._meta.get_field('image').storage
    root = Path(settings.MEDIA_ROOT).resolve()
    complete = True
    for name in candidates:
        try:
            if root in (root / name).resolve().parents:
                schedule_image_cleanup(name, storage)
        except OSError:
            complete = False
    return complete


def prepare_activation(incoming, current):
    # Keep current auth, OTP, consumed recovery codes and lockouts.
    incoming.execute('PRAGMA foreign_keys=OFF')
    for (table,) in current.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        if table.startswith(('auth_', 'otp_', 'two_factor_', 'axes_', 'django_admin_log', 'django_content_type')):
            incoming.execute(f'DELETE FROM "{table}"')
            rows = current.execute(f'SELECT * FROM "{table}"').fetchall()
            if rows:
                incoming.executemany(f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in rows[0])})', rows)
    incoming.execute('DELETE FROM django_session')
    incoming.commit()
    if incoming.execute('PRAGMA foreign_key_check').fetchall():
        raise ValidationError('Relations incompatibles après conservation des accès actuels.')


def activate(incoming):
    incoming.backup(connection.connection)


def backup_image_referenced(name):
    path = backup_path()
    if not path.exists():
        return False
    try:
        with closing(open_readonly(path)) as db:
            if db.execute('SELECT 1 FROM hub_nouvelle WHERE image=? LIMIT 1', (name,)).fetchone():
                return True
            try:
                return db.execute('SELECT 1 FROM hub_configurationgenerale WHERE image_accueil=? LIMIT 1',
                                  (name,)).fetchone() is not None
            except sqlite3.OperationalError:
                return False  # Backup antérieur à l'image d'accueil.
    except sqlite3.DatabaseError:
        return True
