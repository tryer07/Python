# 定义一个名为TextFileHandler的类，该类支持文本文件的读取和写入功能（优化版）
# 优化点：
# 1. 菜单式交互：用户进入程序后可选择 读取文件 / 写入文件 / 退出
# 2. 写入时进一步询问写入方式：w = 覆盖（更改）已存在的文本内容，a = 在已存在内容后面追加新内容
#    （对应 open() 的 'w' / 'a' 模式；若文件尚不存在则自动新建，无需再做覆盖/追加的选择）
# 3. 类中新增 exists() 用于判断文件是否存在；read_file 不再在类内部打印"成功"，展示职责交给主程序
# 4. write_file 返回 True/False 表示成败，主程序分别给出成功与失败提示
# 5. 输入辅助函数统一采用标志位循环 + 循环外统一返回，输错不会崩溃，也不会产生隐式 None 类型警告


import os


# ---------- 文本文件处理类 ----------
class TextFileHandler:

    """用于处理文本文件的读取和写入操作"""

    def __init__(self, file_path):

        """
        初始化TextFileHandler对象
        :param file_path: 文本文件路径
        """
        self.file_path = file_path  # 文本文件路径

    def exists(self):

        """
        判断文件是否存在
        :return: 存在返回 True，否则返回 False
        """
        return os.path.exists(self.file_path)

    def read_file(self):

        """
        读取文本文件内容
        :return: 文件内容字符串；读取失败时返回空字符串（类型恒为 str，不混入 None）
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f'  [读取失败] 发生错误：{e}')
            return ''

    def write_file(self, content, append=False):

        """
        写入文本文件内容
        :param content: 要写入的文本内容（str）
        :param append: False = 用新内容覆盖原有内容；True = 在原有内容后面追加
        :return: 写入成功返回 True，失败返回 False
        """

        # 根据选择决定打开模式：'a' 追加到文件末尾，'w' 清空后重写
        mode = 'a' if append else 'w'
        try:
            with open(self.file_path, mode, encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            print(f'  [写入失败] 发生错误：{e}')
            return False


# ---------- 输入辅助函数 ----------
def input_write_mode():

    """
    选择写入方式（标志位循环 + 循环外统一返回）
    :return: True 表示追加到已有内容后面，False 表示覆盖更改原有内容
    """
    append = False
    valid = False

    while not valid:
        ans = input('  请选择写入方式（w = 更改已存在的文本内容 / a = 在已存在内容后追加）：').strip().lower()
        if ans == 'w':
            append = False
            valid = True
        elif ans == 'a':
            append = True
            valid = True
        else:
            print('  [输入无效] 请输入 w(覆盖) 或 a(追加)。')

    return append


def input_content():

    """
    输入要写入的文本内容：逐行输入，空行结束，至少要有一行非空内容
    （标志位循环 + 循环外统一返回）
    :return: 多行文本用换行符连接后的字符串
    """
    print('  请输入要写入的内容（每行一条，直接回车空行结束）：')

    lines: list[str] = []
    result = ''
    valid = False

    while not valid:
        line = input('    > ')
        if line.strip():
            lines.append(line)
            continue
        # 输入空行表示结束；一行内容都没有则重新提示
        if lines:
            result = '\n'.join(lines)
            valid = True
        else:
            print('  [输入无效] 内容不能为空，请重新输入。')

    return result


# ---------- 主程序 ----------
if __name__ == '__main__':

    print('==== 欢迎使用文本文件处理系统（优化版）====')

    handler = TextFileHandler('example.txt')

    # 菜单主循环：用户可反复选择读取/写入，直到选择退出
    while True:

        print('\n请选择要执行的操作：')
        print('1. 读取文件')
        print('2. 写入文件')
        print('0. 退出系统')

        choice = input('请输入您的选择（0 / 1 / 2）：').strip()

        if choice == '1':
            if not handler.exists():
                print(f'  文件 {handler.file_path} 还不存在，请先执行写入操作。')
            else:
                content = handler.read_file()
                if content:
                    print(f'  文件内容如下（共 {len(content)} 个字符）：')
                    print('-' * 36)
                    print(content)
                    print('-' * 36)
                else:
                    print('  文件存在，但内容为空。')
        elif choice == '2':
            # 文件不存在时两种写法效果一致，直接新建，无需询问覆盖还是追加
            if handler.exists():
                append = input_write_mode()
            else:
                print(f'  文件 {handler.file_path} 还不存在，将自动新建。')
                append = False

            content = input_content()
            if handler.write_file(content, append):
                if append:
                    print(f'  已在原有内容后成功追加 {len(content)} 个字符。')
                else:
                    print(f'  已成功用新内容更改 {handler.file_path}。')
        elif choice == '0':
            print('已退出系统，感谢使用，再见！')
            break
        else:
            print('  无效的选项，请输入 0、1 或 2。')
