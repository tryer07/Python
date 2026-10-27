# 按文件后缀名自动整理文件夹：把散落在目录中的文件，移动到以各自扩展名命名的分类文件夹里
# 实现的内容：
# 1. os.listdir() 遍历指定目录下的所有文件和子目录
# 2. os.path.splitext() 分割文件名与扩展名，切片 [1:] 去掉前导点号，得到纯扩展名作为分类依据
# 3. os.path.isdir() 判断分类文件夹是否存在，不存在则 os.makedirs() 创建
# 4. shutil.move() 移动文件（比 os.rename() 更适合跨目录移动场景）
# 5. 关键写法：把"移动文件"放在 if 判断之外，而非 else 分支
#    无论文件夹是新建还是已存在，文件都能被正确移动，从而消除代码重复
# 6. 路径统一用 os.path.join() 拼接，交由系统处理分隔符，避免手写反斜杠带来的转义问题

import os
import shutil


def organize_folder(directory):

    """
    按文件后缀名把目录中的文件整理进对应的分类文件夹
    :param directory: 要整理的目录路径
    :return: 字典 {扩展名: 移动的文件个数}，用于汇总展示
    """

    moved_counts = {}

    for name in os.listdir(directory):
        # 用 join 拼接完整路径，分隔符交给系统处理，避免转义字符问题
        source_path = os.path.join(directory, name)

        # 已经整理好的分类文件夹（子目录）跳过，不重复处理
        if os.path.isdir(source_path):
            continue

        # splitext 分割出 (文件名, 带点的扩展名)，切片 [1:] 去掉前导点号
        extension = os.path.splitext(name)[1][1:]

        # 没有扩展名的文件归入 other 类，避免生成空文件夹名
        if not extension:
            extension = 'other'

        target_dir = os.path.join(directory, extension)
        # 分类文件夹不存在则创建（存在时什么都不做）
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        # 移动代码放在 if 之外：无论文件夹是新建还是早已存在，文件都会被移动
        target_path = os.path.join(target_dir, name)
        shutil.move(source_path, target_path)

        moved_counts[extension] = moved_counts.get(extension, 0) + 1

    return moved_counts


if __name__ == '__main__':

    # 以脚本自身所在目录为基准，保证从项目根运行也能正确定位到要整理的目录
    directory = os.path.dirname(os.path.abspath(__file__))

    print(f'即将整理目录：{directory}')
    confirm = input('文件会被移动到以扩展名命名的子文件夹，是否继续？(y/n)：').strip().lower()

    if confirm != 'y':
        print('已取消整理，未做任何改动。')
    else:
        result = organize_folder(directory)

        print('\n' + '=' * 30)
        print('        整理结果汇总')
        print('=' * 30)
        if not result:
            print('目录中没有需要整理的文件。')
        else:
            total = 0
            for extension, count in sorted(result.items()):
                print(f'{extension:<10}{count:>5} 个')
                total += count
            print('-' * 30)
            print(f'{"合计":<10}{total:>5} 个')
        print('=' * 30)
