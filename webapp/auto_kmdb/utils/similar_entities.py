"""
Finds existing db keywords (mainly institutions) that are probably the same entity as a new,
differently written name, e.g. 'MFB Zrt.' -> 'Magyar Fejlesztési Bank (MFB)' or
'Sport & Event Kft.' -> 'Sport&Event Kft.'.

The results are only suggestions: the user has to pick them explicitly on the annotation UI.
"""

import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

# Company forms are left out from the comparison: 'Auchan Magyarország Kft.' ~ 'Auchan Kft.'
LEGAL_FORMS = {
    "kft", "zrt", "nyrt", "rt", "bt", "kht", "kkt", "nkft", "nonprofit", "kozhasznu", "ltd",
    "limited", "gmbh", "inc", "llc", "srl", "plc", "ag", "sa", "sro", "doo",
}
# Articles at the start and conjunctions inside a name are not compared:
# 'A Haza Nem Eladó Mozgalom' ~ 'Haza Nem Eladó Mozgalom', 'Hotel and More' ~ 'Hotel & More'
LEADING_STOPWORDS = {"a", "az", "the"}
INNER_STOPWORDS = {"es", "of", "for"}
# Parenthesized disambiguators that are not aliases: 'Magyar Nemzet (újság)'
NON_ALIAS_PARTS = {"ujsag", "folyoirat", "hetilap", "napilap", "portal", "radio", "televizio"}

MIN_TOKEN_LEN_FOR_SUFFIX = 5
# Endings that do not change a name much:
# 'önkormányzat' ~ 'önkormányzata', 'kerület' ~ 'kerületi', 'holding' ~ 'holdings'
IGNORED_SUFFIXES = {"a", "e", "i", "ja", "je", "s"}
# Tokens matched only by ignoring a suffix count less than identical tokens
SUFFIX_MATCH_WEIGHT = 0.85
# Tokens contained in more names than this are not used for candidate retrieval (e.g. 'magyar')
MAX_RETRIEVAL_DF = 1000
# Names weighting less than a token used in ~5 names are not distinctive (math.log(5) ~ 1.6)
DISTINCTIVE_IDF_MARGIN = 1.5

EXACT_SCORE = 1.0
# 'MFB Zrt.' ~ 'Magyar Fejlesztési Bank (MFB)'
ACRONYM_ALIAS_SCORE = 0.95
# 'MFB' ~ 'Magyar Fejlesztési Bank', initials are less reliable than aliases given in the db
INITIALS_SCORE = 0.85
# 'Kispest' ~ 'Budapest Főváros XIX. kerület Önkormányzata (Kispest)'
WORD_ALIAS_SCORE = 0.7


