from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os
import time
from typing import TypedDict

import requests

from .config import Config, ExportData, ExportInfo, Record


class InputRecord(TypedDict):
    """输入JSON的记录类型定义"""

    cardPoolType: int | str
    resourceId: int
    qualityLevel: int
    name: str
    resourceType: str
    count: int
    time: str
    isSorted: bool
    group: int


class InputJsonData(TypedDict):
    """输入JSON的数据结构"""

    version: str
    date: str
    playerId: str
    pulls: list[InputRecord]


@dataclass
class ResourceMapper:
    """资源映射器，用于缓存API数据"""

    weapon_map: dict[int, str] = field(default_factory=dict)
    character_map: dict[int, str] = field(default_factory=dict)


class JsonConverter:
    """JSON文件转换器，用于处理Wuwatracker的JSON数据"""

    def __init__(self, file_path: str, output_dir: str | None = None):
        """
        初始化JSON转换器

        Args:
            file_path: JSON文件路径
            output_dir: 输出目录，如果为None则使用文件所在目录
        """
        self.file_path: str = os.path.abspath(file_path)
        self.output_dir: str = output_dir if output_dir else os.path.dirname(self.file_path)
        self.resource_mapper: ResourceMapper = ResourceMapper()
        self.export_data: ExportData = self._init_export_data()

    def _init_export_data(self) -> ExportData:
        """
        初始化导出数据

        Returns:
            初始化后的导出数据
        """
        current_time = time.localtime()

        info: ExportInfo = {
            "export_time": time.strftime("%Y-%m-%d %H:%M:%S", current_time),
            "export_app": Config.APP_NAME,
            "export_app_version": Config.APP_VERSION,
            "export_timestamp": int(time.mktime(current_time)),
            "version": Config.EXPORT_VERSION,
            "uid": "unknown",
        }

        record_list: list[Record] = []

        export_data: ExportData = {"info": info, "list": record_list}

        return export_data

    def process(self) -> bool:
        """
        处理JSON文件

        Returns:
            处理是否成功
        """
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"文件 {self.file_path} 不存在")

            if not os.access(self.file_path, os.R_OK):
                raise PermissionError(f"文件 {self.file_path} 不可读")

            # 读取JSON文件
            with open(self.file_path, encoding="utf-8") as f:
                json_data: InputJsonData = json.load(f)

            # 处理数据
            return self._process_json_data(json_data)

        except FileNotFoundError as e:
            print(f"文件未找到 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except PermissionError as e:
            print(f"权限错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON解析错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except KeyError as e:
            print(f"数据格式错误，缺少必要字段 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except Exception as e:
            print(f"未知错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False

    def _process_json_data(self, json_data: InputJsonData) -> bool:
        """
        处理JSON数据

        Args:
            json_data: 输入的JSON数据

        Returns:
            处理是否成功
        """
        try:
            # 设置UID
            self.export_data["info"]["uid"] = json_data.get("playerId", "unknown")

            # 预加载资源映射
            self._load_resource_mappings()

            # 处理每条记录
            pulls = json_data.get("pulls", [])
            for pull in pulls:
                record = self._convert_record(pull)
                if record:
                    self.export_data["list"].append(record)

            print(f"成功处理 {len(pulls)} 条记录")
            return True

        except Exception as e:
            print(f"处理JSON数据失败: {str(e)}")
            return False

    def _load_resource_mappings(self) -> None:
        """加载资源映射（武器和角色）"""
        try:
            # 加载武器映射
            self._load_weapon_mapping()
            # 加载角色映射
            self._load_character_mapping()
        except Exception as e:
            print(f"加载资源映射失败: {str(e)}")

    def _load_weapon_mapping(self) -> None:
        """从API加载武器名称映射"""
        try:
            url = "https://api-v2.encore.moe/api/zh-Hans/weapon"
            response = requests.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            weapons = data.get("weapons", [])

            weapon_count = 0
            for weapon in weapons:
                weapon_id = weapon.get("Id")
                weapon_name = weapon.get("Name")
                if weapon_id and weapon_name:
                    self.resource_mapper.weapon_map[weapon_id] = weapon_name
                    weapon_count += 1

            print(f"已加载 {weapon_count} 个武器名称映射")

        except requests.RequestException as e:
            print(f"请求武器API失败: {str(e)}")
            # 使用备用方案或空映射
        except Exception as e:
            print(f"处理武器数据失败: {str(e)}")

    def _load_character_mapping(self) -> None:
        """从API加载角色名称映射"""
        try:
            url = "https://api-v2.encore.moe/api/zh-Hans/character"
            response = requests.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            characters = data.get("roleList", [])

            character_count = 0
            for character in characters:
                character_id = character.get("Id")
                character_name = character.get("Name")
                if character_id and character_name:
                    self.resource_mapper.character_map[character_id] = character_name
                    character_count += 1

            print(f"已加载 {character_count} 个角色名称映射")

        except requests.RequestException as e:
            print(f"请求角色API失败: {str(e)}")
            # 使用备用方案或空映射
        except Exception as e:
            print(f"处理角色数据失败: {str(e)}")

    def _convert_record(self, input_record: InputRecord) -> Record | None:
        """
        转换单条记录

        Args:
            input_record: 输入记录

        Returns:
            转换后的记录，如果转换失败则返回None
        """
        try:
            # 转换卡池类型
            card_pool_type = self._convert_card_pool_type(input_record.get("cardPoolType", 0))

            # 转换资源类型
            resource_type = self._convert_resource_type(input_record.get("resourceType", ""))

            # 转换名称（英文转中文）
            name = self._convert_name(
                input_record.get("resourceId", 0), input_record.get("resourceType", ""), input_record.get("name", "")
            )

            # 转换时间格式
            time_str = self._convert_time_format(input_record.get("time", ""))

            return {
                "cardPoolType": card_pool_type,
                "resourceId": input_record.get("resourceId", 0),
                "qualityLevel": input_record.get("qualityLevel", 3),
                "resourceType": resource_type,
                "name": name,
                "count": input_record.get("count", 1),
                "time": time_str,
            }

        except Exception as e:
            print(f"转换记录失败: {str(e)}, 记录: {input_record}")
            return None

    def _convert_card_pool_type(self, pool_type: int) -> str:
        """
        转换卡池类型

        Args:
            pool_type: 卡池类型数字

        Returns:
            卡池类型字符串
        """
        # 创建反向映射
        reverse_mapping = {v: k for k, v in Config.POOLTYPE_MAPPING.items()}

        # 将数字转为字符串查找
        pool_type_str = str(pool_type)
        return reverse_mapping.get(pool_type_str, f"{pool_type}")

    def _convert_resource_type(self, resource_type: str) -> str:
        """
        转换资源类型

        Args:
            resource_type: 资源类型字符串

        Returns:
            转换后的资源类型
        """
        return Config.RESOURCE_TYPE_MAPPING.get(resource_type, resource_type)

    def _convert_name(self, resource_id: int, resource_type: str, original_name: str) -> str:
        """
        转换名称（英文转中文）

        Args:
            resource_id: 资源ID
            original_name: 原始名称

        Returns:
            转换后的中文名称
        """
        # 根据资源类型选择不同的映射表
        if resource_id in self.resource_mapper.weapon_map:
            return self.resource_mapper.weapon_map[resource_id]
        if resource_id in self.resource_mapper.character_map:
            return self.resource_mapper.character_map[resource_id]
        # 若找不到映射，打印警告并返回原始名称
        print(f"警告：未找到资源 ID {resource_id} 的英文名，使用原始名称 '{original_name}'")
        return original_name

    def _convert_time_format(self, time_str: str) -> str:
        """
        转换时间格式

        Args:
            time_str: 原始时间字符串

        Returns:
            转换后的时间字符串
        """
        if not time_str:
            return ""

        try:
            # 尝试多种时间格式
            for fmt in Config.INPUT_TIME_FORMATS:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.strftime(Config.OUTPUT_TIME_FORMAT)
                except ValueError:
                    continue

            # 如果都没有匹配，尝试处理ISO格式（带时区）
            if "T" in time_str:
                # 移除Z时区标记
                if time_str.endswith("Z"):
                    time_str = time_str[:-1] + "+00:00"

                # 尝试带时区的ISO格式
                try:
                    dt = datetime.fromisoformat(time_str)
                    return dt.strftime(Config.OUTPUT_TIME_FORMAT)
                except ValueError:
                    pass

            # 如果所有格式都失败，返回原始字符串
            print(f"时间格式转换失败: {time_str}")
            return time_str

        except Exception as e:
            print(f"时间格式转换异常: {time_str}, 错误: {str(e)}")
            return time_str

    def get_export_data(self) -> ExportData:
        """
        获取导出数据

        Returns:
            完整的导出数据
        """
        return self.export_data

    def save_json(self, filename: str | None = None) -> None:
        """
        保存为JSON文件

        Args:
            filename: 自定义文件名，如果为None则自动生成
        """
        try:
            if filename is None:
                uid = self.export_data["info"]["uid"]
                filename = f"export_{uid}.json"

            output_path = os.path.join(self.output_dir, filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.export_data, f, ensure_ascii=False, indent=4)

            print(f"成功导出到: {os.path.relpath(output_path)}")

        except PermissionError:
            print(f"文件写入被拒绝: {filename}")
        except Exception as e:
            print(f"保存失败: {str(e)}")

    @property
    def record_count(self) -> int:
        """
        获取记录数量

        Returns:
            记录条数
        """
        return len(self.export_data["list"])

    @property
    def uid(self) -> str:
        """
        获取UID

        Returns:
            UID字符串
        """
        return self.export_data["info"]["uid"]


class WwuidToWuwatrackerConverter:
    """WWUID JSON 转 Wuwatracker JSON 的转换器"""

    def __init__(self, UTC_OFFSET: int, file_path: str, output_dir: str | None = None):
        """
        初始化转换器

        Args:
            file_path: WWUID 格式的 JSON 文件路径
            output_dir: 输出目录，若为 None 则使用文件所在目录
        """
        self.UTC_OFFSET: int = UTC_OFFSET
        self.file_path: str = os.path.abspath(file_path)
        self.output_dir: str = output_dir if output_dir else os.path.dirname(self.file_path)
        self.en_weapon_map: dict[int, str] = {}  # 武器 ID -> 英文名
        self.en_character_map: dict[int, str] = {}  # 角色 ID -> 英文名
        self.wwuid_data: ExportData  # 输入的 WWUID 数据
        self.wuwatracker_data: InputJsonData | None = None  # 输出的 Wuwatracker 数据

    def process(self) -> bool:
        """
        执行转换流程

        Returns:
            转换是否成功
        """
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"文件 {self.file_path} 不存在")
            with open(self.file_path, encoding="utf-8") as f:
                self.wwuid_data = json.load(f)

            if not self.wwuid_data or "info" not in self.wwuid_data or "list" not in self.wwuid_data:
                raise KeyError("WWUID 数据缺少 info 或 list 字段")

            self._load_en_resource_mappings()
            self._convert_to_wuwatracker()

            if not self.wuwatracker_data:
                raise ValueError("转换后的 Wuwatracker 数据为空")

            pulls_count = len(self.wuwatracker_data["pulls"])
            print(f"成功处理 {len(self.wwuid_data['list'])} 条记录，展开后共 {pulls_count} 条抽卡记录")
            return True

        except Exception as e:
            print(f"处理失败: {str(e)}")
            return False

    def _load_en_resource_mappings(self) -> None:
        """加载英文资源映射（武器和角色）"""
        self._load_en_weapon_mapping()
        self._load_en_character_mapping()

    def _load_en_weapon_mapping(self) -> None:
        """从 API 加载武器英文名映射"""
        try:
            url = "https://api-v2.encore.moe/api/en/weapon"
            response = requests.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            weapons = data.get("weapons", [])
            count = 0
            for weapon in weapons:
                wid = weapon.get("Id")
                en_name = weapon.get("Name")
                if wid and en_name:
                    self.en_weapon_map[wid] = en_name
                    count += 1
            print(f"已加载 {count} 个武器英文名")
        except requests.exceptions.Timeout:
            print("加载武器英文名超时，将使用原始名称")
        except requests.exceptions.RequestException as e:
            print(f"加载武器英文名请求失败: {e}，将使用原始名称")
        except Exception as e:
            print(f"加载武器英文名未知错误: {e}，将使用原始名称")

    def _load_en_character_mapping(self) -> None:
        """从 API 加载角色英文名映射"""
        try:
            url = "https://api-v2.encore.moe/api/en/character"
            response = requests.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            characters = data.get("roleList", [])
            count = 0
            for char in characters:
                cid = char.get("Id")
                en_name = char.get("Name")
                if cid and en_name:
                    self.en_character_map[cid] = en_name
                    count += 1
            print(f"已加载 {count} 个角色英文名")
        except requests.exceptions.Timeout:
            print("加载角色英文名超时，将使用原始名称")
        except requests.exceptions.RequestException as e:
            print(f"加载角色英文名请求失败: {e}，将使用原始名称")
        except Exception as e:
            print(f"加载角色英文名未知错误: {e}，将使用原始名称")

    def _convert_to_wuwatracker(self) -> None:
        """执行核心转换逻辑"""
        pulls: list[InputRecord] = []
        # 遍历每条记录
        for record in self.wwuid_data["list"]:
            card_pool_chinese = record.get("cardPoolType", "")
            card_pool_num = Config.POOLTYPE_MAPPING.get(card_pool_chinese, card_pool_chinese)

            # 根据 count 展开为多条记录
            for _ in range(record.get("count", 1)):
                en_name = self._get_en_name_by_id(
                    record["resourceId"],
                    record.get("name", ""),  # fallback 使用原始名称（可能是中文）
                )

                pull: InputRecord = {
                    "cardPoolType": int(card_pool_num),
                    "resourceId": record["resourceId"],
                    "qualityLevel": record["qualityLevel"],
                    "name": en_name,
                    "resourceType": self._convert_resource_type(record["resourceType"]),
                    "count": record["count"],
                    "time": self._convert_time_to_iso(record["time"]),
                    "isSorted": True,
                    "group": 1,
                }
                pulls.append(pull)

        # 设置group
        # 倒序遍历每条记录，上一个记录时间与当前记录时间相同则group+1，不同则group为1
        for i in range(len(pulls) - 1, -1, -1):
            if i == len(pulls) - 1:  # 最下面一条，group = 1
                pulls[i]["group"] = 1
            else:
                next_pull = pulls[i + 1]
                if pulls[i]["time"] == next_pull["time"]:
                    pulls[i]["group"] = next_pull["group"] + 1
                else:
                    pulls[i]["group"] = 1

        # 构建基础结构
        self.wuwatracker_data = {
            "version": getattr(Config, "WUWATRACKER_VERSION", "0.0.2"),
            "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "playerId": self.wwuid_data["info"]["uid"],
            "pulls": pulls,
        }

    def _get_en_name_by_id(self, resource_id: int, fallback_name: str) -> str:
        """根据资源 ID 获取英文名，若失败则返回 fallback_name"""
        if resource_id in self.en_weapon_map:
            return self.en_weapon_map[resource_id]
        if resource_id in self.en_character_map:
            return self.en_character_map[resource_id]
        # 若找不到映射，打印警告并返回原始名称
        print(f"警告：未找到资源 ID {resource_id} 的英文名，使用原始名称 '{fallback_name}'")
        return fallback_name

    def _convert_resource_type(self, resource_type: str) -> str:
        """
        转换资源类型

        Args:
            resource_type: 资源类型字符串

        Returns:
            转换后的资源类型
        """
        return Config.REVERSE_RESOURCE_TYPE_MAPPING.get(resource_type, resource_type)

    def _convert_time_to_iso(self, time_str: str) -> str:
        """
        将 WWUID 的时间格式 (YYYY-MM-DD HH:MM:SS) 转换为 ISO 8601 带时区格式
        将转换时区时间为 UTC+0，直接附加 +00:00
        """
        try:
            dt = datetime.strptime(time_str, Config.OUTPUT_TIME_FORMAT)
            dt_utc = dt - timedelta(hours = self.UTC_OFFSET)  # e.g. UTC+8 → UTC
            return dt_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        except Exception:
            print(f"时间格式转换失败: {time_str}，将原样返回")
            return time_str

    def save_json(self, filename: str | None = None) -> None:
        """
        保存转换后的 JSON 文件

        Args:
            filename: 自定义文件名，若为 None 则自动生成
        """
        if not self.wuwatracker_data:
            print("没有可保存的数据，请先调用 process()")
            return

        try:
            if filename is None:
                uid = self.wuwatracker_data["playerId"]
                filename = f"{uid}_{datetime.now().strftime('%Y-%m-%d')}_wuwatracker-pulls.json"

            output_path = os.path.join(self.output_dir, filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.wuwatracker_data, f, ensure_ascii=False, indent=2)

            print(f"成功导出到: {os.path.relpath(output_path)}")

        except Exception as e:
            print(f"保存失败: {str(e)}")
