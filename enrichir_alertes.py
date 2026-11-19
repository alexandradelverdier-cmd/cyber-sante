import datetime
import html
import json
import pathlib
import re
import time

import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
ENTREE = pathlib.Path("a_enrichir.json")
SORTIE = pathlib.Path("details_alertes.jsonl")


def chercher(motif, texte):
    m = re.search(motif, texte)
    return m.group(1) if m else None


def lire_page(url):
    brut = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
    texte = html.unescape(re.sub(r"<[^>]+>", " ", brut))
    texte = re.sub(r"\s+", " ", texte)
    cvss = chercher(r"Score CVSS v[\d.]+ : ([\d.]+)", texte)
    return {
        "cvss": float(cvss) if cvss else None,
        "exploitee": chercher(r"activement exploit\S+ : (Oui|Non)", texte),
        "correctif": chercher(r"Un correctif existe : (Oui|Non)", texte),
        "contournement": chercher(r"mesure de contournement existe : (Oui|Non)", texte),
        "cwe": chercher(r"(CWE-\d+)", texte),
        "vecteur": chercher(r"Vecteur d'attaque : (\S+)", texte),
        "privileges": chercher(r"Privil\S+ n\S+ pour r\S+ l'attaque : (\S+)", texte),
        "poc_disponible": "preuve de concept est disponible" in texte.lower(),
    }


def main():
    alertes = json.loads(ENTREE.read_text(encoding="utf-8") or "[]")
    print(f"{len(alertes)} alertes a enrichir")
    maintenant = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with SORTIE.open("w", encoding="utf-8") as out:
        for i, a in enumerate(alertes, 1):
            try:
                details = lire_page(a["lien"])
            except Exception as e:
                print(f"  {a['id_alerte']} : erreur {type(e).__name__}, on passe")
                continue
            details.update(id_alerte=a["id_alerte"], recupere_le=maintenant)
            out.write(json.dumps(details, ensure_ascii=False) + "\n")
            if i % 10 == 0:
                print(f"  {i}/{len(alertes)}")
            time.sleep(1)
    print(f"Termine : {SORTIE}")


if __name__ == "__main__":
    main()
