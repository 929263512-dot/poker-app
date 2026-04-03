import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 核心工具：智能解析与视觉显示 =================
def parse_cards(input_str):
    if not input_str: return []
    s = input_str.upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    return [c[0] + c[1].lower() for c in cards]

def display_poker_icons(card_list):
    if not card_list: return ""
    suits_map = {'s': ('♠️', '#000000'), 'h': ('♥️', '#FF0000'), 'd': ('♦️', '#FF0000'), 'c': ('♣️', '#008000')}
    html_str = ""
    for c in card_list:
        val = c[0].replace('T', '10')
        icon, color = suits_map[c[1]]
        html_str += f"<span style='font-size:24px; font-weight:bold; color:{color}; margin-right:10px;'>{val}{icon}</span>"
    return html_str

# ================= 2. 核心引擎：9人桌盈利推演 =================
def simulate_9_way_equity(hand, board):
    """极速模拟 9 人桌面对随机手牌的胜率"""
    evaluator = Evaluator()
    try:
        h1 = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return 0.0, "解析错误"

    wins = 0
    # 为了手机不卡顿，我们将模拟次数定为 1000 次，足够实战参考
    iterations = 1000 
    for _ in range(iterations):
        deck = Deck()
        try:
            for card in h1 + b: deck.cards.remove(card)
        except: break
        
        # 模拟 8 个对手的随机手牌
        others = [deck.draw(2) for _ in range(8)]
        # 补齐公共牌
        needed = 5 - len(b)
        full_b = b + deck.draw(needed) if needed > 0 else b
        
        my_score = evaluator.evaluate(full_b, h1)
        # 必须比所有对手都强
        if all(evaluator.evaluate(full_b, o) >= my_score for o in others):
            wins += 1
            
    return wins / iterations, None

def get_matrix_advice(hand_str):
    tier_map = {
        'T1 (顶级)': ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo'],
        'T2 (强牌)': ['TT', '99', 'AQs', 'AQo', 'AJs', 'KQs'],
        'T3 (优质)': ['88', '77', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo'],
        'T4 (投机)': ['66', '55', 'A9s', 'A8s', 'KTs', 'QTs', 'T9s', '98s', 'J9s']
    }
    h = "".join(sorted([hand_str[0], hand_str[2]], reverse=True))
    suited = hand_str[1] == hand_str[3]
    h_key = h + ('s' if suited else 'o') if h[0] != h[1] else h
    tier = "T5 (垃圾)"
    for name, cards in tier_map.items():
        if h_key in cards: tier = name
    matrix = {
        "前位 (UTG/MP1)": "🛑 **极紧弃牌**：除 T1 以外全部弃牌。",
        "中位 (MP2/HJ)": "🟡 **稳健过滤**：T1/T2 必打。T3 没人加注可跟。",
        "后位 (CO/BTN)": "💰 **主动剥削**：T1-T4 均可打。抢池主战场！",
        "盲注 (SB/BB)": "🛡️ **防守反击**：位置差，仅用 T1/T2 强反击。"
    }
    return tier, matrix

# ================= 3. UI 界面 =================
st.set_page_config(page_title="德州盈利终端", layout="centered")
st.title("🏆 9人桌盈利决策终端")

# 侧边栏：底池计算细节
with st.sidebar:
    st.header("💵 盈利参数")
    pot = st.number_input("总底池 ($)", 100)
    call_bet = st.number_input("跟注额 ($)", 20)
    st.markdown("---")
    st.write("s=黑桃 | h=红桃 | d=方块 | c=梅花")

# 1. 翻前快速录入
h_raw = st.text_input("🎯 你的底牌 (如 asad)", value="asad").lower()
h_cards = parse_cards(h_raw)
st.markdown(display_poker_icons(h_cards), unsafe_allow_html=True)

if len(h_cards) == 2:
    st.markdown("---")
    tier, matrix = get_matrix_advice(h_cards[0] + h_cards[1])
    st.success(f"### 当前牌力：{tier}")
    for pos, adv in matrix.items():
        with st.expander(f"📍 {pos} 盈利对策", expanded=True):
            st.write(adv)

st.markdown("---")

# 2. 翻后深度计算
b_raw = st.text_input("🌊 公共牌 (连着写)", value="").lower()
b_cards = parse_cards(b_raw)
st.markdown(display_poker_icons(b_cards), unsafe_allow_html=True)

if st.button("⚡ 获取翻后盈利方案", type="primary", use_container_width=True):
    if len(h_cards) != 2:
        st.error("请输入底牌")
    else:
        with st.spinner("🧠 正在模拟 9 人桌 1000 局对抗..."):
            equity, err = simulate_9_way_equity(h_cards, b_cards)
            if err:
                st.error(err)
            else:
                st.success("推演完成！")
                c1, c2 = st.columns(2)
                c1.metric("9人真实胜率", f"{equity*100:.1f}%")
                odds = call_bet / (pot + call_bet) if pot+call_bet > 0 else 0
                c2.metric("保本所需胜率", f"{odds*100:.1f}%")
                
                st.markdown("---")
                if equity > odds * 1.5:
                    st.balloons()
                    st.success("💰 **盈利建议：重磅下注/加注！** 你的牌面在 9 人桌极具统治力。")
                elif equity > odds:
                    st.warning("✅ **盈利建议：跟注看牌。** 胜率超过赔率，长期盈利。")
                else:
                    st.error("❌ **盈利建议：果断弃牌。** 面对 9 人范围，你的赢面不足以支撑成本。")
