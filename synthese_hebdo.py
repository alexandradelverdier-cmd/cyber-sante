import datetime
import json
import os
import pathlib
import time

from google import genai

MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
ENTREE = pathlib.Path("alertes_semaine.json")
DOSSIER = pathlib.Path("syntheses")
NB_PRIORITES = 8

PROMPT = """
Tu rediges la note de veille cybersecurite hebdomadaire d'un etablissement de sante francais.
Lecteur : le directeur de l'etablissement, pas un informaticien.

Chiffres de la semaine (calcules, a reprendre tels quels) :
{stats}

Alertes prioritaires, triees par score decroissant (donnees officielles du CERT Sante) :
{alertes}

Redige en Markdown, en francais, 300 mots maximum :
1. "## En bref" : 2 phrases sur le niveau de menace de la semaine.
2. "## A traiter en priorite" : les 3 alertes les plus urgentes. Pour chacune, une ligne en gras
   avec l'editeur et le produit, puis : ce que risque l'etablissement en langage simple,
   pourquoi c'est urgent (exploitee, critique...), et l'action a demander a la DSI.
3. "## A surveiller" : les autres alertes de la liste, une ligne chacune.
4. "## Sources" : le lien de chaque alerte citee.

Regles :
- N'utilise QUE les informations fournies. N'invente aucun chiffre, produit ou consequence.
- Pas de jargon sans explication (VPN = acces a distance au reseau de l'hopital, etc.).
- Pas de tiret cadratin. Phrases courtes.
- Une vulnerabilite ne signifie pas une attaque reussie : ecris "pourrait permettre a un attaquant de...", jamais "compromis" ni "impacte".
- Ne rajoute aucun qualificatif absent des donnees (exemple interdit : "base de donnees hospitaliere").
- Titre de chaque alerte : "**Fabricant : produit**", sans repeter le nom du fabricant.
- Relis-toi : aucun mot repete, accords corrects.
- Ecris dans un francais impeccable, AVEC tous les accents (securite -> sécurité, periode -> période), meme si ces consignes en sont depourvues.
"""


def appeler(client, prompt):
    for essai in range(1, 6):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt).text
        except Exception as e:
            attente = 15 * essai
            print(f"  Erreur ({type(e).__name__}), nouvel essai dans {attente} s ({essai}/5)")
            time.sleep(attente)
    raise SystemExit("Echec apres 5 essais, relance plus tard.")


def main():
    alertes = json.loads(ENTREE.read_text(encoding="utf-8") or "[]")
    if not alertes:
        raise SystemExit("Aucune alerte cette semaine.")

    dates = sorted(a["date_publication"] for a in alertes)
    stats = "\n".join([
        f"- Période : du {dates[0]} au {dates[-1]}",
        f"- Alertes publiées : {len(alertes)}",
        f"- Failles critiques (CVSS >= 9) : {sum(a['gravite'] == 'critique' for a in alertes)}",
        f"- Failles déjà exploitées par des attaquants : {sum(a['exploitee'] == 'oui' for a in alertes)}",
        f"- Pertinence haute pour un hôpital : {sum(a['pertinence_hopital'] == 'haute' for a in alertes)}",
    ])
    champs = ["editeur", "titre", "cvss", "gravite", "exploitee", "poc_disponible",
              "correctif", "categorie_si", "justification", "score_priorite", "lien"]
    top = [{k: a[k] for k in champs} for a in alertes[:NB_PRIORITES]]

    print(f"Modele : {MODEL} | {len(alertes)} alertes, {len(top)} envoyees au modele")
    client = genai.Client(http_options={"timeout": 120_000})
    texte = appeler(client, PROMPT.format(stats=stats, alertes=json.dumps(top, ensure_ascii=False, indent=1)))

    DOSSIER.mkdir(exist_ok=True)
    fichier = DOSSIER / f"synthese_{dates[-1]}.md"
    entete = f"# Veille cyber sante : semaine du {dates[0]} au {dates[-1]}\n\n{stats}\n\n"
    fichier.write_text(entete + texte, encoding="utf-8")
    print(f"Termine : {fichier}")


if __name__ == "__main__":
    main()
