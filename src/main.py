import os
from excel_converter import ExcelProcessor

def batch_process():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(src_dir, "..", "data"))
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建数据目录: {data_dir}")
        print(f"请将需要处理的 .xlsx 文件放入 {data_dir} 文件夹中，然后重新运行程序。")
        return

    for filename in os.listdir(data_dir):
        if filename.endswith(".xlsx"):
            full_path = os.path.join(data_dir, filename)
            print(f"\n正在处理文件: {filename}")
            processor = ExcelProcessor(full_path)
            if processor.process():
                processor.save_json()
            else:
                print(f"文件处理中止: {filename}")

if __name__ == "__main__":
    try:
        batch_process()
    except Exception as e:
        print(f"程序异常终止: {str(e)}")