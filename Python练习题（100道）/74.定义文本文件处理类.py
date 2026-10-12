#定义一个名为TextFileHandler的类，该类支持文本文间的读取和写入功能

#定义文本文件处理类

class TextFileHandler:

    """用于处理文本文件的读取和写入操作"""

    def __init__(self,file_path):

        """初始化TextFileHandler对象"""

        self.file_path = file_path   #文本文件路径

    def read_file(self):

        """
        读取文本文件内容
        :return: 文本文件内容
        :rtype: str
        """
        try:
            with open(self.file_path,'r',encoding='utf-8') as file:
                print("文件读取成功")
                content = file.read()
                return content

        except FileNotFoundError:
            return "文件未找到"

        except Exception as e:
            return f"发生错误：{e}"

    def write_file(self,content):

        """
        写入文本文件内容
        :param content: 要写入的文本内容
        :type content: str
        """

        try:
            with open(self.file_path,'w',encoding='utf-8') as file:
                file.write(content)
                print("文件写入成功")
        except Exception as e:
            print(f"发生错误：{e}")

#示例使用

handler = TextFileHandler('example.txt')
print(handler.read_file())

handler.write_file('该文本作为74题的测试文本使用')
print(handler.read_file())
