import streamlit as st
from treys import Card, Evaluator, Deck
import easyocr
import cv2
import numpy as np
import re
from PIL import Image

# 初始化 OCR 引擎
@st.cache_resource
def load_ocr_engine():
    return easyocr.Reader(['en'], gpu=False) 

CARD_VALUES = {'2','3','4','5','6','7','8','9','T','J','Q','K','A'}

def get_suit_by_color(img_patch):
    hsv = cv2.cvtColor(img_patch, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 50])

    mask_red = cv2.addWeighted(cv2.inRange(hsv, lower_red1, upper_red1), 1.0, cv2.inRange(hsv, lower_red2, upper_red2), 1.0, 0.0)
    mask_black = cv2.inRange(hsv, lower_black, upper_black)

    colors = {'h/d (红)': cv2.countNonZero(mask_red), 's/c (黑)': cv2.countNonZero(mask_black)}
    suit_color = max(colors, key=colors.get)
    return 'h' if '红' in suit_color else 's', suit_color

def advanced_recognize_cards(image_cv, reader):
    detected_cards = []
    replacements = {'10': 'T', 'O': 'Q', 'I': 'J', 'l': 'A', 'A': 'A'}
    
    try:
        result = reader.readtext(image_cv, detail=1)
        for (bbox, text_raw, prob) in result:
            text = text_raw.upper().strip()
            text = "".join([replacements.get(c, c) for c in text if replacements.get(c, c) in CARD_VALUES])
            
            if text in CARD_VALUES:
                (tl, tr, br, bl) = bbox
                x_min, y_min = max(0, int(tl[0])), max(0, int(tl[1]))
                x_max, y_max = int(br[0]), int(br[1])
                card_patch = image_cv[y_min:y_max, x_min:x_max]
                if card_patch.size == 0: continue
                suit_char, _ = get_suit_by_color(card_patch)
                detected_cards.append(f"{text}{suit_char}")
    except Exception as e:
        pass # 忽略图像识别的严重报错，交由人工处理
    return list(dict.fromkeys(detected_cards)) # 去重

def simulate_equity(hand1_str, hand2_str, board_str=[], iterations=5000):
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        # 判断对手手牌是否已知
        hand2_known = len(hand2_str) == 2
        hand2 = [Card.new(c) for c in hand2_str] if hand2_known else []
        board = [Card.new(c) for c in board_str]
    except Exception as e: 
        return None, None, f"格式错误，请检查大写和小写字母: {e}"

    wins1, wins2, ties = 0, 0, 0
    for i in range(iterations):
        deck = Deck()
        try:
            for card in hand1 + hand2 + board: deck.cards.remove(card)
        except ValueError: 
            return None, None, "输入了重复卡牌！"

        # 如果对手手牌未知，则每次模拟随机发两张牌给他
        sim_hand2 = hand2 if hand2_known else deck.draw(2)
        
        cards_needed = 5 - len(board)
        simulated_board = board + deck.draw(cards_needed) if cards_needed > 0 else board
        
        score1 = evaluator.evaluate(simulated_board, hand1)
        score2 = evaluator.evaluate(simulated_board, sim_hand2)
        
        if score1 < score2: wins1 += 1
        elif score2 < score1: wins2 += 1
        else: ties += 1
        
    eq1 = (wins1 + 0.5 * ties) / iterations
    eq2 = (wins2 + 0.5 * ties) / iterations
    return eq1, eq2, None

