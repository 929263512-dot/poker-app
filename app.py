import streamlit as st
from treys import Card, Evaluator, Deck
import easyocr
import cv2
import numpy as np
import re
from PIL import Image

# 初始化 OCR 引擎 (仅英文，只识别数字)
@st.cache_resource
def load_ocr_engine():
    return easyocr.Reader(['en'], gpu=False) 

# 定义 standard 的德州代码 (10 写成 T)
CARD_VALUES = {'2','3','4','5','6','7','8','9','T','J','Q','K','A'}
CARD_SUITS = {'s', 'h', 'd', 'c'}

def get_suit_by_color(img_patch):
    """
    根据图片小块的颜色判断花色 (需要根据具体 APP UI 优化)
    简化版：只区分红(h/d) 黑(s/c)
    高级版：通过 HSV 空间区分四个花色
    """
    # 转换为 HSV 颜色空间
    hsv = cv2.cvtColor(img_patch, cv2.COLOR_BGR2HSV)
    
    # 定义 HSV 中的红色、黑色、蓝色(部分APP梅花是蓝色)、绿色范围
    # 注意：这些阈值需要根据特定 APP 的卡牌设计进行微调！
    # 以下为通用参考值
    
    # 红色 (红桃/方块)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    
    # 黑色 (黑桃)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 50])

    # 蓝色 (梅花部分APP设计)
    lower_blue = np.array([100, 150, 0])
    upper_blue = np.array([140, 255, 255])

    # 绿色 (梅花部分APP设计)
    lower_green = np.array([40, 70, 70])
    upper_green = np.array([80, 255, 255])

    # 创建掩膜
    mask_red = cv2.addWeighted(cv2.inRange(hsv, lower_red1, upper_red1), 1.0, 
                              cv2.inRange(hsv, lower_red2, upper_red2), 1.0, 0.0)
    mask_black = cv2.inRange(hsv, lower_black, upper_black)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    # 计算掩膜中非零像素的数量 (颜色面积)
    colors = {
        'h/d (红)': cv2.countNonZero(mask_red),
        's (黑桃)': cv2.countNonZero(mask_black),
        'c (蓝色梅花)': cv2.countNonZero(mask_blue),
        'c (绿色梅花)': cv2.countNonZero(mask_green)
    }
    
    # 找出面积最大的颜色
    most_likely_suit_color = max(colors, key=colors.get)
    
    # 简化版映射：为了精准度，高级定制版需要你校对
    # 目前只区分红黑
    if '红' in most_likely_suit_color:
        return 'h', most_likely_suit_color # 返回猜测的'h' (红桃)，用户需校对方块'd'
    else:
        return 's', most_likely_suit_color # 返回猜测的's' (黑桃)，用户需校对梅花'c'

def advanced_recognize_ggpoker_cards(image_cv, reader):
    """
    高级定制版识别逻辑：OCR读数字 + 颜色检花色
    """
    detected_cards = []
    
    # 替换常见的数字误识别
    replacements = {'10': 'T', 'O': 'Q', 'I': 'J', 'l': 'A', 'A': 'A'}
    
    # ================= 定制版逻辑核心 =================
    # 使用坐标切割 (以下坐标基于标准的 1080p GGPoker 竖屏截图，需要你人工确认符合你的手机)
    # 格式: [y_start : y_end, x_start : x_end]
    
    # 假设底牌区域：[1800:2050, 250:830]
    # 假设公共牌区域：[1000:1300, 50:1030]
    
    # 1. 运行 OCR 识别所有文本 (用于找数字)
    result = reader.readtext(image_cv, detail=1) # detail=1 返回坐标
    
    for (bbox, text_raw, prob) in result:
        text = text_raw.upper().strip()
        
        # 应用替换并清理文本
        text = "".join([replacements.get(c, c) for c in text if replacements.get(c, c) in CARD_VALUES])
        
        # 如果可能是数字 (如 'A', '10', '9')
        if text in CARD_VALUES:
            # 获取文字在图片中的坐标块，去原图中提取颜色
            (tl, tr, br, bl) = bbox
            x_min, y_min = int(tl[0]), int(tl[1])
            x_max, y_max = int(br[0]), int(br[1])
            
            # 为了准确，花色通常在数字的下方或旁边。我们切一个小一点的、包含数字的块来分析颜色。
            card_patch = image_cv[y_min : y_max, x_min : x_max]
            
            if card_patch.size == 0: continue
            
            # 获取颜色
            suit_char, color_name = get_suit_by_color(card_patch)
            
            # 简化版限制：AI无法100%分清红桃/方块，黑桃/梅花。只能分清红黑。
            # 我们填一个最常用的，让用户校对。
            detected_cards.append(f"{text}{suit_char}")
            # st.info(f"AI在文本 '{text_raw}' 处检测到数字 '{text}'，花色颜色偏向 '{color_name}'。")

    return detected_cards

