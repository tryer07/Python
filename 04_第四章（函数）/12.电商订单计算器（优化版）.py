def calculate_order_cost(*args, coupon_amount: float = 0.0, score_amount: int = 0, express_fee: float = 0.0) -> float:
    """
    根据传入的商品信息、优惠信息、运费信息计算订单总金额
    :param args: 商品信息，每个元素是 (商品名, 单价, 数量)
    :param coupon_amount: 优惠券金额
    :param score_amount: 积分
    :param express_fee: 运费
    :return: 订单总金额
    """
    # ========== 1. 打印商品清单并计算商品总金额 ==========
    print('\n' + '=' * 45)
    print('商品清单')
    print('=' * 45)
    total_cost = 0.0
    for item_name, item_price, item_qty in args:
        subtotal = item_price * item_qty
        total_cost += subtotal
        print(f'{item_name:<10} 单价：{item_price:>8.2f}  数量：{item_qty:>3}  小计：{subtotal:>10.2f}')
    print(f'\n商品总金额：{total_cost:.2f} 元')

    # ========== 2. 扣减优惠券 ==========
    if total_cost >= 5000:
        actual_coupon = min(coupon_amount, total_cost)  # 优惠金额不能超过商品总价
        total_cost -= actual_coupon
        print(f'优惠券抵扣：-{actual_coupon:.2f} 元')
    else:
        print('商品总金额未满 5000，无法使用优惠券')

    # ========== 3. 扣减积分 ==========
    if total_cost >= 5000:
        usable_score = (score_amount // 100) * 100  # 只取整百部分
        discount = usable_score // 100  # 100 积分 = 1 元
        actual_discount = min(discount, total_cost)  # 抵扣不能超过当前金额
        total_cost -= actual_discount
        print(f'积分抵扣：使用 {usable_score} 积分，抵扣 {actual_discount:.2f} 元')
    else:
        print('商品总金额未满 5000，无法使用积分抵扣')

    # ========== 4. 添加运费 ==========
    total_cost += express_fee
    print(f'运费：+{express_fee:.2f} 元')

    return total_cost


# ============ 交互式录入 ============
if __name__ == '__main__':
    print('=' * 45)
    print('欢迎使用电商订单计算器')
    print('=' * 45)

    goods_list = []
    while True:
        print('\n--- 录入商品（直接回车结束录入）---')
        input_name = input('请输入商品名称：').strip()
        if input_name == '':
            break

        # 安全输入单价
        while True:
            try:
                input_price = float(input(f'请输入「{input_name}」的单价：'))
                if input_price < 0:
                    print('单价不能为负数，请重新输入')
                    continue
                break
            except ValueError:
                print('输入无效，请输入数字')

        # 安全输入数量
        while True:
            try:
                input_qty = int(input(f'请输入「{input_name}」的数量：'))
                if input_qty <= 0:
                    print('数量必须为正整数，请重新输入')
                    continue
                break
            except ValueError:
                print('输入无效，请输入整数')

        goods_list.append((input_name, input_price, input_qty))
        print(f'✓ 已添加：{input_name} × {input_qty}，单价 {input_price:.2f} 元')

    if not goods_list:
        print('\n未录入任何商品，程序结束。')
    else:
        print('\n--- 录入优惠与运费信息（无则输入 0）---')

        # 处理优惠券输入
        try:
            user_coupon = float(input('请输入优惠券金额：'))
        except ValueError:
            user_coupon = 0.0
            print('输入无效，默认按 0 处理')

        # 处理积分输入
        try:
            user_score = int(input('请输入积分：'))
        except ValueError:
            user_score = 0
            print('输入无效，默认按 0 处理')

        # 处理运费输入
        try:
            user_express = float(input('请输入运费：'))
        except ValueError:
            user_express = 0.0
            print('输入无效，默认按 0 处理')

        # 调用函数计算
        total = calculate_order_cost(
            *goods_list,
            coupon_amount=user_coupon,
            score_amount=user_score,
            express_fee=user_express
        )

        print('\n' + '=' * 45)
        print(f'订单总金额：{total:.2f} 元')
        print('=' * 45)