def get_action_advice(equity, street):
    if street == "翻牌前":
        if equity > 0.65: return "🔥 超强底牌：大胆加注 (Raise)！"
        elif equity > 0.55: return "✅ 优质底牌：适合入池 (Call/Bet)。"
        else: return "⚠️ 边缘或垃圾牌：建议弃牌 (Fold)，除非你在大盲位免费看牌。"

    # 翻后赔率教练
    advice = f"💡 **底池赔率指导**：你的实战赢面约为 **{equity*100:.1f}%**。\n\n"
    if equity > 0.8:
        advice += "📈 绝对优势！你应该**主动下注或加注**，争取赢下更多筹码。"
    elif equity > 0.5:
        advice += "⚔️ 略占优势。可以尝试**价值下注**，如果对手猛烈反击，需警惕对手是在买花/买顺。"
    elif equity > 0.2:
        advice += "🛡️ 你落后了（可能是听牌）。**只在跟注代价很小的情况下才跟注**。如果对手下注超过底池的 1/2，建议弃牌。"
    else:
        advice += "❌ 胜率渺茫。赶紧跑！**果断弃牌 (Fold)**。"
    return advice

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州智能教练 究极版", layout="centered")

st.title("🛡️ 德州智能教练 (实战究极版)")
st.markdown("对手手牌可留空！系统将自动模拟面对**全范围未知底牌**的真实胜率。")
st.markdown("---")

reader = load_ocr_engine()

if 'p1_cards' not in st.session_state: st.session_state['p1_cards'] = "As, 2s"
if 'p2_cards' not in st.session_state: st.session_state['p2_cards'] = "" # 默认留空，测试未知对手
if 'board_cards' not in st.session_state: st.session_state['board_cards'] = "4s, Ks, Th"

with st.expander("📷 上传游戏截图自动填牌 (OCR)", expanded=True):
    uploaded_file = st.file_uploader("支持截图辅助识别 (需人工校对花色)", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的截图", use_container_width=True)
        if st.button("🔍 智能分析截图", use_container_width=True):
            with st.spinner("视觉神经元正在提取牌面..."):
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                all_detected = advanced_recognize_cards(img_cv, reader)
                
                if not all_detected:
                    st.warning("识别失败，请直接在下方手动输入。")
                else:
                    st.success(f"侦测到卡牌: {', '.join(all_detected)}")
                    if len(all_detected) >= 2:
                        st.session_state['p1_cards'] = f"{all_detected[0]}, {all_detected[1]}"
                    if len(all_detected) >= 3:
                        st.session_state['board_cards'] = ", ".join(all_detected[2:])
                    st.session_state['p2_cards'] = "" # 清空对手牌，准备测算综合胜率
                    st.info("⚠️ 请校对下方输入框！确认无误后点击计算。")

st.markdown("---")
st.subheader("🃏 手牌库")

col1, col2 = st.columns(2)
with col1:
    p1_input = st.text_input("🎯 你的手牌 (必须2张)", key='p1_cards')
with col2:
    p2_input = st.text_input("❓ 对手手牌 (未知请留空)", key='p2_cards', placeholder="留空则模拟随机手牌")

board_input = st.text_input("🌊 公共牌 (0, 3, 4, 5张)", key='board_cards')

if st.button("⚡ 计算实战综合胜率", type="primary", use_container_width=True):
    p1_hand = [c.strip() for c in p1_input.split(",") if c.strip()]
    p2_hand = [c.strip() for c in p2_input.split(",") if c.strip()]
    board_cards = [c.strip() for c in board_input.split(",") if c.strip()]

    if len(p1_hand) != 2:
        st.error("你必须输入自己的2张底牌！")
    elif len(p2_hand) not in [0, 2]:
        st.error("对手手牌必须是2张，或者直接留空！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("公共牌数量不对！")
    else:
        with st.spinner("量子大脑模拟中... (进行5000次平行宇宙推演)"):
            eq1, eq2, err = simulate_equity(p1_hand, p2_hand, board_cards, iterations=5000)

            if err:
                st.error(err)
            else:
                st.success("推演完成！")
                st.markdown("### 📊 实战胜率")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="✅ 你的预期胜率", value=f"{eq1 * 100:.2f}%")
                with res_col2:
                    label_text = "⚠️ 随机范围胜率" if len(p2_hand) == 0 else "⚠️ 对手胜率"
                    st.metric(label=label_text, value=f"{eq2 * 100:.2f}%")
                
                street = "翻牌前" if len(board_cards) == 0 else "翻牌后"
                st.markdown("### 🤖 战术板")
                st.info(get_action_advice(eq1, street))
