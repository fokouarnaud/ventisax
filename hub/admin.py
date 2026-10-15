from django.contrib import admin, messages
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url
from django.views.decorators.cache import never_cache
from functools import wraps
from django.core.exceptions import ValidationError
from django.db import models
from two_factor.admin import AdminSiteOTPRequiredMixin
from unfold.sites import UnfoldAdminSite
from unfold.admin import ModelAdmin, TabularInline

from .models import ConfigurationGenerale, Secteur, Nouvelle, NouvelleSecteur, LienNouvelle


class SecureAdminSite(AdminSiteOTPRequiredMixin, UnfoldAdminSite):
    site_header = "Administration Ventisax"
    site_title = "Ventisax"

    def get_urls(self):
        from django.urls import path
        from .database_admin import database_view
        return [path("database/", self.admin_view(database_view), name="database_versions")] + super().get_urls()

    def admin_view(self, view, cacheable=False):
        protected = super().admin_view(view, cacheable=cacheable)

        @wraps(view)
        @never_cache
        def require_otp(request, *args, **kwargs):
            if not self.has_permission(request):
                return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))
            return protected(request, *args, **kwargs)
        return require_otp


site = SecureAdminSite(name="admin")


class PublicationAdmin(ModelAdmin):
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}
    readonly_fields = ("uuid", "publie", "premiere_publication", "cree_le", "modifie_le")
    actions = ("publish_selected", "unpublish_selected")
    list_filter = ("publie",)

    @admin.action(description="Publier les contenus complets en français et anglais")
    def publish_selected(self, request, queryset):
        for obj in queryset:
            try:
                obj.publish()
            except ValidationError as exc:
                self.message_user(request, f"{obj} : {exc}", level=messages.ERROR)
            else:
                self.message_user(request, f"{obj} publié.", level=messages.SUCCESS)

    @admin.action(description="Dépublier sans supprimer les données")
    def unpublish_selected(self, request, queryset):
        for obj in queryset:
            obj.unpublish()
        self.message_user(request, "Contenus dépubliés.", level=messages.SUCCESS)

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return (*fields, "slug_fr", "slug_en") if obj and obj.premiere_publication else fields


@admin.register(Secteur, site=site)
class SecteurAdmin(PublicationAdmin):
    list_display = ("nom_fr", "etat", "publie", "ordre")
    search_fields = ("nom_fr", "nom_en")


class LienInline(TabularInline):
    model = LienNouvelle
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}
    extra = 0
    readonly_fields = ("uuid",)


class SecteurInline(TabularInline):
    model = NouvelleSecteur
    extra = 0


@admin.register(Nouvelle, site=site)
class NouvelleAdmin(PublicationAdmin):
    list_display = ("titre_fr", "date_jalon", "publie", "premiere_publication")
    search_fields = ("titre_fr", "titre_en")
    inlines = (LienInline, SecteurInline)


@admin.register(ConfigurationGenerale, site=site)
class ConfigurationAdmin(ModelAdmin):
    readonly_fields = ("uuid", "modifie_le")
    fieldsets = (
        ("Textes", {"fields": ("identite_fr", "identite_en", "resume_fr", "resume_en", "presentation_fr",
                               "presentation_en", "parcours_fr", "parcours_en", "implantation_fr", "implantation_en")}),
        ("Coordonnées", {"fields": ("email", "whatsapp")}),
        ("Réseaux", {"fields": ("youtube_channel_url", "facebook_url", "tiktok_url", "instagram_url"),
                     "description": "Liens facultatifs vers les profils publics, affichés en liens simples."}),
        ("Suivi", {"fields": ("uuid", "modifie_le")}),
    )

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not ConfigurationGenerale.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
