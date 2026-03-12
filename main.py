import os

from src.wuwatool_excel_converter import ExcelProcessor
from src.wuwatracker_json_converter import JsonConverter, WwuidToWuwatrackerConverter

src_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.normpath(os.path.join(src_dir, ".", "data"))
export_dir = os.path.normpath(os.path.join(src_dir, ".", "export"))


def batch_process():
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.makedirs(export_dir)
        print(f"已创建数据目录: {data_dir}")
        print(f"请将需要处理的 抽卡记录 文件放入 {data_dir} 文件夹中，然后重新运行程序。")
        return

    for filename in os.listdir(data_dir):
        if filename.endswith(".xlsx"):
            full_path = os.path.join(data_dir, filename)
            print(f"\n正在处理表格文件: {filename}")
            processor = ExcelProcessor(full_path, export_dir)
            if processor.process():
                processor.save_json()
            else:
                print(f"文件处理中止: {filename}")

        if filename.endswith(".json"):
            full_path = os.path.join(data_dir, filename)
            print(f"\n正在处理JSON文件: {filename}")
            converter = JsonConverter(full_path, export_dir)
            if converter.process():
                converter.save_json()
            else:
                print(f"文件处理中止: {filename}")


def conver_to_wuwatracker():
    conver_file = "export_你的uid.json"
    utc_timezone = 8  # e.g. UTC+8 将被转换为 UTC+0
    converter = WwuidToWuwatrackerConverter(utc_timezone, f"{export_dir}/{conver_file}", export_dir)
    if converter.process():
        converter.save_json()


if __name__ == "__main__":
    try:
        batch_process()
        conver_to_wuwatracker()
    except Exception as e:
        print(f"程序异常终止: {str(e)}")
