from sqlalchemy.orm import Session

from app.models import Company

SEED_COMPANIES = [
    {"name": "字节跳动", "industry": "互联网", "scale_tags": ["独角兽"]},
    {"name": "腾讯", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "阿里巴巴", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "百度", "industry": "互联网", "scale_tags": ["上市"]},
    {"name": "美团", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "拼多多", "industry": "互联网", "scale_tags": ["上市"]},
    {"name": "网易", "industry": "游戏", "scale_tags": ["上市"]},
    {"name": "米哈游", "industry": "游戏", "scale_tags": ["独角兽"]},
    {"name": "中信证券", "industry": "金融", "scale_tags": ["上市"]},
    {"name": "招商银行", "industry": "金融", "scale_tags": ["上市", "世界500强"]},
    {"name": "华为", "industry": "制造", "scale_tags": ["世界500强"]},
]


def seed_if_empty(db: Session) -> int:
    """Insert the seed companies only if the companies table is currently empty.

    recruiting_open/recruiting_url are intentionally left at their defaults
    (False/None) — these are time-sensitive and must be verified (e.g. via
    web search) or filled in by hand rather than fabricated here.
    """
    if db.query(Company).count() > 0:
        return 0
    for entry in SEED_COMPANIES:
        db.add(Company(name=entry["name"], industry=entry["industry"], scale_tags=entry["scale_tags"]))
    db.commit()
    return len(SEED_COMPANIES)
