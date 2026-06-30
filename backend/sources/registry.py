from backend.sources.korea_ntb import KoreaNTBSource
from backend.sources.wipo_patentscope import WIPOPatentscopeSource
from backend.sources.ip_australia import IPAustraliaSource
from backend.sources.csir_india import CSIRIndiaSource
from backend.sources.dost_tapi import DOSTTAPISource
from backend.sources.slintec import SLINTECSource
from backend.sources.tech2biz import Tech2BizSource
from backend.sources.jst_japan import JSTJapanSource
from backend.config import settings

_ip_aus = IPAustraliaSource()
_csir = CSIRIndiaSource()
_dost = DOSTTAPISource()
_slintec = SLINTECSource()
_tech2biz = Tech2BizSource()
_jst = JSTJapanSource()

SOURCES = [
    KoreaNTBSource(),
    WIPOPatentscopeSource(),
    *([_ip_aus] if settings.IP_AUSTRALIA_CLIENT_ID else []),
    _csir,
    _dost,
    _slintec,
    _tech2biz,
    _jst,
]

SOURCE_MAP = {s.id: s for s in SOURCES}
