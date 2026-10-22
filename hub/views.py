from urllib.parse import urlencode

from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from .context_processors import THEME_COOKIE
from .models import SOCIAL_NAMES, ConfigurationGenerale, Nouvelle, Secteur


LABELS = {
    "fr": dict(home="Accueil", about="Présentation", news="Journal de formation", contact="Contact", sectors="Secteurs",
               empty="Aucune nouvelle publiée pour le moment.", group="Groupe", all="Tous les secteurs",
               filter="Filtrer", previous="Précédent", next="Suivant", learning="Apprentissages",
               step="Prochaine étape", preparation="En préparation", active="Actif", site="Site du secteur",
               email="Contacter par e-mail", whatsapp="Contacter par WhatsApp", skip="Aller au contenu",
               unavailable="Le projet prépare ses contenus bilingues.", video="Vidéo", video_language="", report="Compte rendu de manipulation", view="Affichage", view_list="Liste", view_grid="Grille",
               instagram="Voir sur Instagram", facebook="Voir sur Facebook", notify="Me prévenir à l’ouverture",
               notify_message="Bonjour Ventisax, prévenez-moi à l’ouverture de vos services de climatisation "
                              "et de froid. Mon quartier : ",
               academy_title="Réviser les cours",
               academy_text="Les cours et quiz de cette formation sont sur l'Académie Ventisax. L'accès se fait avec "
                            "un identifiant personnel : demandez-le-nous.",
               academy_open="Ouvrir l'Académie", academy_new_tab="(nouvel onglet)",
               academy_whatsapp="Demander un accès par WhatsApp", academy_email="Demander un accès par e-mail",
               academy_subject="Demande d'accès à l'Académie",
               academy_message="Bonjour Ventisax, je souhaite un identifiant pour l'Académie Ventisax. Mon nom : … "
                               "Pourquoi je m'y intéresse : …",
               follow="Suivre Ventisax", theme="Thème", theme_system="Thème : système",
               theme_light="Thème : clair", theme_dark="Thème : sombre"),
    "en": dict(home="Home", about="About", news="Training log", contact="Contact", sectors="Sectors",
               empty="No published news yet.", group="Group", all="All sectors", filter="Filter",
               previous="Previous", next="Next", learning="Learning", step="Next step", preparation="In preparation",
               active="Active", site="Sector website", email="Contact by email", whatsapp="Contact on WhatsApp",
               skip="Skip to content", report="Practical work report", view="Display", view_list="List", view_grid="Grid", unavailable="The project is preparing its bilingual content.", video="Video",
               video_language="Video in French", instagram="View on Instagram", facebook="View on Facebook",
               notify="Notify me at launch",
               notify_message="Hello Ventisax, please let me know when your air conditioning and refrigeration "
                              "services open. My neighbourhood: ",
               academy_title="Review the lessons",
               academy_text="The lessons and quizzes from this training are on the Ventisax Academy. Access requires "
                            "a personal login: ask us for one.",
               academy_open="Open the Academy", academy_new_tab="(new tab)",
               academy_whatsapp="Request access on WhatsApp", academy_email="Request access by email",
               academy_subject="Academy access request",
               academy_message="Hello Ventisax, I would like a login for the Ventisax Academy. My name: … "
                               "Why I'm interested: …",
               follow="Follow Ventisax", theme="Theme", theme_system="Theme: system",
               theme_light="Theme: light", theme_dark="Theme: dark"),
}


ACADEMY_PAGES = ("news", "detail", "contact")  # Renvoi vers l'Académie : journal, entrées et contact seulement.


def academy_links(config, labels):
    """Liens du bloc Académie, ou None sans adresse ; demandes d'accès sur les coordonnées administrées."""
    if not config.academie_url:
        return None
    return dict(url=config.academie_url, whatsapp_url=config.whatsapp_text_url(labels["academy_message"]),
                email_url=config.email_text_url(labels["academy_subject"], labels["academy_message"]))


VIEWS = ("liste", "grille")  # Affichages du journal ; l'URL porte le choix (partageable, sans JavaScript).


def report_rows(text):
    """Lignes « Rubrique : valeur » d'un compte rendu, en paires (rubrique, valeur) ; sinon rubrique vide."""
    rows = []
    for line in filter(None, (line.strip() for line in text.splitlines())):
        label, found, value = line.partition(":")
        rows.append((label.strip(), value.strip()) if found and len(label.strip()) <= 40 else ("", line))
    return rows


def localized(obj, lang, kind=None):
    data = {field.name[:-3]: getattr(obj, field.name) for field in obj._meta.fields if field.name.endswith("_" + lang)}
    if kind:
        data["url"] = reverse(kind, kwargs={"lang": lang, "slug": getattr(obj, "slug_" + lang)})
    if isinstance(obj, Secteur):
        data.update(site_url=obj.site_url, etat=LABELS[lang]["preparation" if obj.etat == "preparation" else "active"])
    if isinstance(obj, Nouvelle):
        data.update(date_jalon=obj.date_jalon, premiere_publication=obj.premiere_publication,
                    secteurs=[localized(s, lang, "sector") for s in obj.secteurs.filter(publie=True)],
                    liens=[{**localized(link, lang), "url": link.url} for link in obj.liens.all()],
                    youtube_id=obj.youtube_id, instagram_url=obj.instagram_url, facebook_url=obj.facebook_url,
                    rapport=report_rows(getattr(obj, "compte_rendu_" + lang)))
        if hasattr(obj, "image") and obj.image:
            data.update(image_url=obj.image.url, image_width=obj.image.width, image_height=obj.image.height)
    return data


