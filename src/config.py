class Config:
    APP_NAME = "WutheringWavesUID"
    APP_VERSION = "2.0.1"
    EXPORT_VERSION = "v2.0"
    REQUIRED_COLUMNS = ["卡池", "资源ID", "星级", "类型", "名称", "数量", "时间"]
    RECORD_TEMPLATE = {
        "cardPoolType": "",
        "resourceId": 0,
        "qualityLevel": 0,
        "resourceType": "",
        "name": "",
        "count": 1,
        "time": ""
    }