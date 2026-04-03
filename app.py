import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 初始化卡牌库 =================
def get_card_library():
    ranks = 'AKQJT98765432'
    suits = 'shdc'
    suit_icons = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    display_list, internal_map = [], {}
    for r in ranks:
        for s in suits:
            d_name = f"{r.replace('T','10')}{suit_icons[s]}"
            display_list.append(d_name)
            internal_map[d_name] = f"{r}{s}"
    return display_list, internal_map

# ================= 2. 核心计算引擎 =================
def simulate_equity(hand, board, num_players):
    evaluator = Evaluator()
    try:
        h1 = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return 0.0, "解析错误"
    wins, iterations = 0, 1000 
    for _ in range(iterations):
        deck = Deck()
        try:
            for card in h1 + b: deck.cards.remove(card)
        except: break
        others = [deck.draw(2) for _ in range(num_players - 1)]
        full_b = b + deck.draw(5-len(b)) if len(b)<5 else b
        my_score = evaluator.evaluate(full_b, h1)
        if all(evaluator.evaluate(full_b, o) >= my_score for o in others): wins += 1
    return wins / iterations, None

# ================= 3. UI 界面布局优化 =================
st.set_page_config(page_title="极简德州大师", layout="centered")

# A. 顶部极简参数 (横向排开)
col1, col2, col3 = st.columns(3)
with col1:
    num_p = st.number_input("人数", 2, 10, 6, step=1)
with col2:
    pot = st.number_input("底池", 0, 10000, 100, step=10)
with col3:
    call = st.number_input("跟注", 0, 10000, 20, step=10)

display_names, internal_map = get_card_library()

# B. 折叠式卡牌选择器 (节省垂直空间)
with st.expander("🎯 点击选择手牌", expanded=True):
    selected_hand = st.pills("手牌", options=display_names, selection_mode="multi", label_visibility="collapsed")
    hand_codes = [internal_map[name] for name in selected_hand] if selected_hand else []
    if len(hand_codes) > 2: st.warning("仅限2张")

with st.expander("🌊 点击选择公共牌", expanded=False):
    remaining = [c for c in display_names if c not in (selected_hand or [])]
    selected_board = st.pills("公共牌", options=remaining, selection_mode="multi", label_visibility="collapsed")
    board_codes = [internal_map[name] for name in selected_board] if selected_board else []
    if len(board_codes) > 5: st.warning("仅限5张")

# C. 计算与紧凑结果
if st.button("⚡ 获取方案", type="primary", use_container_width=True):
    if len(hand_codes) == 2:
        equity, _ = simulate_equity(hand_codes, board_codes, num_p)
        res1, res2, res3 = st.columns(3)
        res1.metric("胜率", f"{equity*100:.1f}%")
        odds = call / (pot + call) if (pot + call) > 0 else 0
        res2.metric("保本", f"{odds*100:.1f}%")
        ev = (equity * pot) - ((1 - equity) * call)
        res3.metric("EV", f"{ev:+.1f}")
        
        if ev > 0: st.success("✅ 跟注/加注")
        else: st.error("❌ 弃牌 (Fold)")

# D. 底部对策矩阵 (默认折叠)
if len(hand_codes) == 2:
    with st.expander("📊 查看全位置策略矩阵", expanded=False):
        st.write("前位: 极紧弃牌 | 中位: 稳健过滤 | 后位: 主动剥削 | 盲注: 防守反击")
