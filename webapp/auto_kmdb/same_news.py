from itertools import product

newspapers = [
    {"name": "444", "id": 122},
    {"name": "444.hu", "id": 122},
    {"name": "24.hu", "id": 102},
    {"name": "24.", "id": 102},
    {"name": "index", "id": 1},
    {"name": "telex", "id": 251},
    {"name": "origo", "id": 13},
    {"name": "magyarnemzet", "id": 3},
    {"name": "g7", "id": 205},
    {"name": "népszava", "id": 20},
    {"name": "bank360", "id": 130},
    {"name": "Privátbankár", "id": 130},
    {"name": "hvg360", "id": 242},
    {"name": "hvg", "id": 5},
    {"name": "hvg.hu", "id": 5},
    {"name": "atv", "id": 54},
    {"name": "átlátszó", "id": 94},
    {"name": "atlatszo.hu", "id": 94},
    {"name": "válasz online", "id": 281},
    {"name": "valaszonline.hu", "id": 281},
    {"name": "szabadeurópa", "id": 250},
    {"name": "media1", "id": 232},
    {"name": "rtl", "id": 269},
    {"name": "rtl.hu", "id": 269},
    {"name": "lap", "id": None},
    {"name": "magyarhang", "id": 222},
    {"name": "portál", "id": None},
    {"name": "újság", "id": None},
    {"name": "hírportál", "id": None},
    {"name": "mfor", "id": 9},
    {"name": "mfor.hu", "id": 9},
    {"name": "mandiner", "id": 150},
    {"name": "pénzcentrum", "id": 55},
    {"name": "magyarnarancs", "id": 6},
    {"name": "világgazdaság", "id": 11},
    {"name": "vaol", "id": None},
    {"name": "vg.hu", "id": 11},
    {"name": "direkt36", "id": 155},
    {"name": "economx", "id": 25},
    {"name": "szabadpécs", "id": 209},
    {"name": "pestisrácok.hu", "id": 139},
    {"name": "propeller", "id": 146},
    {"name": "Népszabadság", "id": 2},
    {"name": "Magyar Hírlap", "id": 15},
    {"name": "Heti Válasz", "id": 12},
    {"name": "Figyelő", "id": 96},
    {"name": "Élet és Irodalom", "id": 19},
    {"name": "168 óra", "id": 22},
    {"name": "Hírszerző", "id": 23},
    {"name": "Nemzeti Sport", "id": 32},
    {"name": "Blikk", "id": 45},
    {"name": "ATV", "id": 54},
    {"name": "Portfolio", "id": 72},
    {"name": "Hetek", "id": 74},
    {"name": "Bors", "id": 87},
    {"name": "Szabad Föld", "id": 152},
    {"name": "Magyar Idők", "id": 161},
    {"name": "Forbes", "id": 184},
    {"name": "Qubit", "id": 210},
    {"name": "888", "id": 226},
    {"name": "Demokrata", "id": 243},
    {"name": "Partizán", "id": 260},
]


def clean(text):
    return text.lower().replace(".", "").replace(" ", "")


for n in newspapers:
    n["name"] = clean(n["name"])

news_names = [n["name"] for n in newspapers]

products = [
    clean("".join(e))
    for e in (
        list(
            product(
                [
                    "írja",
                    "írta",
                    "írta meg",
                    "tudta meg",
                    "számolt be",
                    "számolt be az esetről",
                    "mondta",
                    "számolt be",
                    "szúrta ki",
                    "ír hosszabban",
                    "derül ki",
                    "válaszolta",
                ],
                ["a", "az", ""],
                news_names,
            )
        )
        + list(
            product(
                ["elismerte"],
                ["a", "az", ""],
                news_names,
                ["-nak", "nak", "-nek", "nek"],
            )
        )
        + list(
            product(
                news_names, ["vette észre", "azt írja", "bukkant rá", "kiderítette"]
            )
        )
        + list(product(news_names, ["úgy tudja"]))
        + list(product(news_names, ["riportjából kiderül", "riportja szerint"]))
        + list(product(["ahogy"], ["a", "az", ""], news_names, ["írja"]))
        + list(
            product(["landolt"], ["a", "az", ""], news_names, ["postaládájában"])
        )  # landolt a Magyar Narancs postaládájában
        + list(
            product(
                [
                    "vette észre",
                    "tájékoztatott",
                    "tájékoztat",
                    "számol be",
                    "számolt be",
                    "szúrta ki",
                    "értesült",
                    "adta hírül",
                    "írja",
                    "írta",
                    "olvasható",
                    "fedezte fel",
                    "derítette ki",
                    "derült ki",
                    "közölte",
                    "róla",
                ],
                ["a", "az", ""],
                news_names,
            )
        )
        + list(
            product(
                ["a", "az", ""],
                news_names,
                [
                    "beszámolója szerint",
                    "összeállítása szerint",
                    "kérdésére",
                    "felhívja a figyelmet",
                    "kiderítette",
                    "vett észre",
                    "által ismertetett",
                    "kiperelte",
                    "szemlézte",
                    "jogi úton hozzájutott",
                    "szerint kiderült",
                    "cikke szerint",
                    "szúrt ki",
                    "írta",
                    "megkeresésére azt mondta",
                    "kiemelte",
                    "közöl",
                    "írása",
                    "szerint",
                    "állítása",
                    "azt állítja",
                    "szemléz",
                    "nézett",
                    "információi",
                    "meg is kérdezte",
                    "kérdezett",
                ],
            )
        )
        + list(
            product(
                ["derül ki", "derült ki"],
                ["a", "az"],
                news_names,
                ["beszámolójából", "cikkéből", "riportjából"],
            )
        )
        + list(product(["írta"], ["a", "az"], news_names))
        + list(product(["szemléző"], news_names, ["szerint"]))
        + list(product(["via"], news_names))
    )
]


def same_news(title, description, text):
    title = clean(title)
    description = clean(description)
    text = clean(text)
    if ":" in title and title.split(":")[0] in news_names:
        for n in newspapers:
            if n["name"] == title.split(":")[0]:
                return n['id']

    for sent in products:
        if sent in description or sent in text:
            for n in newspapers:
                if n["name"] in sent:
                    return n['id']

    if text.endswith(")"):
        for n in newspapers:
            if text[text.rfind("(") :].lower() == "(" + n["name"] + ")":
                return n['id']

    return None
