#案例二(电商订单计算器)

#目标：定义一个函数，根据传入的商品信息(商品名、数量、价格)、优惠信息(优惠券、积分抵扣)、运费信息计算订单总金额

#优惠券详情说明：金额满5000及以上可使用，优惠金额不能超过商品总价
#积分抵扣详情说明：金额满5000及以上可使用，100积分优惠1元，优惠金额不能超过商品总价(积分只能整百抵扣)

def calculate_order_cost(*args,coupon = 0,score = 0,express = 0.0):
    """
    根据传入的商品信息(商品名、数量、价格)、优惠信息(优惠券、积分抵扣)、运费信息计算订单总金额
    :param args:商品信息(商品名、数量、价格) ----->如：("鼠标",188,2)
    :param coupon:优惠信息(优惠券)
    :param score:优惠信息(积分抵扣)
    :param express:运费信息
    :return:返回订单总金额
    """
    #订单总金额 = 商品总金额 - 优惠券 - 积分抵扣 + 运费

    #1.计算商品总金额

    total_price = [goods[1] * goods[2] for goods in args]
    total_cost = sum(total_price)

    #2.扣减优惠券

    if total_cost >= 5000 and coupon < total_cost:
        total_cost -= coupon

    #3.扣减积分抵扣

    if total_cost >= 5000 and score // 100 < total_cost:
        total_cost -= score // 100

    #4.添加运费

    total_cost += express

    return total_cost

#测试

#情况一(优惠券和积分生效)

total1 = calculate_order_cost(('鼠标',188,2),('键盘',388,10),('手机',3888,1),coupon = 10,score = 4000,express = 9.9)
print(total1)

#情况二(优惠券和积分生效)

total2 = calculate_order_cost(('鼠标',188,1),('键盘',388,1),('手机',3888,1),coupon = 10,score = 4000,express = 9.9)
print(total2)