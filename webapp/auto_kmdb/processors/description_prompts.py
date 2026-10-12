"""
Prompts for generating the descriptions of KMDB entities. The common rules are in the system
instruction, the task and the context given from the KMDB differ by entity type. Models that can
search the web are asked to find sources beyond the given KMDB articles.
"""

from typing import Optional

SYSTEM_INSTRUCTION = """A K-Monitor közpénz- és korrupciós sajtóadatbázisának (K-Monitor Adatbázis, https://adatbazis.k-monitor.hu) szerkesztője vagy. Az adatbázis a magyar sajtó korrupcióról, közbeszerzésekről, közpénzek felhasználásáról és a közélet átláthatóságáról szóló cikkeit gyűjti, és a cikkeket személyekkel, intézményekkel, aktákkal (ügyekkel) és sajtótermékekkel címkézi. A feladatod ezeknek a címkéknek a rövid leírását megírni vagy frissíteni.

Szabályok:
- A szöveg legyen objektív, tényszerű, lényegretörő és időtálló! Ne használj az írás időpontjához kötött kifejezéseket (pl. „jelenleg”, „nemrég”, „idén”, „tavaly”), helyettük konkrét évszámokat, dátumokat írj.
- Az egyes tényállítások mögé keress forrást, és rakd a mondat után [url] formátumban, pl.: „2019-ben nevezték ki a hivatal élére. [https://telex.hu/...]” Több forrás esetén mindegyik URL-t külön szögletes zárójelbe tedd, vesszővel ne fűzd össze őket, pl.: „... [https://hvg.hu/...] [https://444.hu/...]”
{sources_rule}
- Csak olyat írj, amit a források alátámasztanak. Ha valamire nincs forrásod, inkább hagyd ki.
- Ne minősíts, és ne használj értékítéletet. A vádakat, gyanúkat és eljárásokat pontosan, a forrásnak megfelelően írd le (ki állította, folyik-e eljárás, jogerős-e az ítélet), és tartsd tiszteletben az ártatlanság vélelmét.
- Magyarul, markdown formátumban írj, folyó szövegben: a bekezdéseket üres sor válassza el, kiemelést és felsorolást csak indokolt esetben használj, címsort ne.
- Csak a leírás szövegét add vissza, bevezető vagy záró megjegyzés nélkül."""

SEARCH_SOURCES_RULE = """- Forrásnak alapvetően sajtóhíreket használj! A megadott cikkek a K-Monitor Adatbázis legutóbbi cikkei a címkéről, a korábbi és a további információkhoz webes kereséssel keress forrást. Forrásként a megtalált oldal pontos, eredeti URL-jét add meg, URL-t ne találj ki és ne rakj össze. A K-Monitor Adatbázist (adatbazis.k-monitor.hu) ne add meg forrásként, a jelenlegi leírás állításaihoz is eredeti forrást keress."""

GIVEN_SOURCES_RULE = """- Forrásnak a megadott sajtóhíreket használd! Csak a megadott cikkek URL-jeit hivatkozd, pontosan úgy, ahogy a listában szerepelnek, URL-t ne találj ki. A K-Monitor Adatbázist (adatbazis.k-monitor.hu) ne add meg forrásként."""

# Entity types whose most frequent co-tagged entities are listed in the prompt.
RELATED_TYPES: dict[str, list[str]] = {
    "person": ["file", "institution"],
    "institution": ["file", "person"],
    "file": ["person", "institution"],
    "newspaper": [],
}

RELATED_LABELS: dict[str, str] = {
    "file": "akták (ügyek)",
    "person": "személyek",
    "institution": "intézmények",
}