def _fold(text: str) -> str:
    """Lowercase, remove accents and spell out symbols."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"['’`´]", "", text)  # McDonald's -> mcdonalds
    text = re.sub(r"\b(\w)\.(?=\w\.)", r"\1", text)  # s.r.o. -> sro.
    text = text.replace("&", " es ").replace("+", " plusz ")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )
    return re.sub(r"\band\b", "es", text)


def _tokenize(text: str) -> list[str]:
    tokens = [t for t in re.split(r"[\W_]+", _fold(text)) if t]
    while len(tokens) > 1 and tokens[-1] in LEGAL_FORMS:
        tokens.pop()
    content_tokens = [
        t for i, t in enumerate(tokens)
        if not (i == 0 and t in LEADING_STOPWORDS) and not (i > 0 and t in INNER_STOPWORDS)
    ]
    return content_tokens or tokens


def _is_acronym(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    upper = sum(c.isupper() for c in letters)
    return upper >= 2 and upper >= len(letters) / 2


@dataclass(frozen=True)
class NormalizedName:
    tokens: tuple[str, ...]
    key: str
    acronym_aliases: frozenset[str]
    word_aliases: frozenset[str]
    initials: str


def normalize(name: str) -> NormalizedName:
    """
    Normalizes a name for comparison:
        - lowercase, without accents, punctuation and trailing company forms
        - '&', 'and' -> 'es', '+' -> 'plusz'
        - parenthesized parts are aliases: 'Magyar Fejlesztési Bank (MFB)' has the alias 'mfb'
        - names of at least 3 words also get their initials as an alias
    """
    alias_pattern = r"(?:^|(?<=\s))\(([^)]*)\)"
    main = re.sub(alias_pattern, " ", name)
    acronym_aliases, word_aliases = set(), set()
    for part in re.findall(alias_pattern, name):
        if _is_acronym(part):
            # 'Semmelweis Egyetem (SE/SOTE)'
            for acronym in re.split(r"[/,;]", part):
                key = "".join(_tokenize(acronym))
                if len(key) >= 2:
                    acronym_aliases.add(key)
        else:
            key = "".join(_tokenize(part))
            if len(key) >= 2 and key not in NON_ALIAS_PARTS:
                word_aliases.add(key)

    tokens = _tokenize(main)
    initials = "".join(t[0] for t in tokens if not t.isdigit())
    return NormalizedName(
        tokens=tuple(tokens),
        key="".join(tokens),
        acronym_aliases=frozenset(acronym_aliases),
        word_aliases=frozenset(word_aliases),
        initials=initials if len(initials) >= 3 else "",
    )


def _token_similarity(a: str, b: str) -> float:
    """
    1 for identical tokens, SUFFIX_MATCH_WEIGHT if they only differ in an ignored suffix,
    0 otherwise.
    """
    if a == b:
        return 1.0
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if (
        len(short) >= MIN_TOKEN_LEN_FOR_SUFFIX
        and long.startswith(short)
        and long[len(short):] in IGNORED_SUFFIXES
    ):
        return SUFFIX_MATCH_WEIGHT
    return 0.0


class SimilarEntityIndex:
    """
    In-memory index of db keywords for finding the probable duplicates of a name.

    Scores are between 0 and 1:
        1.0  the normalized names are identical ('Sport & Event Kft.' ~ 'Sport&Event Kft.')
        0.95 the name is an acronym alias of the keyword ('MFB Zrt.' ~ 'Magyar Fejlesztési Bank
             (MFB)'), or the other way around
        0.85 the name is the initials of the keyword ('MFB' ~ 'Magyar Fejlesztési Bank')
        0.7  the name is a parenthesized alias of the keyword ('Kispest' ~ 'Budapest Főváros XIX.
             kerület Önkormányzata (Kispest)')
        else weighted token overlap, where rare words count more than common ones like 'magyar'
    """

    def __init__(self, entities: Iterable[dict]):
        """
        Args:
            entities: dicts containing the 'id' and 'name' of db keywords and optionally their
                usage 'count'
        """
        self.entities: dict[int, dict] = {}
        self.normalized: dict[int, NormalizedName] = {}
        self.by_key: dict[str, set[int]] = defaultdict(set)
        self.by_acronym_alias: dict[str, set[int]] = defaultdict(set)
        self.by_word_alias: dict[str, set[int]] = defaultdict(set)
        self.by_initials: dict[str, set[int]] = defaultdict(set)
        self.by_token: dict[str, set[int]] = defaultdict(set)
        self.tokens_by_prefix: dict[str, set[str]] = defaultdict(set)

        for entity in entities:
            self.add(entity)
        n = len(self.entities)
        self.idf: dict[str, float] = {
            token: math.log(1 + n / len(ids)) for token, ids in self.by_token.items()
        }
        self.max_idf = math.log(1 + n)
        self.distinctive_weight = self.max_idf - DISTINCTIVE_IDF_MARGIN

    def add(self, entity: dict) -> None:
        """
        Adds a db keyword to the index, e.g. after it has been created. Token weights are not
        recalculated, new tokens count as rare ones.
        """
        if not entity.get("name") or entity.get("id") is None:
            return
        entity_id = int(entity["id"])
        normalized = normalize(entity["name"])
        if not normalized.key:
            return
        self.entities[entity_id] = entity
        self.normalized[entity_id] = normalized
        self.by_key[normalized.key].add(entity_id)
        for alias in normalized.acronym_aliases:
            self.by_acronym_alias[alias].add(entity_id)
        for alias in normalized.word_aliases:
            self.by_word_alias[alias].add(entity_id)
        if normalized.initials:
            self.by_initials[normalized.initials].add(entity_id)
        for token in normalized.tokens:
            self.by_token[token].add(entity_id)
            self.tokens_by_prefix[token[:MIN_TOKEN_LEN_FOR_SUFFIX]].add(token)

    def _weight(self, token: str) -> float:
        return self.idf.get(token, self.max_idf)

    def _similar_tokens(self, token: str) -> set[str]:
        return {
            t for t in self.tokens_by_prefix.get(token[:MIN_TOKEN_LEN_FOR_SUFFIX], ())
            if _token_similarity(token, t) > 0
        }

    def _overlap_score(self, query: tuple[str, ...], candidate: tuple[str, ...]) -> float:
        """
        Combines how much of the shorter name is covered by the other one with how much the two
        names have in common in total, every token weighted by its idf.
        """
        candidate_tokens = set(candidate)
        query_weight = candidate_weight = matched_query = matched_candidate = 0.0
        for token in set(query):
            best_match, best_similarity = None, 0.0
            for candidate_token in candidate_tokens:
                similarity = _token_similarity(token, candidate_token)
                if similarity > best_similarity:
                    best_match, best_similarity = candidate_token, similarity
            # unknown tokens are rare by definition, unless they are a variant of a known token
            weight = self.idf.get(token, self._weight(best_match) if best_match else self.max_idf)
            query_weight += weight
            if best_match:
                candidate_tokens.remove(best_match)
                matched_query += best_similarity * weight
                matched_candidate += best_similarity * self._weight(best_match)
                candidate_weight += self._weight(best_match)
        if matched_query == 0:
            return 0.0
        candidate_weight += sum(self._weight(t) for t in candidate_tokens)

        def distinctiveness(weight: float) -> float:
            return min(1.0, weight / self.distinctive_weight)

        # being contained only counts if the contained name is distinctive enough:
        # 'Auchan Kft.' in 'Auchan Magyarország Kft.' does, 'Szolgáltató Bt.' in anything does not
        containment = max(
            matched_query / query_weight * distinctiveness(query_weight),
            matched_candidate / candidate_weight * distinctiveness(candidate_weight),
        )
        dice = (matched_query + matched_candidate) / (query_weight + candidate_weight)
        return (containment + dice) / 2

    def find(
        self,
        name: str,
        limit: int = 3,
        min_score: float = 0.6,
        exclude_ids: Iterable[int] = (),
    ) -> list[dict]:
        """
        Returns the db keywords that are probably the same entity as the given name.

        Args:
            name: the name to search for, e.g. a detected entity or a name typed by the user
            limit: maximum number of returned keywords
            min_score: keywords with lower score are dropped
            exclude_ids: ids of db keywords not to return

        Returns:
            List of dicts containing the 'id', 'name', 'count' and similarity 'score' of the
            keywords, ordered by score and count.
        """
        query = normalize(name)
        if not query.key:
            return []
        excluded = set(exclude_ids)
        scores: dict[int, float] = {}

        def add(ids: Iterable[int], score: float):
            for entity_id in ids:
                if entity_id not in excluded and score > scores.get(entity_id, 0):
                    scores[entity_id] = score

        add(self.by_key.get(query.key, ()), EXACT_SCORE)
        add(self.by_acronym_alias.get(query.key, ()), ACRONYM_ALIAS_SCORE)
        for alias in query.acronym_aliases:
            add(self.by_key.get(alias, ()), ACRONYM_ALIAS_SCORE)
        add(self.by_initials.get(query.key, ()), INITIALS_SCORE)
        if query.initials:
            add(self.by_key.get(query.initials, ()), INITIALS_SCORE)
        add(self.by_word_alias.get(query.key, ()), WORD_ALIAS_SCORE)
        for alias in query.word_aliases:
            add(self.by_key.get(alias, ()), WORD_ALIAS_SCORE)

        candidates: set[int] = set()
        for token in query.tokens:
            for similar_token in self._similar_tokens(token):
                ids = self.by_token[similar_token]
                if len(ids) <= MAX_RETRIEVAL_DF:
                    candidates |= ids
        for entity_id in candidates - excluded:
            score = self._overlap_score(query.tokens, self.normalized[entity_id].tokens)
            if score > scores.get(entity_id, 0):
                scores[entity_id] = score

        ranked = sorted(
            (entity_id for entity_id, score in scores.items() if score >= min_score),
            key=lambda entity_id: (
                -scores[entity_id], -(self.entities[entity_id].get("count") or 0)
            ),
        )
        return [
            {
                "id": entity_id,
                "name": self.entities[entity_id]["name"],
                "count": self.entities[entity_id].get("count"),
                "score": round(scores[entity_id], 3),
            }
            for entity_id in ranked[:limit]
        ]
