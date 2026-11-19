import json
import os
import pathlib
import time

from google import genai
from pypdf import PdfReader

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
PDF_DIR = pathlib.Path("pdf")
OUT = pathlib.Path("indicateurs_observatoire.jsonl")
PAGES_PAR_MORCEAU = 8

PROMPT = """
Voici le TEXTE des pages {debut} a {fin} du rapport annuel {annee} de l'Observatoire
des signalements d'incidents de securite des SI de sante (CERT Sante).
Chaque page commence par une ligne "=== PAGE n ===".
Extrais TOUS les chiffres, ceux de l'annee du rapport ET ceux de l'annee precedente
cites en comparaison. S'il n'y a aucun chiffre, renvoie [].

Renvoie uniquement une liste JSON. Chaque element a exactement ces champs :
- "annee" : l'annee a laquelle le chiffre se rapporte
- "indicateur" : nb_signalements, nb_structures, part_signalements, nb_rancongiciels,
  nb_alertes_envoyees, nb_interventions, ou autre nom court en snake_case
- "dimension" : total, origine, type_incident, type_structure, region, impact, mois, trimestre
- "modalite" : la valeur de la dimension (ex. "malveillante", "rancongiciel",
  "etablissement public", "Occitanie", "janvier"). Mets "total" si dimension = total
- "valeur" : un nombre (pas de texte, pas de %)
- "unite" : "nombre" ou "pourcentage"
- "page" : le numero n de la ligne "=== PAGE n ===" ou se trouve le chiffre
- "extrait" : la phrase d'ou vient le chiffre (20 mots max)

Regles :
- N'invente rien. Si un chiffre n'est pas clair, ne le mets pas.
- N'extrais pas une evolution en % (ex. "+29 %") : uniquement des valeurs.

TEXTE :
{texte}
"""


def annees_deja_faites():
    if not OUT.exists():
        return set()
    with OUT.open(encoding="utf-8") as f:
        return {json.loads(l)["annee_rapport"] for l in f if l.strip()}


def morceaux_de_texte(pdf):
    pages = PdfReader(pdf).pages
    for debut in range(0, len(pages), PAGES_PAR_MORCEAU):
        fin = min(debut + PAGES_PAR_MORCEAU, len(pages))
        texte = "\n".join(
            f"=== PAGE {i + 1} ===\n{pages[i].extract_text() or ''}"
            for i in range(debut, fin)
        )
        yield debut + 1, fin, texte


def extraire(client, prompt):
    for essai in range(1, 6):
        try:
            reponse = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return json.loads(reponse.text)
        except Exception as e:
            attente = 15 * essai
            print(f"    Erreur ({type(e).__name__}), nouvel essai dans {attente} s ({essai}/5)")
            time.sleep(attente)
    raise SystemExit("Echec apres 5 essais, relance plus tard : les annees faites seront sautees.")


def main():
    client = genai.Client(http_options={"timeout": 120_000})
    faites = annees_deja_faites()
    print(f"Modele : {MODEL}")
    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        annee_rapport = int(pdf.stem)
        if annee_rapport in faites:
            print(f"{annee_rapport} deja extrait, on passe.")
            continue
        print(f"Extraction {annee_rapport}...")
        lignes_rapport = []
        for debut, fin, texte in morceaux_de_texte(pdf):
            print(f"  pages {debut}-{fin}...")
            prompt = PROMPT.format(debut=debut, fin=fin, annee=annee_rapport, texte=texte)
            lignes = extraire(client, prompt)
            print(f"    {len(lignes)} chiffres")
            lignes_rapport.extend(lignes)
            time.sleep(3)
        with OUT.open("a", encoding="utf-8") as out:
            for ligne in lignes_rapport:
                ligne["annee_rapport"] = annee_rapport
                out.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        print(f"  Total {annee_rapport} : {len(lignes_rapport)} chiffres")
    print(f"Termine : {OUT}")


if __name__ == "__main__":
    main()
