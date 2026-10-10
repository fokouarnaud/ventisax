"""Contenus du brief validé ; pas de coordonnées ni de réalisation inventées."""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hub.models import ConfigurationGenerale, Secteur


class Command(BaseCommand):
    help = "Initialiser le brief bilingue sans remplacer les contenus existants."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--whatsapp", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            if not ConfigurationGenerale.objects.exists():
                ConfigurationGenerale.objects.create(
                    identite_fr="Ventisax — projet de groupe en développement",
                    identite_en="Ventisax — a group project in development",
                    resume_fr="Nous préparons un futur groupe à Yaoundé et ses environs, autour de la climatisation, du froid et du matériel électronique.",
                    resume_en="We are preparing a future group in Yaoundé and the surrounding area, focused on air conditioning, refrigeration and electronic equipment.",
                    presentation_fr="Ventisax est un projet informel en formation. Notre ambition est de constituer une future SARL. Aucune prestation ni vente n’est actuellement proposée sur ce site.",
                    presentation_en="Ventisax is an informal project in training. Our ambition is to establish a future limited liability company. No services or sales are currently offered on this website.",
                    parcours_fr="Le parcours commence par la formation et la préparation des deux secteurs. Les étapes réelles seront partagées ici au fil de la progression.",
                    parcours_en="Our journey begins with training and preparation of the two sectors. Actual milestones will be shared here as the project progresses.",
                    implantation_fr="Yaoundé et ses environs, Cameroun",
                    implantation_en="Yaoundé and the surrounding area, Cameroon",
                    email=options["email"], whatsapp=options["whatsapp"],
                )
            sectors = [
                ("climatisation-froid", "air-conditioning-refrigeration", "Climatisation et froid", "Air conditioning and refrigeration", "Préparer une activité dans la climatisation et le froid.", "Preparing an activity in air conditioning and refrigeration."),
                ("materiel-electronique", "electronic-equipment", "Matériel électronique", "Electronic equipment", "Préparer une activité autour du matériel électronique.", "Preparing an activity focused on electronic equipment."),
            ]
            for order, (slug_fr, slug_en, name_fr, name_en, desc_fr, desc_en) in enumerate(sectors, 1):
                Secteur.objects.get_or_create(slug_fr=slug_fr, defaults=dict(
                    slug_en=slug_en, nom_fr=name_fr, nom_en=name_en,
                    description_fr=desc_fr, description_en=desc_en,
                    apprentissages_fr="Formation en préparation ; les apprentissages acquis seront documentés au fil du parcours.",
                    apprentissages_en="Training is being prepared; acquired skills will be documented throughout the journey.",
                    prochaine_etape_fr="Commencer la formation et documenter les premières étapes réelles.",
                    prochaine_etape_en="Begin training and document the first actual milestones.",
                    ordre=order, etat="preparation", publie=True,
                ))
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Brief initialisé ; contenus existants conservés. Aucun jalon créé."))
