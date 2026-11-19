import datetime
import json
import pathlib

import feedparser
import requests

URL = "https://cyberveille.esante.gouv.fr/alertes-et-vulnerabilites/rss.xml"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
OUT = pathlib.Path("alertes_rss.jsonl")


def main():
    reponse = requests.get(URL, headers={"User-Agent": UA}, timeout=30)
    reponse.raise_for_status()
    flux = feedparser.parse(reponse.content)
    maintenant = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with OUT.open("w", encoding="utf-8") as f:
        for e in flux.entries:
            f.write(json.dumps({
                "id_alerte": e.get("id") or e.get("link"),
                "titre": e.get("title"),
                "lien": e.get("link"),
                "date_publication": e.get("published"),
                "resume": e.get("summary"),
                "ingere_le": maintenant,
            }, ensure_ascii=False) + "\n")

    print(f"{len(flux.entries)} alertes recuperees dans {OUT}")


if __name__ == "__main__":
    main()
