from backend.sources.korea_ntb import KoreaNTBSource

SOURCES = [
    KoreaNTBSource(),
]

SOURCE_MAP = {s.id: s for s in SOURCES}
