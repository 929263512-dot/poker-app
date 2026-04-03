import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 核心工具：起手牌等级系统 =================

def get_preflop_tier(hand):
    """根据起手牌判断等级 (简化版职业分级)"""
    if len(hand) != 2: return None, None
    
    # 提取点数和是否同花
    r1, s1 = hand[0][0].upper().replace('10','T'), hand[0][1]
    r2, s2 = hand[1][0].upper().replace('10','T'), hand[1][1]
    suited = s1 == s2
    
    # 建立点数顺序
    rank_order = "23456789TJQKA"
    v1, v2 = rank_order.find(r1), rank_order.find(r2)
    if v1 < v2: v1, v2 = v2, v1
    h_str = f"{rank_order[v1]}{rank_order[v2]}{'s' if suited else 'o'}"
    if r1 == r2: h_str = f"{r1}{r2}" # 对子

    # 顶级起手牌 (T1)
    if h_str in ['AA', 'KK', 'QQ', 'JJ', 'AKs']:
        return "🔥 T1: 顶级天牌", "必打！翻前可以直接加注 (3-bet) 甚至全下。"
    # 强力起手牌 (T2)
    elif h_str in ['TT', 'AQs', 'AQo', 'AJs', 'KQs', 'AKo']:
        return "💎 T2: 强力起手", "非常扎实。适合主动加注，占领主动权。"
    # 中等起手牌 (T3)
    elif h_str in ['99', '88', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo']:
        return "🟢 T3: 优质牌", "有很大潜力。多人池中表现不错，注意控制位置。"
    # 投机牌 (T4)
    elif v1 >= 10 or (suited and v1 - v2 <= 3):
        return "🟡 T4: 投机牌", "适合在后位偷池，或者便宜进池看翻牌买顺/买花。"
    # 垃圾牌
    else:
        return "💀 T5: 垃圾牌", "长期打这种牌必亏。建议直接弃牌，除非你在大盲位免费看牌。"

# ================= 核心工具：智能解析 =================

def parse_cards(input_str):
    if not input_str: return []
    s = input_str.upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    return [c[0] + c[1].lower() for c in cards]

def display_cards(card_list):
    suits_map = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    visuals = [f"**{c[0].replace('T','10')}{suits_map[c[1]]}**" for c in card_list]
    return " ".join(visuals) if visuals else "待输入"

# ================= 核心引擎：模拟逻辑 =================

def simulate_multi_equity(hand, board, num_players, iterations=3000):
    evaluator = Evaluator()
    try:
        h1 = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return None, "格式错误"
    wins = 0
    for _ in range(iterations):
        deck = Deck()
        try:
            for card in h1 + b: deck.cards.remove(card)
        except: return None, "重复"
        others = [deck.draw(2) for _ in range(num_players - 1)]
        cards_needed = 5 - len(b)
        full_board = b + deck.draw(cards_needed) if cards_needed > 0 else b
        my_score = evaluator.evaluate(full_board, h1)
        is_winner = True
        for o in others:
            if evaluator.evaluate(full_board, o) < my_score:
                is_winner = False
                break
        if is_winner: wins += 1
    return wins / iterations, None

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州决策终端", layout="wide")
st.title("📟 德州扑克实战决策终端 (带翻前评级)")

with st.sidebar:
    st.header("⚙️ 游戏设置")
    num_players = st.slider("玩家人数 (含自己)", 2, 10, 6)
    st.markdown("---")
    pot_size = st.number_input("当前总底池 ($)", 0, 1000000, 100)
    opp_bet = st.number_input("对方下注额 ($)", 0, 1000000, 50)
    st.markdown("---")
    opp_type = st.selectbox("对手性格", ["未知", "跟注站 (不弃牌)", "疯子 (乱加注)", "紧逼 (没牌不打)"])

col_h, col_b = st.columns(2)
with col_h:
    st.subheader("🎯 你的底牌")
    p1_raw = st.text_input("输入底牌 (如 ak)", key="p1")
    p1_cards = parse_cards(p1_raw)
    st.markdown(f"确认：{display_cards(p1_cards)}")
    
    # --- 核心新增：翻前牌力显示 ---
    if len(p1_cards) == 2:
        tier_name, tier_desc = get_pre_flop_tier = get_preflop_tier(p1_cards)
        st.markdown(f"**起手评级：{tier_name}**")
        st.caption(tier_desc)

with col_b:
    st.subheader("🌊 公共牌")
    board_raw = st.text_input("输入公共牌 (翻前留空)", key="board")
    board_cards = parse_cards(board_raw)
    st.markdown(f"确认：{display_cards(board_cards)}")

st.markdown("---")

if st.button("⚡ 秒出最高盈利方案", type="primary", use_container_width=True):
    if len(p1_cards) != 2:
        st.error("请输入底牌")
    else:
        equity, err = simulate_multi_equity(p1_cards, board_cards, num_players)
        if err: st.error(err)
        else:
            c1, c2 = st.columns(2)
            c1.metric("你的真实胜率", f"{equity*100:.1f}%")
            c2.metric("保本所需胜率", f"{(opp_bet/(pot_size+opp_bet))*100:.1f}%")
            
            # 教练建议逻辑 (综合判断)
            st.markdown("### 🤖 盈利决策建议")
            call_odds = opp_bet / (pot_size + opp_bet)
            
            if len(board_cards) == 0:
                tier_name, _ = get_preflop_tier(p1_cards)
                if "T1" in tier_name or "T2" in tier_name:
                    st.success("🔥 翻前优势巨大：建议大幅加注 (3-Bet)！不要给垃圾牌便宜看翻牌的机会。")
                elif equity > call_odds:
                    st.warning("✅ 赔率合适：可以跟注进场，但注意控制底池。")
                else:
                    st.error("❌ 建议弃牌：你的底牌在当前人数下盈利前景暗淡。")
            else:
                # 翻后逻辑 (保持之前的 EV 建议)
                ev = (equity * pot_size) - ((1 - equity) * opp_bet)
                if equity > call_odds:
                    st.success(f"📈 决策：跟注/加注是盈利的 (EV: {ev:+.1f})。你的牌力领先于平均水平。")
                else:
                    st.error(f"📉 决策：及时止损。当前胜率支撑不起你的跟注成本。")