def simulate_equity(hand1_str, hand2_str, board_str=[], iterations=5000):
    """(保持胜率计算逻辑)"""
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        hand2 = [Card.new(c) for c in hand2_str]
        board = [Card.new(c) for c in board_str]
    except Exception as e: return None, None, f"格式错误: {e}"

    deck = Deck()
    for card in hand1 + hand2 + board:
        try: deck.cards.remove(card)
        except ValueError: return None, None, f"输入了重复卡牌: {Card.int_to_str(card)}"

    wins1, wins2, ties = 0, 0, 0
    for i in range(iterations):
        deck = Deck()
        for card in hand1 + hand2 + board: deck.cards.remove(card)
        cards_needed = 5 - len(board)
        simulated_board = board + deck.draw(cards_needed) if cards_needed > 0 else board
        score1 = evaluator.evaluate(simulated_board, hand1)
        score2 = evaluator.evaluate(simulated_board, hand2)
        if score1 < score2: wins1 += 1
        elif score2 < score1: wins2 += 1
        else: ties += 1
    eq1 = (wins1 + 0.5 * ties) / iterations
    eq2 = (wins2 + 0.5 * ties) / iterations
    return eq1, eq2, None

def get_action_advice(equity, rank_strength, street):
    """
    根据胜率、牌力强度和街数给出简单的打法建议
    """
    if street == "翻前":
        if equity > 0.8: return "✅ 翻前超强牌：必须下注/加注 (Raise)。"
        elif equity > 0.6: return "✅ 翻前强牌：下注 (Bet) / 跟注 (Call)。"
        elif equity > 0.4: return "⚠️ 翻前边缘牌：考虑过牌 (Check) / 便宜跟注摊牌。"
        else: return "❌ 翻前弱牌：过牌 (Check) / 弃牌 (Fold)。"

    # 翻后算法：结合胜率 (Equity) 和牌面结构 (rank_strength)
    # rank_strength: 0.0 (最弱高牌) - 1.0 (皇家同花顺)
    
    if rank_strength > 0.95: # 超强牌 (葫芦+)
        return "✅ 超强牌：价值下注 (Value Bet) / 大幅加注 (Raise) 以期打光筹码。"
    elif rank_strength > 0.8: # 强牌 (两对-三条)
        if equity > 0.7: return "✅ 强牌：主动下注 (Bet) / 保护牌力，防止对手听牌。"
        else: return "⚠️ 强牌但听牌严重：跟注 (Call) / 控制底池大小。"
    elif rank_strength > 0.5: # 中等牌 (顶对-超对)
        if equity > 0.5: return "⚠️ 中等牌：价值薄弱，尝试过牌 (Check) 摊牌或便宜跟注。"
        else: return "⚠️ 中等牌且偏弱：过牌 (Check) / 准备弃牌给压力。"
    else: # 弱牌 (中底对-高牌)
        # 听牌逻辑非常复杂， treys并不直接提供。我们这里简化。
        if equity > 0.45: return "⚠️ 弱牌但可能在听牌：过牌 (Check) / 寻求免费看下张牌。"
        else: return "❌ 弱牌：过牌 (Check) / 弃牌 (Fold)。"

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州智能教练", layout="centered")

st.title("📸 德州智能教练 (GGPoker 定制版)")
st.markdown("上传截图自动填牌，秒算胜率，并提供智能打法建议。")
st.markdown("---")

# 初始化 OCR 引擎
reader = load_ocr_engine()
evaluator = Evaluator()

# 初始化 Session State 用于存储卡牌
if 'p1_cards' not in st.session_state: st.session_state['p1_cards'] = "As, 2s"
if 'p2_cards' not in st.session_state: st.session_state['p2_cards'] = "Kh, Kd" # 预设对手一对K用于测试买花
if 'board_cards' not in st.session_state: st.session_state['board_cards'] = "4s, Ks, Th"

