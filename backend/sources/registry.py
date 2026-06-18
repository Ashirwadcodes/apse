from backend.sources.korea_ntb import KoreaNTBSource
from backend.sources.wipo_patentscope import WIPOPatentscopeSource
from backend.sources.india_tifac import IndiaTIFACSource
from backend.sources.ip_australia import IPAustraliaSource
from backend.config import settings

_ip_aus = IPAustraliaSource()

SOURCES = [
    KoreaNTBSource(),
    WIPOPatentscopeSource(),
    IndiaTIFACSource(),
    *([_ip_aus] if settings.IP_AUSTRALIA_CLIENT_ID else []),
]

SOURCE_MAP = {s.id: s for s in SOURCES}
