#定义一个函数，该函数接收一个字符串和一个整数作为参数，完成以下操作：

#1.从字符串头部截取指定长度的字符串并翻转
#2.从字符串尾部截取指定长度的字符串并翻转
#3.分别打印头部和尾部翻转后与剩余部分拼接后的新字符串

#定义函数

def rotate_and_contact(s, n):
    """
    该函数接收一个字符串和一个整数作为参数，完成以下操作：
    1.从字符串头部截取指定长度的字符串并翻转
    2.从字符串尾部截取指定长度的字符串并翻转
    3.分别打印头部和尾部翻转后与剩余部分拼接后的新字符串
    :return: None
    """

    #从字符串头部截取指定长度的字符串并翻转

    head = s[:n][::-1]

    #头部剩余部分

    head_remaining = s[n:]

    #头部翻转后与剩余部分拼接后的新字符串

    head_result = head + head_remaining

    #从字符串尾部截取指定长度的字符串并翻转

    tail = s[-n:][::-1]

    #尾部剩余部分

    tail_remaining = s[:-n]

    # 尾部翻转后与剩余部分拼接后的新字符串

    tail_result = tail + tail_remaining

    # 打印结果
    print(head_result)

    print(tail_result)

#调用函数

rotate_and_contact("hello world", 3)