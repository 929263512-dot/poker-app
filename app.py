import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 核心库与工具 =================
def get_card_library():
    ranks, suits = 'AKQJT98765432', 'shdc'
    icons = {'s':'♠️', 'h':'♥️', 'd':'♦️', 'c':'♣️'}
    display, mapping = [], {}
    for r in ranks:
        for s in suits:
            name = f"{r.replace('T','10')}{icons[s]}"
            display.append(name)
            mapping[name] = f"{r}{s}"
    return display, mapping

def simulate_equity(hand, board, num_p):
    evaluator = Evaluator()
    try:
        h1 = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return 0.0
    wins, iters = 0, 1000
    for _ in range(iters):
        deck = Deck()
        try:
            for c in h1 + b: deck.cards.remove(c)
        except: break
        others = [deck.draw(2) for _ in range(num_p - 1)]
        full_b = b + deck.draw(5-len(b)) if len(b)<5 else b
        score = evaluator.evaluate(full_b, h1)
        if all(evaluator.evaluate(full_b, o) >= score for o in others): wins += 1
    return wins / iters

# ================= 2. 剥削建议逻辑 (盈利核心) =================
def get_exploit_advice(h_codes, pos, opp_type, equity, odds):
    # 手牌等级
    r = "".join(sorted([h_codes[0], h_codes[2]], key=lambda x: '23456789TJQKA'.index(x), reverse=True))
    suited = h_codes[1] == h_codes[3]
    h_key = r + ('s' if suited else 'o') if r[0] != r[1] else r
    
    # 盈利动作
    ev_margin = equity - odds
    
    if ev_margin <= 0.05 and ev_margin > 0:
        return "⚠️ **鸡肋局：弃牌。** 虽然数学微弱盈利，但考虑抽水和波动，这种边缘牌是输钱的源头。", "error"
    
    if "疯子" in opp_type:
        if equity > 0.35: return "🌪️ **剥削疯子：跟注/陷阱。** 让他自己表演，你只需在河牌收割。", "success"
        return "🛑 **弃牌。** 别和疯子硬碰硬，等他送死。", "error"
    
    if "紧逼" in opp_type:
        if equity > 0.7: return "🪨 **硬碰硬：加注。** 他有牌，但你更强，狠狠收割他的价值。", "success"
        return "🚨 **绝对弃牌！** 他这种人动钱必有大牌，你的 AA 可能已经落后了。", "error"

    if equity > odds * 1.5: return "🚀 **重炮价值：加注。** 别给对手免费看牌的机会，收割！", "success"
    if equity > odds: return "✅ **稳健跟注。** 概率支持你继续，但不要造大底池。", "warning"
    return "❌ **果断弃牌。** 9人桌最盈利的动作就是 Fold。", "error"

# ================= 3. 极简 UI 布局 =================
st.set_page_config(page_title="盈利终端 2.0", layout="centered")

# A. 顶部极简参数 (紧凑布局)
st.caption("s=黑桃 | h=红桃 | d=方块 | c=梅花")
c1, c2, c3 = st.columns(3)
with c1: num_p = st.number_input("人数", 2, 10, 9)
with c2: pot = st.number_input("总池", 0, 10000, 100, step=10)
with c3: call = st.number_input("需跟", 0, 10000, 20, step=10)

opp_type = st.pills("对手是谁？", ["普通", "疯子(松凶)", "紧逼(老石头)", "跟注站(鱼)"], label_visibility="collapsed") or "普通"

display_names, internal_map = get_card_library()

# B. 选择器 (省空间)
with st.expander("🎯 选牌器 (点开即选)", expanded=True):
    h_select = st.pills("手牌", display_names, selection_mode="multi", label_visibility="collapsed")
    b_select = st.pills("公牌", [c for c in display_names if c not in (h_select or [])], selection_mode="multi", label_visibility="collapsed")

h_codes = [internal_map[n] for n in h_select] if h_select else []
b_codes = [internal_map[n] for n in b_select] if b_select else []

# C. 位置锁定 (盈利开关)
pos = st.segmented_control("你的位置", ["前位(UTG)", "中位(MP)", "后位(BTN)", "盲注"], default="前位(UTG)")

# D. 深度计算
if st.button("⚡ 获取剥削建议", type="primary", use_container_width=True):
    if len(h_codes) == 2:
        equity = simulate_equity(h_codes, b_codes, num_p)
        odds = call / (pot + call) if pot+call > 0 else 0
        
        # UI 结果显示
        st.markdown(f"胜率: **{equity*100:.1f}%** | 保本: **{odds*100:.1f}%**")
        
        advice, color = get_exploit_advice(h_codes, pos, opp_type, equity, odds)
        
        if color == "success": st.success(advice)
        elif color == "warning": st.warning(advice)
        else: st.error(advice)

st.markdown("---")
st.caption("盈利秘籍：9人桌绝大部分时间应该在 Fold。只打 1.5 倍赔率以上的优势局。")
