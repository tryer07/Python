#案例尝试2

#合并两个列表中的元素并去重
# num_list1 = [19,23,56,77,88,91,57,36]
# num_list2 = [19,24,57,99,96,58,31,24]
#
# for num in num_list2:
#     num_list1.append(num)
#
# print('合并后的原始列表:',num_list1)
#
# new_list = []
#
# for num in num_list1:
#     if num not in new_list: #判断元素是否处于新的list中
#         new_list.append(num)

#
# new_list.sort()
# print('去重后的合并列表：',new_list)

#案例尝试2(简化版本)
# num_list1 = [19,23,56,77,88,91,57,36]
# num_list2 = [19,24,57,99,96,58,31,24]
#
# num_list = [*num_list1, *num_list2] #利用了解包和组包的写法省略了for语句的使用
# print('合并后的原始列表：',num_list)
#
# new_list1 = []
#
# for num in num_list:
#     if num not in new_list1: #判断元素是否处于新的list中
#         new_list1.append(num)
#
#
# new_list1.sort()
# print('去重后的合并列表：',new_list1)

#案例尝试2(再简化版本)
num_list1 = [19,23,56,77,88,91,57,36]
num_list2 = [19,24,57,99,96,58,31,24]

new_list = num_list1 + num_list2
print('合并后的原始列表：',new_list)

new_list1 = []
for num in new_list:
    if num not in new_list1:
        new_list1.append(num)


new_list1.sort()
print('去重后的合并列表',new_list1)