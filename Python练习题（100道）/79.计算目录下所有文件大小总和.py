# 计算当前目录下所有文件的大小总和，并以 KB 为单位打印结果
# 实现的内容：
# 1. os.listdir() 遍历目录内容，得到该目录下的名字列表（默认只含顶层，不进入子目录）
# 2. os.path.isfile() 过滤掉文件夹，只对确认为"文件"的条目参与统计
# 3. os.path.getsize() 获取单个文件的字节数，循环累加到总大小变量
# 4. 输出时把字节总和除以 1024 转换为 KB，用格式化字符串保留两位小数
# 说明：因为 listdir 不递归，.idea 等子文件夹内的文件未被统计，
#       所以程序结果会比资源管理器显示的项目总容量偏小（视频中的误差来源）

import os


def total_size(directory):

    """
    统计目录下所有顶层文件的大小总和（不递归进入子目录）
    :param directory: 目标目录路径
    :return: 文件字节大小的总和（int）
    """

    total_bytes = 0

    for name in os.listdir(directory):
        file_path = os.path.join(directory, name)
        # 只累加文件，跳过子文件夹
        if os.path.isfile(file_path):
            total_bytes += os.path.getsize(file_path)

    return total_bytes


if __name__ == '__main__':

    # 以脚本自身所在目录为基准，保证从项目根运行也能正确定位到练习目录
    directory = os.path.dirname(os.path.abspath(__file__))

    total_bytes = total_size(directory)

    # 字节转换为 KB：除以 1024，保留两位小数
    total_kb = total_bytes / 1024
    print(f'目录「{directory}」下所有文件的大小总和为：{total_kb:.2f} KB')
