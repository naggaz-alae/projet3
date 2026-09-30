"""Découpage des contrats en passages (« chunks ») qui suivent leur structure.

Pourquoi ne pas couper tous les N caractères ? Parce qu'une exclusion séparée
de la garantie qu'elle limite fait répondre « couvert » à tort. On coupe donc
aux titres de sections, et chaque passage garde son « fil d'Ariane »
(ex. « 5 - Garanties > 5.14 Responsabilités civiles »).

Les assureurs numérotent différemment, on reconnaît plusieurs formats :
  « Article 12 - … »   « TITRE II … » / « Chapitre 3 » / « Section I - … »
  « 2.1 Biens immobiliers »   « 1 - Présentation »   « 4. INCENDIE »
"""

import re
from dataclasses import asdict, dataclass

from ingestion.parse_pdf import Page

# Niveau hiérarchique de chaque type de titre (1 = le plus haut)
_NIVEAU_MOT = {"titre": 1, "partie": 1, "chapitre": 2, "section": 3, "article": 4}

MOTIF_MOT_CLE = re.compile(
    r"^(TITRE|Titre|PARTIE|Partie|CHAPITRE|Chapitre|SECTION|Section)\s+([IVXLC]+|\d+)\b"
)
# « Article 12 - Vol » oui, mais « Article L. 113-2 du Code des assurances » non :
# on exige un numéro suivi d'un séparateur, d'une majuscule ou de la fin de ligne.
MOTIF_ARTICLE = re.compile(r"^(ARTICLE|Article)\s+\d+[A-Za-z]?\s*(?:$|[-–:.]|[A-ZÀ-Ý])")
MOTIF_DECIMAL = re.compile(
    r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s*(?:[-–]\s*)?[A-ZÀÂÇÉÈÊËÎÏÔÛÙÜŸ]"
)
# Lignes de sommaire : « 2.1 Biens assurés ........ 12 » -> ignorées
MOTIF_SOMMAIRE = re.compile(r"(\.\s?){4,}\s*\d*\s*$")

LONGUEUR_MAX_TITRE = 120
PREAMBULE = "Préambule"


@dataclass
class Chunk:
    chunk_id: str
    contrat_id: str
    section: str        # fil d'Ariane des titres
    page_debut: int
    page_fin: int
    texte: str

    def to_dict(self) -> dict:
        return asdict(self)


def niveau_titre(ligne: str) -> int | None:
    """Renvoie le niveau hiérarchique si la ligne est un titre de section, sinon None."""
    if len(ligne) > LONGUEUR_MAX_TITRE or ligne.endswith((",", ";")):
        return None
    if m := MOTIF_MOT_CLE.match(ligne):
        return _NIVEAU_MOT[m.group(1).lower()]
    if MOTIF_ARTICLE.match(ligne):
        return _NIVEAU_MOT["article"]
    if m := MOTIF_DECIMAL.match(ligne):
        # « 2 » -> 4, « 2.1 » -> 5, « 2.1.3 » -> 6 : toujours sous les TITRE/CHAPITRE/SECTION
        return 3 + m.group(1).count(".") + 1
    return None


def decouper(pages: list[Page], contrat_id: str, taille_max: int = 2500) -> list[Chunk]:
    """Transforme les pages d'un contrat en passages structurés."""
    chunks: list[Chunk] = []
    pile_titres: list[tuple[int, str]] = []       # [(niveau, titre), ...]
    lignes_section: list[tuple[int, str]] = []    # [(page, ligne), ...]

    def section_courante() -> str:
        return " > ".join(t for _, t in pile_titres) or PREAMBULE

    def vider_section() -> None:
        if lignes_section:
            chunks.extend(_decouper_section(lignes_section, section_courante(), contrat_id,
                                            len(chunks), taille_max))
            lignes_section.clear()

    for page in pages:
        for ligne in page.texte.splitlines():
            if MOTIF_SOMMAIRE.search(ligne):
                continue
            niveau = niveau_titre(ligne)
            if niveau is None:
                lignes_section.append((page.numero, ligne))
                continue
            vider_section()
            while pile_titres and pile_titres[-1][0] >= niveau:
                pile_titres.pop()
            pile_titres.append((niveau, ligne))
    vider_section()
    return chunks


def _decouper_section(lignes: list[tuple[int, str]], section: str, contrat_id: str,
                      index_depart: int, taille_max: int) -> list[Chunk]:
    """Une section trop longue est coupée en plusieurs passages, sur des fins de ligne.
    Chaque morceau garde le même fil d'Ariane."""
    morceaux: list[list[tuple[int, str]]] = [[]]
    taille = 0
    for page, ligne in lignes:
        if taille + len(ligne) > taille_max and morceaux[-1]:
            morceaux.append([])
            taille = 0
        morceaux[-1].append((page, ligne))
        taille += len(ligne) + 1

    resultat = []
    for morceau in morceaux:
        texte = "\n".join(l for _, l in morceau).strip()
        if not texte:
            continue
        resultat.append(Chunk(
            chunk_id=f"{contrat_id}-{index_depart + len(resultat):04d}",
            contrat_id=contrat_id,
            section=section,
            page_debut=morceau[0][0],
            page_fin=morceau[-1][0],
            texte=texte,
        ))
    return resultat
