import os
import pandas as pd
import time
import json
import warnings
from config import Config

class ExcelProcessor:
    def __init__(self, file_path):
        self.file_path = os.path.abspath(file_path)
        self.export_data = self._init_export_data()
        self.found_uid = False

    def _init_export_data(self):
        current_time = time.localtime()
        return {
            "info": {
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S", current_time),
                "export_app": Config.APP_NAME,
                "export_app_version": Config.APP_VERSION,
                "export_timestamp": int(time.mktime(current_time)),
                "version": Config.EXPORT_VERSION,
                "uid": "unknown"
            },
            "list": []
        }

    def process(self):
        try:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"文件 {self.file_path} 不存在")
                
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
                excel_file = pd.ExcelFile(self.file_path)
                self._process_uid(excel_file)
                self._process_sheets(excel_file)
            return True
        except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as e:
            print(f"文件处理失败 ({os.path.basename(self.file_path)}): {str(e)}")
            return False
        except Exception as e:
            print(f"未知错误 ({os.path.basename(self.file_path)}): {str(e)}")
            return False

    def _process_uid(self, excel_file):
        for sheet in excel_file.sheet_names:
            if sheet.isdigit():
                self.export_data["info"]["uid"] = sheet
                self.found_uid = True
                break

    def _process_sheets(self, excel_file):
        for sheet in excel_file.sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet)
                self._validate_columns(df.columns)
                self._process_sheet_data(df, sheet)
            except KeyError as e:
                print(f"工作表 {sheet} 缺少必要列: {str(e)}")
            except Exception as e:
                print(f"处理工作表 {sheet} 失败: {str(e)}")

    def _validate_columns(self, columns):
        missing = set(Config.REQUIRED_COLUMNS) - set(columns)
        if missing:
            raise ValueError(f"缺少必要列: {', '.join(missing)}")

    def _process_sheet_data(self, df, sheet_name):
        for _, row in df.iterrows():
            try:
                record = self._create_record(row)
                self.export_data["list"].append(record)
            except (ValueError, TypeError) as e:
                print(f"数据类型错误: {str(e)}")
            except Exception as e:
                print(f"记录处理失败: {str(e)}")

    def _create_record(self, row):
        return {
            "cardPoolType": str(row["卡池"]),
            "resourceId": int(row["资源ID"]),
            "qualityLevel": int(row["星级"]),
            "resourceType": str(row["类型"]),
            "name": str(row["名称"]),
            "count": int(row["数量"]),
            "time": str(row["时间"])
        }

    def save_json(self):
        output_file = f"export_{self.export_data['info']['uid']}.json"
        try:
            output_path = os.path.join(os.path.dirname(self.file_path), "..", "data", output_file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.export_data, f, ensure_ascii=False, indent=4)
            print(f"成功导出到: {os.path.relpath(output_path)}")
        except PermissionError:
            print(f"文件写入被拒绝: {output_file}")
        except Exception as e:
            print(f"保存失败: {str(e)}")