import sqlite3
import smtplib
from contextlib import closing
from datetime import datetime, timezone as utc_timezone
from uuid import UUID

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from unfold.widgets import UnfoldAdminEmailInputWidget, UnfoldBooleanWidget

from . import database_versions as versions


class DatabaseForm(forms.Form):
    action = forms.ChoiceField(choices=[(a, a) for a in ('save', 'swap', 'upload_backup', 'upload_current', 'email')], widget=forms.HiddenInput)
    database = forms.FileField(label='Fichier SQLite compatible (20 Mio maximum)', required=False,
        widget=forms.FileInput(attrs={'style': 'width:100%;min-width:0;max-width:100%'}))
    email = forms.EmailField(label='Destinataire', widget=UnfoldAdminEmailInputWidget, required=False, help_text='Vide : adresse de votre compte administrateur.')
    confirm = forms.BooleanField(label='Je confirme le remplacement et ai téléchargé une copie hors hébergement.', widget=UnfoldBooleanWidget, required=False)

    def clean(self):
        data = super().clean()
        if data.get('action') in ('swap', 'upload_backup', 'upload_current', 'save') and not data.get('confirm'):
            if data.get('action') != 'save' or versions.backup_path().exists():
                raise ValidationError('Confirmer le remplacement de la base concernée.')
        if data.get('action', '').startswith('upload') and not data.get('database'):
            self.add_error('database', 'Choisir un fichier SQLite.')
        return data


def utc_stamp():
    return timezone.now().astimezone(utc_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def warn_unclean(request, obsolete, prefix):
    if not versions.cleanup_images(obsolete):
        messages.warning(request, f'{prefix} ; certains anciens médias demandent un nettoyage manuel.')


def database_view(request):
    from .admin import site
    if not request.user.is_superuser:
        return HttpResponseForbidden('Gestion des bases réservée au superadministrateur.')
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    form = DatabaseForm(request.POST or None, request.FILES or None)
    if request.method == 'GET' and 'download' in request.GET:
        try:
            slot = request.GET['download']
            if slot not in ('current', 'backup'):
                raise ValidationError('Emplacement inconnu.')
            with closing(versions.snapshot() if slot == 'current' else versions.read_backup()) as db:
                ident, created = versions.version_row(db)
                stamp = utc_stamp()
                response = HttpResponse(db.serialize(), content_type='application/vnd.sqlite3')
                response['Content-Disposition'] = f'attachment; filename="ventisax-{slot}-{stamp}-UTC-{UUID(ident)}.sqlite3"'
                return response
        except (ValidationError, sqlite3.Error, OSError, ValueError) as exc:
            form.add_error(None, ValidationError(exc.messages) if isinstance(exc, ValidationError) else 'Téléchargement impossible.')
    if request.method == 'POST' and form.is_valid():
        try:
            action = form.cleaned_data['action']
            with closing(versions.snapshot()) as current:
                if action == 'save':
                    warn_unclean(request, versions.store_backup(current, new_version=True), 'Backup enregistré')
                elif action in ('swap', 'upload_current', 'upload_backup'):
                    incoming = versions.read_backup() if action == 'swap' else versions.read_upload(form.cleaned_data['database'])
                    with closing(incoming):
                        if action == 'upload_backup':
                            warn_unclean(request, versions.store_backup(incoming), 'Backup enregistré')
                        else:
                            versions.prepare_activation(incoming, current)
                            obsolete = versions.store_backup(current)
                            versions.activate(incoming)
                            logout(request)
                            warn_unclean(request, obsolete, 'Base activée')
                            messages.success(request, 'Base activée ; ancienne courante conservée en backup. Reconnectez-vous avec vos accès actuels.')
                            return redirect(settings.LOGIN_URL)
                elif action == 'email':
                    recipient = form.cleaned_data['email'] or request.user.email
                    forms.EmailField().clean(recipient)
                    payload = current.serialize()
                    if len(payload) > settings.DATABASE_EMAIL_MAX_BYTES:
                        raise ValidationError('Base trop volumineuse pour l’e-mail (10 Mio maximum). Utiliser la sauvegarde manuelle.')
                    stamp = utc_stamp()
                    ident = versions.version().uuid
                    message = EmailMessage(f'Ventisax — base courante — {stamp} UTC',
                        f'Base courante {ident}, exportée le {stamp} UTC.\nCette pièce jointe contient des données privées. Conserver en lieu sûr.\nLes médias doivent être sauvegardés séparément.',
                        settings.DEFAULT_FROM_EMAIL, [recipient])
                    message.attach(f'ventisax-{stamp}-UTC-{ident}.sqlite3', payload, 'application/vnd.sqlite3')
                    if message.send() != 1:
                        raise ValidationError('Le serveur e-mail n’a pas accepté l’envoi.')
            messages.success(request, 'Base courante envoyée par e-mail.' if action == 'email' else 'Base backup enregistrée.')
            return redirect('admin:database_versions')
        except (ValidationError, sqlite3.Error, OSError, ValueError, smtplib.SMTPException) as exc:
            form.add_error(None, ValidationError(exc.messages) if isinstance(exc, ValidationError) else 'Opération impossible. Vérifiez le fichier, l’espace disponible ou la configuration SMTP.')
    current = versions.version()
    backup = None
    path = versions.backup_path()
    if path.exists():
        try:
            with closing(versions.open_readonly(path)) as db:
                ident, created = versions.version_row(db)
                backup = {'uuid': UUID(ident), 'created_at': datetime.fromisoformat(created).replace(tzinfo=utc_timezone.utc), 'size': path.stat().st_size}
        except (sqlite3.Error, ValueError, TypeError):
            form.add_error(None, 'Backup illisible : charger une base compatible pour le remplacer.')
    return TemplateResponse(request, 'admin/database_versions.html', {
        **site.each_context(request), 'title': 'Versions de base de données', 'form': form,
        'current': current, 'backup': backup, 'local_zone': settings.TIME_ZONE,
    })
