import streamlit as st
from treys import Card, Evaluator, Deck
import easyocr
import cv2
import numpy as np
import re
from PIL import Image

# 初始化 Evaluator 和 OCR 引擎 (缓存 OCR 引擎以提高速度)
@st.cache_resource
def load_ocr_engine():
    # 使用英文识别
    return easyocr.Reader(['en'], gpu=False) 

# 德州扑克卡牌正则匹配
CARD_PATTERN = re.compile(r'([2-9AKQJTakqjt])([hsdcHSDC])')

def parse_cards_from_text(text_list):
    """
    从 OCR 识别出的文本列表中解析出卡牌
    """
    detected_cards = []
    # 替换常见的误识别
    replacements = {'10': 'T', '0': 'Q', 'I': 'J', '1': 'A', '$': 's'}
    
    for text_raw in text_list:
        text = text_raw.upper().strip()
        # 应用替换
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # 匹配 Ah, 2s, Td 这种标准格式
        matches = CARD_PATTERN.findall(text)
        for val, suit in matches:
            detected_cards.append(f"{val}{suit.lower()}")
            
        # 处理可能的“2 黑桃”或者“A 红桃”这种分开识别的情况 (非常复杂，此处简化)

    return detected_cards

def simulate_equity(hand1_str, hand2_str, board_str=[], iterations=5000):
    """(保持原来的胜率计算逻辑)"""
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        hand2 = [Card.new(c) for c in hand2_str]
        board = [Card.new(c) for c in board_str]
    except Exception as e:
        return None, None, f"卡牌输入格式有误，请检查！(错误: {e})"

    deck = Deck()
    for card in hand1 + hand2 + board:
        try:
            deck.cards.remove(card)
        except ValueError:
            return None, None, f"输入了重复的卡牌 ({Card.int_to_str(card)})，请检查！"

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
    total = wins1 + wins2 + ties
    eq1 = (wins1 + 0.5 * ties) / total
    eq2 = (wins2 + 0.5 * ties) / total
    return eq1, eq2, None

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州智能胜率计算器", layout="centered")

st.title("📸 德州智能胜率计算器 (含截图分析)")
st.markdown("上传牌局截图自动填牌，或手动输入，秒算赢面。")
st.markdown("---")

# 初始化 OCR 引擎
reader = load_ocr_engine()

# 初始化 Session State 用于存储识别出的卡牌
if 'p1_cards' not in st.session_state: st.session_state['p1_cards'] = "Ah, Kh"
if 'p2_cards' not in st.session_state: st.session_state['p2_cards'] = "Qs, Qc"
if 'board_cards' not in st.session_state: st.session_state['board_cards'] = ""

# ================= 1. 截图分析区 =================
with st.expander("📷 上传截图自动填牌 (OCR)", expanded=True):
    uploaded_file = st.file_uploader("选择牌局截图...", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        # 显示上传的文件
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的截图", use_container_width=True)
        
        if st.button("🔍 自动分析截图", use_container_width=True):
            with st.spinner("魔法进行中，正在从图片中读取卡牌..."):
                # 将 PIL 图片转换为 OpenCV 格式
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # 运行 OCR
                result = reader.readtext(img_cv, detail=0)
                
                # 解析卡牌
                all_detected = parse_cards_from_text(result)
                
                if not all_detected:
                    st.warning("未能识别到清晰的卡牌，请手动输入或尝试更清晰的截图。")
                else:
                    st.success(f"识别到 {len(all_detected)} 张卡牌: {', '.join(all_detected)}")
                    # 尝试自动分配卡牌 (需要根据具体 APP UI 优化，这里是简化版)
                    # 默认前两张归你，后两张归对手，其余归公共
                    if len(all_detected) >= 2:
                        st.session_state['p1_cards'] = f"{all_detected[0]}, {all_detected[1]}"
                    if len(all_detected) >= 4:
                        st.session_state['p2_cards'] = f"{all_detected[2]}, {all_detected[3]}"
                    if len(all_detected) >= 5:
                        st.session_state['board_cards'] = ", ".join(all_detected[4:])
                    st.info("⚠️ 已将识别结果填入下方输入框，请务必人工校对后再计算！")

st.markdown("---")

# ================= 2. 卡牌输入与计算区 =================
st.subheader("🃏 手动校对与计算")
st.info("💡 格式：Ah, Kh, Qs, Qc, Td, 2c (A-2 + h:红桃, s:黑桃, d:方块, c:梅花)")

col1, col2 = st.columns(2)
with col1:
    p1_input = st.text_input("你的手牌", key='p1_cards')
with col2:
    p2_input = st.text_input("对手手牌", key='p2_cards')

board_input = st.text_input("公共牌 (翻牌/转牌/河牌)", key='board_cards')

if st.button("⚡ 计算实时胜率", type="primary", use_container_width=True):
    # 处理输入格式
    p1_hand = [c.strip() for c in p1_input.split(",") if c.strip()]
    p2_hand = [c.strip() for c in p2_input.split(",") if c.strip()]
    board_cards = [c.strip() for c in board_input.split(",") if c.strip()]

    if len(p1_hand) != 2 or len(p2_hand) != 2:
        st.error("每位玩家必须输入确切的 2 张手牌！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("公共牌数量必须是 0张, 3张, 4张 或 5张！")
    else:
        with st.spinner("大脑飞速计算中..."):
            eq1, eq2, err = simulate_equity(p1_hand, p2_hand, board_cards, iterations=5000)

            if err:
                st.error(err)
            else:
                st.success("计算完成！")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="✅ 你的胜率", value=f"{eq1 * 100:.2f}%")
                with res_col2:
                    st.metric(label="⚠️ 对手胜率", value=f"{eq2 * 100:.2f}%")