# ================= 1. 截图分析区 =================
with st.expander("📷 上传游戏截图自动填牌 (高级定制)", expanded=True):
    st.warning("⚠️ 简化版OCR限制：AI只能精准分清红和黑。AI无法区分红桃/方块，黑桃/梅花。\n\n已为您填入最常用花色，请务必人工校对！(红h=红桃, 红d=方块, 黑s=黑桃, 黑c=梅花)")
    uploaded_file = st.file_uploader("选择牌局截图...", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的截图", use_container_width=True)
        
        if st.button("🔍 智能分析截图", use_container_width=True):
            with st.spinner("魔法进行中，正在深度分析图片..."):
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # 运行高级识别逻辑
                all_detected = advanced_recognize_ggpoker_cards(img_cv, reader)
                
                if not all_detected:
                    st.warning("未能识别到清晰的卡牌，可能坐标偏移或分辨率不符。请手动输入。")
                else:
                    st.success(f"识别到 {len(all_detected)} 张卡牌: {', '.join(all_detected)}")
                    
                    # 为了更无敌，我们可以通过坐标大概把牌分堆
                    # 但在简化版OCR中，我们默认排序分配：前两张为你，余下为公共
                    # 这需要你校对！
                    if len(all_detected) >= 2:
                        st.session_state['p1_cards'] = f"{all_detected[0]}, {all_detected[1]}"
                    if len(all_detected) >= 3:
                        st.session_state['board_cards'] = ", ".join(all_detected[2:])
                    st.info("⚠️ 已将识别结果填入下方输入框，**请务必人工校对格式和花色**后再计算！")

st.markdown("---")

# ================= 2. 卡牌输入与计算区 =================
st.subheader("🃏 手动校对与教练建议")
st.info("💡 格式：Ah, Td, 2c (A-2 + h:红桃, s:黑桃, d:方块, c:梅花。T是10)")

col1, col2 = st.columns(2)
with col1:
    p1_input = st.text_input("你的手牌", key='p1_cards')
with col2:
    p2_input = st.text_input("对手手牌", key='p2_cards')

board_input = st.text_input("公共牌", key='board_cards')

if st.button("⚡ 计算胜率 & 获取建议", type="primary", use_container_width=True):
    # 处理输入格式
    p1_hand = [c.strip() for c in p1_input.split(",") if c.strip()]
    p2_hand = [c.strip() for c in p2_input.split(",") if c.strip()]
    board_cards = [c.strip() for c in board_input.split(",") if c.strip()]

    if len(p1_hand) != 2 or len(p2_hand) != 2:
        st.error("每位玩家必须输入确切的 2 张手牌！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("公共牌数量必须是 0张(翻前), 3张(翻牌), 4张(转牌) 或 5张(河牌)！")
    else:
        with st.spinner("大脑飞速计算中..."):
            eq1, eq2, err = simulate_equity(p1_hand, p2_hand, board_cards, iterations=5000)

            if err:
                st.error(err)
            else:
                st.success("计算完成！")
                st.markdown("### 📊 实时胜率")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="✅ 你的胜率", value=f"{eq1 * 100:.2f}%")
                with res_col2:
                    st.metric(label="⚠️ 对手胜率", value=f"{eq2 * 100:.2f}%")
                
                # 行动建议
                st.markdown("### 🤖 教练建议")
                # 计算当前牌面结构
                if len(board_cards) >= 3:
                    try:
                        hand_for_eval = [Card.new(c) for c in p1_hand + board_cards]
                        rank_strength = evaluator.get_five_card_rank_strength(evaluator.evaluate([Card.new(c) for c in board_cards], [Card.new(c) for c in p1_hand]))
                        street = "翻牌前" if len(board_cards) == 0 else "翻牌后"
                    except Exception: 
                        st.warning("行动建议系统需要手动校对完成后才能提供。")
                        rank_strength, street = 0, "未知"
                else: 
                    rank_strength = 0
                    street = "翻牌前"

                # 翻前建议逻辑 (简化)
                if len(board_cards) == 0: street="翻前"

                # 获取行动建议
                advice = get_action_advice(eq1, rank_strength, street)
                if "✅" in advice: st.success(advice)
                elif "❌" in advice: st.error(advice)
                else: st.warning(advice)
