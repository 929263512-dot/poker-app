import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 工具函数：解析与显示 =================
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

# ================= 2. 计算引擎：动态模拟 =================
def simulate_equity(hand, board, num_players):
    evaluator = Evaluator()
    try:
        h1 = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return 0.0, "解析错误"
    wins = 0
    iterations = 1200 
    for _ in range(iterations):
        deck = Deck()
        try:
            for card in h1 + b: deck.cards.remove(card)
        except: break
        others = [deck.draw(2) for _ in range(num_players - 1)]
        needed = 5 - len(b)
        full_b = b + deck.draw(needed) if needed > 0 else b
        my_score = evaluator.evaluate(full_b, h1)
        if all(evaluator.evaluate(full_b, o) >= my_score for o in others): wins += 1
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

# ================= 3. UI 界面布局 =================
st.set_page_config(page_title="德州盈利终端", layout="centered")

# 1. 顶部参考栏
st.markdown("""
<div style="background-color:#f0f2f6; padding:5px; border-radius:5px; text-align:center; font-size:12px; color:#666;">
    s=黑桃♠️ | h=红桃♥️ | d=方块♦️ | c=梅花♣️
</div>
""", unsafe_allow_html=True)

st.title("🏆 德州盈利决策大师")

# 2. 核心参数区 (置顶)
with st.container(border=True):
    col_p, col_b, col_c = st.columns(3)
    with col_p:
        num_players = st.number_input("桌面剩余人数", 2, 10, 6)
    with col_b:
        pot_size = st.number_input("总底池 ($)", 0, 100000, 100)
    with col_c:
        call_amount = st.number_input("需跟注 ($)", 0, 100000, 20)

st.markdown("---")

# 3. 输入与计算区
h_raw = st.text_input("🎯 你的底牌 (如 asad)", value="asad").lower()
h_cards = parse_cards(h_raw)
st.markdown(display_poker_icons(h_cards), unsafe_allow_html=True)

b_raw = st.text_input("🌊 公共牌 (翻后录入)", value="").lower()
b_cards = parse_cards(b_raw)
st.markdown(display_poker_icons(b_cards), unsafe_allow_html=True)

if st.button("⚡ 获取盈利方案", type="primary", use_container_width=True):
    if len(h_cards) == 2:
        with st.spinner("计算中..."):
            equity, err = simulate_equity(h_cards, b_cards, num_players)
            if not err:
                res1, res2, res3 = st.columns(3)
                res1.metric("胜率", f"{equity*100:.1f}%")
                odds = call_amount / (pot_size + call_amount) if (pot_size + call_amount) > 0 else 0
                res2.metric("保本线", f"{odds*100:.1f}%")
                ev = (equity * pot_size) - ((1 - equity) * call_amount)
                res3.metric("期望盈利", f"{ev:+.1f}")
                
                if ev > 0: st.success("✅ **盈利动作：跟注/加注。** 长期来看这是赚钱的。")
                else: st.error("❌ **盈利动作：弃牌。** 期望盈利为负，别送钱。")

st.markdown("---")

# 4. 位置信息区 (置于最后面)
if len(h_cards) == 2:
    tier, matrix = get_matrix_advice(h_cards[0] + h_cards[1])
    st.subheader(f"📊 9人桌全位置策略 (牌力: {tier})")
    for pos, adv in matrix.items():
        with st.expander(f"📍 {pos} 对策", expanded=True):
            st.write(adv)

# 位置图参考
st.caption("实战位置参考图")

