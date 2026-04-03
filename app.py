import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 核心逻辑：智能解析与可视化 =================

def parse_cards(input_str):
    """超级宽容的智能输入解析器：无视空格、逗号、大小写，支持10和T"""
    if not input_str: return []
    # 统一变大写，把 10 替换成 T，去掉所有空格和标点
    s = input_str.upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    
    # 用正则抓取所有有效的卡牌组合 (如 AS, 2H, TD)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    # 转换回 Treys 需要的标准格式 (首字母大写，花色小写，如 As)
    return [c[0] + c[1].lower() for c in cards]

def display_cards(card_list):
    """将英文代码转化为漂亮的中文扑克牌显示"""
    suits_map = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    visual_cards = []
    for c in card_list:
        val = c[0].replace('T', '10')
        suit = suits_map[c[1]]
        visual_cards.append(f"**{val}{suit}**")
    return " ".join(visual_cards) if visual_cards else "等待输入..."

# ================= 核心逻辑：胜率引擎 =================

def simulate_equity(hand1_str, hand2_str, board_str, iterations=5000):
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        hand2_known = len(hand2_str) == 2
        hand2 = [Card.new(c) for c in hand2_str] if hand2_known else []
        board = [Card.new(c) for c in board_str]
    except Exception as e:
        return None, None, f"卡牌解析异常，请检查输入！"

    wins1, wins2, ties = 0, 0, 0
    for _ in range(iterations):
        deck = Deck()
        try:
            for card in hand1 + hand2 + board:
                deck.cards.remove(card)
        except ValueError:
            return None, None, "发现重复的卡牌，请检查！"

        sim_hand2 = hand2 if hand2_known else deck.draw(2)
        cards_needed = 5 - len(board)
        simulated_board = board + deck.draw(cards_needed) if cards_needed > 0 else board

        score1 = evaluator.evaluate(simulated_board, hand1)
        score2 = evaluator.evaluate(simulated_board, sim_hand2)

        if score1 < score2: wins1 += 1
        elif score2 < score1: wins2 += 1
        else: ties += 1

    total = wins1 + wins2 + ties
    return wins1 / total, wins2 / total, None

def get_pro_advice(equity, street):
    if street == "翻牌前":
        if equity > 0.65: return "🚀 **重拳出击**：你的底牌极强，必须主动加注 (Raise) 建立底池！"
        elif equity > 0.55: return "⚔️ **稳健入池**：牌力不错，适合跟注 (Call) 或做小额加注。"
        elif equity > 0.45: return "🛡️ **谨慎防守**：边缘牌，只在位置好或前置位没人加注时才看牌。"
        else: return "🗑️ **果断丢弃**：别抱幻想，立刻弃牌 (Fold)，省下记分牌。"

    # 翻后赔率教练
    advice = f"💡 **行动指南** (当前实战胜率 **{equity*100:.1f}%**)：\n\n"
    if equity > 0.85:
        advice += "👑 **绝对碾压**：你在场上是霸主！尽情下注，甚至可以稍微示弱引诱对手诈唬你。"
    elif equity > 0.65:
        advice += "🔥 **强势领跑**：优势很大，应进行**价值下注** (打半个到一个底池)，不给对手免费买牌的机会。"
    elif equity > 0.35:
        advice += "⚖️ **势均力敌 / 强力听牌**：大概率在买花或买顺。**如果对手下注不大，可以跟注看牌**；如果对手全下，计算你的赔率是否划算。"
    else:
        advice += "🛑 **严重落后**：对方大概率已经击中强牌。除非你能免费看牌，否则面对任何下注都应该**立刻弃牌 (Fold)**。"
    return advice

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州胜率大师", layout="centered")

st.title("🃏 德州胜率大师 (极简终极版)")
st.markdown("不用打逗号，不分大小写！直接输入 `as2s` 或 `10hkd`，闭着眼也能算胜率。")
st.markdown("---")

# UI 输入区
col1, col2 = st.columns(2)
with col1:
    p1_raw = st.text_input("🎯 你的底牌 (如: as2s)", value="")
    p1_cards = parse_cards(p1_raw)
    st.markdown(f"识别结果: {display_cards(p1_cards)}")

with col2:
    p2_raw = st.text_input("❓ 对手底牌 (未知请留空)", value="")
    p2_cards = parse_cards(p2_raw)
    st.markdown(f"识别结果: {display_cards(p2_cards)}")

st.markdown("<br>", unsafe_allow_html=True)

board_raw = st.text_input("🌊 公共牌 (连着打, 如: 4sks10h)", value="")
board_cards = parse_cards(board_raw)
st.markdown(f"识别结果: {display_cards(board_cards)}")

st.markdown("---")

# 计算按钮
if st.button("⚡ 一键计算赢面", type="primary", use_container_width=True):
    if len(p1_cards) != 2:
        st.error("❌ 你的底牌必须是 2 张！(比如打: a s 2 s)")
    elif len(p2_cards) not in [0, 2]:
        st.error("❌ 对手底牌必须是 2 张，或者直接清空留白！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("❌ 公共牌只能是 0张(翻前), 3张(翻牌), 4张 或 5张！")
    else:
        with st.spinner("🧠 职业选手大脑运转中 (蒙特卡洛 5000 次推演)..."):
            eq1, eq2, err = simulate_equity(p1_cards, p2_cards, board_cards)

            if err:
                st.error(f"❌ {err}")
            else:
                st.success("✅ 推演完成！")
                
                # 美化胜率显示
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="🎯 你的胜率", value=f"{eq1 * 100:.1f}%")
                with res_col2:
                    label_text = "🌪️ 范围胜率 (未知对手)" if len(p2_cards) == 0 else "😈 对手胜率"
                    st.metric(label=label_text, value=f"{eq2 * 100:.1f}%")
                
                # 教练建议
                street = "翻牌前" if len(board_cards) == 0 else "翻牌后"
                st.info(get_pro_advice(eq1, street))
