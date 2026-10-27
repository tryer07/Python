# 统计英文文章（english_article.txt）中每个单词出现的次数，并输出出现次数最多的前 10 个单词
# 实现的内容：
# 1. 文件读取：with open 以 utf-8 编码打开，逐行遍历；用切片/strip 去除每行末尾换行符与多余空白
# 2. 分词：对每行调用字符串 split()，按默认空白字符（空格、制表符等）拆分为单词列表
# 3. 计数：定义字典存储"单词-次数"映射，遍历时判断键是否存在
#    不存在则初始化为 1（首次出现即代表已出现一次，而非 0），存在则累加
# 4. 排序：对 dict.items() 调用 sorted()，用 lambda 指定按次数（索引 1）降序（reverse=True）
# 5. Top10：对排序结果做列表切片 [:10]，输出高频单词及其频次，完成数据分析闭环

import os
import string


def count_words(file_path):

    """
    逐行读取英文文本，统计每个单词出现的次数
    :param file_path: 英文文章文件路径
    :return: 字典，键为单词（小写、去标点），值为出现次数
    """

    word_counts = {}

    with open(file_path, 'r', encoding='utf-8') as file:
        # 逐行遍历文件
        for line in file:
            # 切片去除行首尾空白（含换行符），保证后续分割逻辑准确
            line = line.strip()
            if not line:
                continue
            # split() 不传参数时按任意空白字符分割，自动处理空格与制表符
            for word in line.split():
                # 去掉单词两端标点并统一小写，避免 "world," 与 "world" 被当作两个词
                word = word.strip(string.punctuation).lower()
                if not word:
                    continue
                # 键不存在则初始化为 1（首次出现即计一次），存在则累加
                if word not in word_counts:
                    word_counts[word] = 1
                else:
                    word_counts[word] += 1

    return word_counts


if __name__ == '__main__':

    # 以脚本自身所在目录为基准拼接路径，保证从项目根运行也能正确找到数据文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'english_article.txt')

    counts = count_words(file_path)

    # items() 取出键值对，lambda 按次数（x[1]）降序排列
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    # 列表切片截取出现次数最多的前 10 个单词
    top10 = ranked[:10]

    print('=' * 30)
    print('        单词出现次数排行（Top 10）')
    print('=' * 30)
    print(f'{"排名":<4}{"单词":<14}{"次数":>5}')
    print('-' * 30)
    for rank, (word, times) in enumerate(top10, start=1):
        print(f'{rank:<4}{word:<14}{times:>5}')
    print('=' * 30)
