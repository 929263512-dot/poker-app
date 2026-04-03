import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 核心逻辑：9人桌位置与牌力评级 =================
def get_position_strategy(hand_str, pos):
    """基于位置的盈利过滤逻辑"""
    tier_map = {
        'T1 (极强)': ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo'],
        'T2 (强牌)': ['TT', '99', 'AQs', 'AQo', 'AJs', 'KQs'],
        'T3 (优质)': ['88', '77', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo']
    }
    
    # 简单的牌型提取逻辑
    h = "".join(sorted([hand_str[0], hand_str[2]], reverse=True))
    suited = hand_str[1] == hand_str[3]
    h_key = h + ('s' if suited else 'o') if h[0] != h[1] else h
    
    curr_tier = "T4 (边缘/垃圾)"
    for name, cards in tier_map.items():
        if h_key in cards: curr_tier = name
        
    # 位置对策
    advice = ""
    if pos in ["UTG (枪口位)", "UTG+1", "MP1"]: # 前位
        if "T1" in curr_tier: advice = "🔥 盈利动作：前位强力加注 (Raise)。你是桌上的领头羊。"
        else: advice = "🛑 盈利动作：弃牌 (Fold)。前位玩弱牌是 9 人桌亏损的最大原因。"
    elif pos in ["BTN (按钮位)", "CO (关位)"]: # 后位
        if "T4" not in curr_tier: advice = "💰 盈利动作：偷池/加注。利用位置优势剥削前位。"
        else: advice = "⚠️ 盈利动作：若前面没人打钱，可以尝试偷池；有人打钱则弃牌。"
    else: # 盲注位
        advice = "🛡️ 盈利动作：防守为主。除非牌力 T2 以上，否则不要轻易反击。"
        
    return curr_tier, advice

# ================= 2. 核心逻辑：多路底池模拟 (9人) =================
def simulate_multi_equity(hand, board, num_players=9):
    evaluator = Evaluator()
    h = [Card.new(c) for c in hand]
    b = [Card.new(c) for c in board]
    wins = 0
    sim_count = 2000
    for _ in range(sim_count):
        deck = Deck()
        try:
            for c in h + b: deck.cards.remove(c)
        except: break
        # 为其他 8 个对手发牌
        others = [deck.draw(2) for _ in range(num_players - 1)]
        full_b = b + deck.draw(5-len(b)) if len(b)<5 else b
        my_s = evaluator.evaluate(full_b, h)
        if all(evaluator.evaluate(full_b, o) >= my_s for o in others): wins += 1
    return wins / sim_count

# ================= 3. 极简 UI 构建 =================
st.set_page_config(page_title="9人桌盈利大师", layout="wide")
st.title("🏆 9人桌盈利决策终端")

with st.sidebar:
    st.header("📊 实战数据输入")
    pos = st.selectbox("你的位置", ["UTG (枪口位)", "UTG+1", "MP1", "MP2", "HJ", "CO (关位)", "BTN (按钮位)", "SB (小盲)", "BB (大盲)"])
    pot = st.number_input("当前总底池 ($)", value=100)
    call_cost = st.number_input("跟注/入池费用 ($)", value=20)
    opp_type = st.radio("对手主要类型", ["稳健型", "疯子/松凶", "跟注站/鱼"])

# 极速手牌录入
col1, col2 = st.columns(2)
with col1:
    h_raw = st.text_input("🎯 你的底牌 (如 ak)", value="aa").lower()
    h_cards = [c[0].upper()+c[1].lower() for c in re.findall(r'([2-9tjqka][hsdc])', h_raw.replace('10','t'))]
    if len(h_cards) == 2:
        tier, pos_adv = get_position_strategy(h_cards[0]+h_cards[1], pos)
        st.info(f"**牌力评级：{tier}**\n\n{pos_adv}")

with col2:
    b_raw = st.text_input("🌊 公共牌 (翻前留空)", value="").lower()
    b_cards = [c[0].upper()+c[1].lower() for c in re.findall(r'([2-9tjqka][hsdc])', b_raw.replace('10','t'))]

st.markdown("---")

if st.button("⚡ 获取最高盈利策略", type="primary", use_container_width=True):
    if len(h_cards) == 2:
        with st.spinner("正在进行 9 人桌深度推演..."):
            equity = simulate_multi_equity(h_cards, b_cards, 9)
            # 计算底池赔率
            pot_odds = call_cost / (pot + call_cost) if (pot + call_cost) > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("你的胜率", f"{equity*100:.1f}%")
            c2.metric("回本所需胜率", f"{pot_odds*100:.1f}%")
            c3.metric("盈利期望 (EV)", f"{(equity*pot - (1-equity)*call_cost):+.1f}")
            
            st.markdown("### 🤖 最终战术指令")
            if equity > pot_odds * 1.2:
                if "疯子" in opp_type:
                    st.success("🔥 **盈利最高打法：慢打 (Trap)！** 让疯子继续下注，你在河牌全下。")
                else:
                    st.success("🔥 **盈利最高打法：价值加注 (Value Bet)！** 你的胜率远超赔率，必须收钱。")
            elif equity > pot_odds:
                st.warning("✅ **盈利最高打法：跟注 (Call)。** 长期来看这是正 EV 决策。")
            else:
                st.error("❌ **盈利最高打法：立刻弃牌 (Fold)。** 数学上你正在送钱。")
