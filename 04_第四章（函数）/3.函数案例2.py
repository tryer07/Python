#案例3：定义一个函数，计算传入的班级学员的高考成绩统计最高分最低分和平均分(保留一位小数)，并返回

def calculate_score(score_list):
    """
    根据传入的班级学员的高考成绩统计最高分最低分和平均分(保留一位小数)，并返回
    :param score_list: 分数列表
    :return:最高分，最低分，平均分
    """
    max_s = max(score_list)
    min_s = min(score_list)
    avg_s = round(sum(score_list) / len(score_list),1)
    return max_s, min_s, avg_s

s_list = [554,579,566,431,398,607,621,666]
max_score, min_score, avg_score = calculate_score(s_list)
print('最高分：',max_score)
print('最低分：',min_score)
print('平均分：',avg_score)

