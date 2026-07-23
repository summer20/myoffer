DEFAULT_INDUSTRIES = ["互联网", "游戏", "金融", "消费", "制造", "其他"]
DEFAULT_SCALE_TAGS = ["上市", "世界500强", "中国500强", "独角兽"]
DEFAULT_POSITIONS = [
    "后端开发",
    "前端开发",
    "算法工程师",
    "产品经理",
    "数据分析",
    "测试开发",
    "运营",
]
DEFAULT_CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
DEFAULT_STAGES = [
    "已投递",
    "笔试",
    "测评",
    "一面",
    "二面",
    "三面",
    "HR面",
    "offer",
    "已拒",
    "已弃",
]
DEFAULT_RESUME_CATEGORIES = [
    "基本信息",
    "教育经历",
    "实习经历",
    "项目经历",
    "技能特长",
    "荣誉奖项",
    "自我评价",
]


def merge_options(defaults: list[str], existing_values: list[str]) -> list[str]:
    """defaults (in order) followed by any extra existing DB values, sorted, deduped, blanks dropped."""
    seen = set(defaults)
    extra = sorted(
        {v.strip() for v in existing_values if v and v.strip() and v.strip() not in seen}
    )
    return list(defaults) + extra