TASKS: dict[str, str] = {
    "person": """Írj egy legfeljebb 2 bekezdéses életrajzi leírást a következő személyről: {name}!
Legyen objektív, időtálló. Az első mondatból derüljön ki, ki ő (pl. foglalkozása, legfontosabb tisztségei). Tartalmazza a K-Monitor Adatbázisban a neve mellett gyűjtött főbb ügyeket{kmdb_ref}!
Az egyes információk mögött [url] formában tartalmazza a forrást is!""",
    "institution": """Írj egy legfeljebb 2 bekezdéses leírást a következő intézményről: {name}!
Legyen objektív, időtálló. Az első mondatból derüljön ki, milyen intézményről van szó (pl. típusa, feladata, tulajdonosa vagy fenntartója). Tartalmazza a K-Monitor Adatbázisban hozzá kapcsolódó főbb ügyeket{kmdb_ref}!
Az egyes információk mögött [url] formában tartalmazza a forrást is!""",
    "file": """Írj egy legfeljebb 2 bekezdéses összefoglalót a következő ügyről (a K-Monitor Adatbázis egyik aktájáról): {name}{kmdb_ref}!
Legyen lényegretörő, objektív és időtálló. Foglald össze, miről szól az ügy, kik az érintett főbb szereplők és intézmények, és időrendben mik voltak a legfontosabb fejlemények (pl. nyilvánosságra kerülés, feljelentés, nyomozás, vádemelés, ítélet) a legutóbbi ismert állapotig.
Az állításoknál [url] formában tartalmazza a forrást!""",
    "newspaper": """Írj egy bekezdésnyi rövid leírást a(z) {name} sajtótermékhez{kmdb_ref}!
Legyen tényszerű, tárgyilagos és időtálló, kb. mint a Wikipédiában: milyen típusú médium (pl. hírportál, napilap, hetilap, televízió), mikor alapították, ki a kiadója és a tulajdonosa, és ha volt, melyek voltak a fontosabb tulajdonosváltások.
Az egyes információk mögött [url] formában tartalmazza a forrást is!""",
}

UPDATE_INSTRUCTION = """A címke jelenlegi leírása:
\"\"\"
{description}
\"\"\"

Írj hozzá frissítést! A jelenlegi leírást ne rövidítsd: a helytálló részeit lehetőleg változatlanul tartsd meg a forrásaikkal együtt, csak az elavult vagy téves állításokat javítsd, és egészítsd ki az újabb fejleményekkel a megadott cikkek{search_sources} alapján. Frissítésnél a bekezdések számára vonatkozó korlát nem érvényes. A leíráshoz nem tartozó részeket (pl. támogatási felhívás, a fotó forrása) hagyd el. Az új és a javított állítások mögé tegyél forrást. A teljes, frissített leírást add vissza."""

RECENT_INSTRUCTION = "A legutóbbi megadott KMDB-cikk {date}-i, webes kereséssel nézz utána az azóta történt fejleményeknek is."

ARTICLES_HEADER: dict[str, str] = {
    "person": "A K-Monitor Adatbázisban a személyhez kapcsolt cikkek",
    "institution": "A K-Monitor Adatbázisban az intézményhez kapcsolt cikkek",
    "file": "A K-Monitor Adatbázisban az aktához kapcsolt cikkek",
    "newspaper": "A K-Monitor Adatbázis cikkei, amelyek címében vagy leadjében szerepel a(z) {name} név (lehetnek köztük olyanok is, amelyek nem erről a sajtótermékről szólnak)",
}


def system_instruction(web_search: bool) -> str:
    return SYSTEM_INSTRUCTION.format(
        sources_rule=SEARCH_SOURCES_RULE if web_search else GIVEN_SOURCES_RULE
    )


def format_articles(
    entity_type: str, name: str, articles: list[dict], limit_reached: bool
) -> str:
    header = ARTICLES_HEADER[entity_type].format(name=name)
    if not articles:
        return f"{header}: nincs ilyen cikk."
    count = f"a legutóbbi {len(articles)} db" if limit_reached else f"{len(articles)} db"
    lines = [f"{header} ({count}, időrendben):"]
    for article in articles:
        source = " – ".join(p for p in (article["newspaper"], article["title"]) if p)
        lines.append("")
        lines.append(f"[{article['date']}] {source}")
        if article["teaser"]:
            lines.append(article["teaser"])
        lines.append(article["url"])
    return "\n".join(lines)


def format_related(related_type: str, related: list[dict]) -> str:
    items = "; ".join(f"{r['name']} ({r['count']})" for r in related)
    return (
        f"A cikkeken leggyakrabban vele együtt szereplő {RELATED_LABELS[related_type]}, "
        f"zárójelben a közös cikkek száma: {items}"
    )


def build_prompt_text(
    entity_type: str,
    name: str,
    kmdb_url: Optional[str],
    current_description: str,
    articles: list[dict],
    limit_reached: bool,
    related: dict[str, list[dict]],
    web_search: bool,
) -> str:
    """The context comes first and the task last, as recommended for long prompts."""
    parts = [format_articles(entity_type, name, articles, limit_reached)]
    parts += [format_related(t, r) for t, r in related.items() if r]
    if articles and web_search:
        parts.append(RECENT_INSTRUCTION.format(date=articles[-1]["date"]))
    parts.append(
        TASKS[entity_type].format(name=name, kmdb_ref=f" ({kmdb_url})" if kmdb_url else "")
    )
    if current_description:
        parts.append(UPDATE_INSTRUCTION.format(
            description=current_description,
            search_sources=" és a webes keresés" if web_search else "",
        ))
    return "\n\n".join(parts)
