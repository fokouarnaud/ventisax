from urllib.parse import urlencode

from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.conf import settings

from .models import ConfigurationGenerale, Nouvelle, Secteur


LABELS = {
    "fr": dict(home="Accueil", about="Présentation", news="Nouvelles", contact="Contact", sectors="Secteurs",
               empty="Aucune nouvelle publiée pour le moment.", group="Groupe", all="Tous les secteurs",
               filter="Filtrer", previous="Précédent", next="Suivant", learning="Apprentissages",
               step="Prochaine étape", preparation="En préparation", active="Actif", site="Site du secteur",
               email="Contacter par e-mail", whatsapp="Contacter par WhatsApp", skip="Aller au contenu",
               unavailable="Le projet prépare ses contenus bilingues.", video="Vidéo", video_language="",
               instagram="Voir sur Instagram", facebook="Voir sur Facebook"),
    "en": dict(home="Home", about="About", news="News", contact="Contact", sectors="Sectors",
               empty="No published news yet.", group="Group", all="All sectors", filter="Filter",
               previous="Previous", next="Next", learning="Learning", step="Next step", preparation="In preparation",
               active="Active", site="Sector website", email="Contact by email", whatsapp="Contact on WhatsApp",
               skip="Skip to content", unavailable="The project is preparing its bilingual content.", video="Video",
               video_language="Video in French", instagram="View on Instagram", facebook="View on Facebook"),
}


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
                    youtube_id=obj.youtube_id, instagram_url=obj.instagram_url, facebook_url=obj.facebook_url)
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
    if selected:
        context["language_url"] += "?" + urlencode({"secteur": getattr(selected, "slug_" + other)})
        context["selected_slug"] = getattr(selected, "slug_" + lang)
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
            context[direction + "_url"] = "?" + urlencode(query)
    elif page == "home":
        context["nouvelles"] = [localized(n, lang, "detail") for n in news[:3]]
    config = ConfigurationGenerale.objects.first()
    with translation.override(lang):
        if not config:
            return render(request, "hub/unavailable.html", context, status=503)
        context.update(config=localized(config, lang), whatsapp_url=config.whatsapp_url, email_url=config.email_url)
        return render(request, "hub/page.html", context)


def not_found(request, exception):
    lang = "en" if request.path.startswith("/en/") else "fr"
    other = "fr" if lang == "en" else "en"
    return render(request, "hub/not_found.html", {"lang": lang, "labels": LABELS[lang], "language_url": f"/{other}/",
                  "preview": getattr(settings, "VENTISAX_PREVIEW", False)}, status=404)