def root(request):
    return redirect("/fr/")


def public(request, lang, page="home", slug=None):
    if lang not in LABELS:
        raise Http404
    other = "en" if lang == "fr" else "fr"
    sectors = Secteur.objects.filter(publie=True)
    news = Nouvelle.objects.filter(publie=True).prefetch_related("secteurs", "liens")
    context = dict(lang=lang, labels=LABELS[lang], page=page,
                   preview=getattr(settings, "VENTISAX_PREVIEW", False),
                   secteurs=[localized(s, lang, "sector") for s in sectors])
    selected = None
    obj = None
    vue = request.GET.get("vue") if page == "news" and request.GET.get("vue") in VIEWS else "liste"
    context["vue"] = vue
    if page == "sector":
        obj = get_object_or_404(sectors, **{"slug_" + lang: slug})
        context["secteur"] = localized(obj, lang, "sector")
        news = news.filter(secteurs=obj).distinct()
    elif page == "detail":
        obj = get_object_or_404(news, **{"slug_" + lang: slug})
        context["nouvelle"] = localized(obj, lang, "detail")
    elif page == "news" and request.GET.get("secteur"):
        selected = get_object_or_404(sectors, **{"slug_" + lang: request.GET["secteur"]})
        news = news.filter(secteurs=selected).distinct()
    route = {"home": "home", "about": "about", "contact": "contact", "news": "news", "sector": "sector", "detail": "detail"}[page]
    kwargs = {"lang": other}
    if obj:
        kwargs["slug"] = getattr(obj, "slug_" + other)
    context["language_url"] = reverse(route, kwargs=kwargs)
    language_query = {"secteur": getattr(selected, "slug_" + other)} if selected else {}
    if vue != "liste":
        language_query["vue"] = vue
    if language_query:
        context["language_url"] += "?" + urlencode(language_query)
    if selected:
        context["selected_slug"] = getattr(selected, "slug_" + lang)
    if page == "news":
        base = {"secteur": getattr(selected, "slug_" + lang)} if selected else {}
        context["view_urls"] = {option: "?" + urlencode({**base, **({"vue": option} if option != "liste" else {})})
                                for option in VIEWS}
    if page in ("news", "sector"):
        try:
            page_obj = Paginator(news, 10).page(request.GET.get("page", "1"))
        except InvalidPage as exc:
            raise Http404 from exc
        context["page_obj"] = page_obj
        context["nouvelles"] = [localized(n, lang, "detail") for n in page_obj]
        for direction, number in (("previous", page_obj.number - 1), ("next", page_obj.number + 1)):
            query = {"page": number}
            if selected:
                query["secteur"] = getattr(selected, "slug_" + lang)
            if vue != "liste":
                query["vue"] = vue
            context[direction + "_url"] = "?" + urlencode(query)
    elif page == "home":
        context["nouvelles"] = [localized(n, lang, "detail") for n in news[:3]]
    config = ConfigurationGenerale.objects.first()
    with translation.override(lang):
        if not config:
            return render(request, "hub/unavailable.html", context, status=503)
        labels = LABELS[lang]
        context.update(config=localized(config, lang), whatsapp_url=config.whatsapp_url, email_url=config.email_url,
                       notify_url=config.notify_url(labels["notify_message"], labels["notify"]),
                       hero_image=config.image_accueil or None,
                       academy=academy_links(config, labels) if page in ACADEMY_PAGES else None,
                       profils=[(SOCIAL_NAMES[f], getattr(config, f)) for f in config.profile_fields if getattr(config, f)])
        return render(request, "hub/page.html", context)


def not_found(request, exception):
    lang = "en" if request.path.startswith("/en/") else "fr"
    other = "fr" if lang == "en" else "en"
    return render(request, "hub/not_found.html", {"lang": lang, "labels": LABELS[lang], "language_url": f"/{other}/",
                  "preview": getattr(settings, "VENTISAX_PREVIEW", False)}, status=404)


def theme(request, choice):
    """Enregistre le thème choisi (cookie lisible par site.js, sans suivi) puis revient sur la page d'origine."""
    target = request.GET.get("next", "")
    if not (target.startswith("/") and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                                      require_https=request.is_secure())):
        target = "/"
    response = redirect(target)
    if choice == "system":
        response.delete_cookie(THEME_COOKIE, samesite="Lax")
    else:
        response.set_cookie(THEME_COOKIE, choice, max_age=365 * 24 * 3600, samesite="Lax", secure=request.is_secure())
    return response
