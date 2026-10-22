THEMES = ("system", "light", "dark")
THEME_COOKIE = "theme"


def theme(request):
    """Thème choisi par le visiteur (cookie de préférence, sans suivi) ; « system » suit le réglage de l'appareil."""
    choice = request.COOKIES.get(THEME_COOKIE)
    return {"theme": choice if choice in ("light", "dark") else "system", "themes": THEMES,
            "theme_next": request.get_full_path()}
