import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 初始化卡牌库 =================
def get_card_library():
    ranks = 'AKQJT98765432'
    suits = 'shdc'
    suit_icons = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    # 生成显示用的名字 (如: A♠️) 和 内部代码 (如: As)
    display_list = []
    internal_map = {}
    for r in ranks:
        for s in suits:
            d_name = f"{r.replace('T','10')}{suit_icons[s]}"
            i_code = f"{r}{s}"
            display_list.append(d_name)
            internal_map[d_name] = i_code
    return display_list, internal_map

# ================= 2. 核心计算引擎 =================
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
    # 格式化手牌用于匹配
    r1, s1, r2, s2 = hand_str[0], hand_str[1], hand_str[2], hand_str[3]
    ranks_sorted = "".join(sorted([r1, r2], key=lambda x: '23456789TJQKA'.index(x), reverse=True))
    h_key = ranks_sorted + ('s' if s1 == s2 else 'o') if r1 != r2 else ranks_sorted
    
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
st.set_page_config(page_title="德州智能决策终端", layout="centered")
st.title("🏆 德州盈利决策大师")

display_names, internal_map = get_card_library()

# --- A. 实战参数区 (10单位步长) ---
with st.container(border=True):
    col_p, col_b, col_c = st.columns(3)
    with col_p:
        num_players = st.number_input("桌面人数", 2, 10, 6, step=1)
    with col_b:
        pot_size = st.number_input("总底池 ($)", 0, 100000, 100, step=10)
    with col_c:
        call_amount = st.number_input("需跟注 ($)", 0, 100000, 20, step=10)

st.markdown("---")

# --- B. 核心选择区 (点选模式) ---
st.subheader("🎯 选择你的底牌")
selected_hand = st.multiselect("点击选择 2 张手牌", options=display_names, max_selections=2)
hand_codes = [internal_map[name] for name in selected_hand]

st.subheader("🌊 选择公共牌")
# 自动过滤掉已经选为手牌的卡牌
remaining_cards = [c for c in display_names if c not in selected_hand]
selected_board = st.multiselect("点击选择 0-5 张公共牌", options=remaining_cards, max_selections=5)
board_codes = [internal_map[name] for name in selected_board]

st.markdown("---")

# --- C. 计算与盈利方案 ---
if st.button("⚡ 获取盈利方案", type="primary", use_container_width=True):
    if len(hand_codes) != 2:
        st.error("请先选好 2 张底牌！")
    else:
        with st.spinner("量子计算中..."):
            equity, err = simulate_equity(hand_codes, board_codes, num_players)
            if not err:
                res1, res2, res3 = st.columns(3)
                res1.metric("真实胜率", f"{equity*100:.1f}%")
                odds = call_amount / (pot_size + call_amount) if (pot_size + call_amount) > 0 else 0
                res2.metric("保本线", f"{odds*100:.1f}%")
                ev = (equity * pot_size) - ((1 - equity) * call_amount)
                res3.metric("期望盈利 (EV)", f"{ev:+.1f}")
                
                st.markdown("---")
                if ev > 0:
                    st.success("✅ **盈利动作：跟注/加注。** 长期来看这是赚钱的。")
                else:
                    st.error("❌ **盈利动作：弃牌 (Fold)。** 当前局面不符合盈利数学。")

st.markdown("---")

# --- D. 底部参考矩阵 ---
if len(hand_codes) == 2:
    tier, matrix = get_matrix_advice("".join(hand_codes))
    st.subheader(f"📊 9人桌全位置策略 (牌力: {tier})")
    for pos, adv in matrix.items():
        with st.expander(f"📍 {pos} 对策", expanded=True):
            st.write(adv)

st.caption("提示：在手机上直接点击下拉框选择，比打字快 3 倍。")
