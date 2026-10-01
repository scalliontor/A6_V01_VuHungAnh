"""Unicode normalization shared by query parsing and catalog matching."""
import unicodedata


def fold_accents(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))
