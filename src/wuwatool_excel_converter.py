from dataclasses import dataclass
import json
import os
import time
import warnings

import pandas as pd
from pandas import DataFrame, ExcelFile

from .config import Config, ExportData, ExportInfo, Record


@dataclass
class ExcelProcessorConfig:
    """Excel处理器的配置类"""

    app_name: str
    app_version: str
    export_version: str
    required_columns: list[str]


class ExcelProcessor:
    """Excel文件处理器，用于读取Excel文件并转换为JSON格式"""

    def __init__(self, file_path: str, output_dir: str | None = None):
        """
        初始化Excel处理器

        Args:
            file_path: Excel文件路径
            output_dir: 输出目录，如果为None则使用文件所在目录
            config: 配置对象，如果为None则使用默认配置
        """
        self.file_path: str = os.path.abspath(file_path)
        self.output_dir: str = output_dir if output_dir else os.path.dirname(self.file_path)
        self.config: ExcelProcessorConfig = self._create_config()
        self.export_data: ExportData = self._init_export_data()
        self.found_uid: bool = False

    def _create_config(self) -> ExcelProcessorConfig:
        """创建配置"""
        return ExcelProcessorConfig(
            app_name=Config.APP_NAME,
            app_version=Config.APP_VERSION,
            export_version=Config.EXPORT_VERSION,
            required_columns=Config.REQUIRED_COLUMNS,
        )

    def _init_export_data(self) -> ExportData:
        """
        初始化导出数据

        Returns:
            初始化后的导出数据
        """
        current_time = time.localtime()

        # 显式构造类型正确的字典
        info: ExportInfo = {
            "export_time": time.strftime("%Y-%m-%d %H:%M:%S", current_time),
            "export_app": self.config.app_name,
            "export_app_version": self.config.app_version,
            "export_timestamp": int(time.mktime(current_time)),
            "version": self.config.export_version,
            "uid": "unknown",
        }

        record_list: list[Record] = []

        export_data: ExportData = {"info": info, "list": record_list}

        return export_data

    def process(self) -> bool:
        """
        处理Excel文件

        Returns:
            处理是否成功
        """
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"文件 {self.file_path} 不存在")

            if not os.access(self.file_path, os.R_OK):
                raise PermissionError(f"文件 {self.file_path} 不可读")

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
                excel_file: ExcelFile = pd.ExcelFile(self.file_path)
                self._process_uid(excel_file)
                self._process_sheets(excel_file)
            return True

        except FileNotFoundError as e:
            print(f"文件未找到 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except PermissionError as e:
            print(f"权限错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except pd.errors.EmptyDataError as e:
            print(f"文件为空 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except ValueError as e:
            print(f"数据错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except Exception as e:
            print(f"未知错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False

    def _process_uid(self, excel_file: ExcelFile) -> None:
        """
        处理UID（从工作表名称中查找数字）

        Args:
            excel_file: pandas Excel文件对象
        """
        for sheet_name in excel_file.sheet_names:
            if sheet_name.isdigit():
                self.export_data["info"]["uid"] = sheet_name
                self.found_uid = True
                break

    def _process_sheets(self, excel_file: ExcelFile) -> None:
        """
        处理所有工作表

        Args:
            excel_file: pandas Excel文件对象
        """
        for sheet_name in excel_file.sheet_names:
            try:
                df: DataFrame = pd.read_excel(excel_file, sheet_name=sheet_name)
                self._validate_columns(df.columns)
                self._process_sheet_data(df, sheet_name)
            except KeyError as e:
                print(f"工作表 {sheet_name} 缺少必要列: {str(e)}")
            except Exception as e:
                print(f"处理工作表 {sheet_name} 失败: {str(e)}")

    def _validate_columns(self, columns: pd.Index) -> None:
        """
        验证列名是否包含所有必需列

        Args:
            columns: DataFrame的列索引

        Raises:
            ValueError: 缺少必要列时抛出
        """
        columns_set = set(columns)
        missing_columns = set(self.config.required_columns) - columns_set

        if missing_columns:
            raise ValueError(f"缺少必要列: {', '.join(sorted(missing_columns))}")

    def _process_sheet_data(self, df: DataFrame, sheet_name: str) -> None:
        """
        处理单个工作表的数据

        Args:
            df: DataFrame对象
            sheet_name: 工作表名称
        """
        for _, row in df.iterrows():
            try:
                record: Record = self._create_record(row)
                self.export_data["list"].append(record)
            except (ValueError, TypeError) as e:
                print(f"工作表 {sheet_name} 数据类型错误: {str(e)}")
                print(f"错误行数据: {row.to_dict()}")
            except Exception as e:
                print(f"工作表 {sheet_name} 记录处理失败: {str(e)}")

    def _create_record(self, row: pd.Series) -> Record:
        """
        从单行数据创建记录

        Args:
            row: pandas Series对象，表示一行数据

        Returns:
            格式化后的记录

        Raises:
            ValueError: 当必要字段转换失败时抛出
            TypeError: 当数据类型不匹配时抛出
        """
        try:
            return {
                "cardPoolType": str(row["卡池"]),
                "resourceId": int(row["资源ID"]),
                "qualityLevel": int(row["星级"]),
                "resourceType": str(row["类型"]),
                "name": str(row["名称"]),
                "count": int(row["数量"]),
                "time": str(row["时间"]),
            }
        except ValueError as e:
            raise ValueError(f"数据转换失败: {str(e)}，行数据: {row.to_dict()}")
        except TypeError as e:
            raise TypeError(f"数据类型错误: {str(e)}，行数据: {row.to_dict()}")

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

        Returns:
            保存的文件路径，如果保存失败则返回None
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
