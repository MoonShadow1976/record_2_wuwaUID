from dataclasses import dataclass, field
from datetime import datetime
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
    isSorted: bool | None
    group: int | None


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
            url = "https://api-v2.encore.moe/zh-Hans/weapon"
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
            url = "https://api-v2.encore.moe/zh-Hans/character"
            response = requests.get(url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()

            characters = response.json()  # API返回的是数组

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
            resource_type: 资源类型
            original_name: 原始名称

        Returns:
            转换后的中文名称
        """
        # 根据资源类型选择不同的映射表
        if resource_type == "Weapon":
            chinese_name = self.resource_mapper.weapon_map.get(resource_id)
        elif resource_type == "Character":
            chinese_name = self.resource_mapper.character_map.get(resource_id)
        else:
            chinese_name = None

        # 如果找到中文名称，返回中文名称，否则返回原始名称
        if chinese_name:
            return chinese_name
        else:
            # 如果找不到映射，尝试记录日志
            if resource_type in ["Weapon", "Character"]:
                print(f"警告：未找到资源ID {resource_id} ({resource_type}) 的中文名称映射")
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
