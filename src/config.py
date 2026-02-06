from typing import TypedDict


class Config:
    APP_NAME: str = "WutheringWavesUID"
    APP_VERSION: str = "3.1.1"
    EXPORT_VERSION: str = "v2.0"

    REQUIRED_COLUMNS: list[str] = ["卡池", "资源ID", "星级", "类型", "名称", "数量", "时间"]

    POOLTYPE_MAPPING: dict[str, str] = {
        "角色精准调谐": "1",
        "武器精准调谐": "2",
        "角色调谐（常驻池）": "3",
        "武器调谐（常驻池）": "4",
        "新手调谐": "5",
        "新手自选唤取": "6",
        "新手自选唤取（感恩定向唤取）": "7",
        "角色新旅唤取": "8",
        "武器新旅唤取": "9",
    }

    # JSON处理相关配置
    API_TIMEOUT: int = 10  # API请求超时时间（秒）
    API_RETRY_COUNT: int = 3  # API重试次数

    # 时间格式转换配置
    INPUT_TIME_FORMATS: list[str] = [
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
        "%Y-%m-%d %H:%M:%S",  # Standard format
    ]

    OUTPUT_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # 资源类型映射
    RESOURCE_TYPE_MAPPING: dict[str, str] = {
        "Weapon": "武器",
        "Character": "角色",
    }


class ExportInfo(TypedDict):
    """导出信息的类型定义"""

    export_time: str
    export_app: str
    export_app_version: str
    export_timestamp: int
    version: str
    uid: str


class Record(TypedDict):
    """单条记录的类型定义"""

    cardPoolType: str
    resourceId: int
    qualityLevel: int
    resourceType: str
    name: str
    count: int
    time: str


class ExportData(TypedDict):
    """完整导出数据的类型定义"""

    info: ExportInfo
    list: list[Record]
