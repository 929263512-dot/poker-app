import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 核心工具：智能识别 =================

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

# ================= 核心引擎：多玩家胜率模拟 =================

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
        except: return None, "重复卡牌"

        # 为其余玩家随机发牌
        others = [deck.draw(2) for _ in range(num_players - 1)]
        cards_needed = 5 - len(b)
        full_board = b + deck.draw(cards_needed) if cards_needed > 0 else b

        my_score = evaluator.evaluate(full_board, h1)
        # 检查是否赢了所有人
        is_winner = True
        for other_hand in others:
            if evaluator.evaluate(full_board, other_hand) < my_score:
                is_winner = False
                break
        if is_winner: wins += 1

    return wins / iterations, None

# ================= 战术大脑：盈利最大化算法 =================

def get_max_profit_strategy(equity, pot, bet, players, opp_type):
    # 计算底池赔率 (Pot Odds)
    # 你需要跟注的比例：跟注额 / (底池总额 + 对方下注额 + 你的跟注额)
    call_odds = bet / (pot + bet) if (pot + bet) > 0 else 0
    ev = (equity * pot) - ((1 - equity) * bet)
    
    strategy = f"### 💰 盈利最大化决策 (EV: {ev:+.1f})\n\n"
    
    if equity > (1 / players) * 1.5: # 显著高于平均胜率
        if "疯子" in opp_type:
            strategy += "🚀 **最高盈利：慢打陷阱 (Slow Play)**\n对方极具攻击性，不要急于加注，通过过牌引诱他继续诈唬下注，在河牌圈再全推（All-in）榨取最大价值。"
        elif "跟注站" in opp_type:
            strategy += "🚀 **最高盈利：重炮价值 (Overbet)**\n对方不会弃牌，直接下注 75% 到 120% 的底池。不要怕吓跑他，他会用任何烂对子支付你。"
        else:
            strategy += "🚀 **最高盈利：标准价值推注**\n建议下注 2/3 底池，保护牌力同时获取价值。"
    
    elif equity > call_odds: # 胜率大于赔率，长期盈利
        strategy += "✅ **最高盈利：跟注 (Call)**\n目前的胜率支持你继续看牌。从概率学上讲，长期这样打是赚钱的。"
    
    else: # 负 EV
        if equity > 0.25 and players <= 3:
            strategy += "⚠️ **最高盈利：尝试诈唬 (Bluff)**\n单纯跟注必赔。如果对方性格偏紧，可以尝试反冲加注（3-Bet）逼迫对方弃牌，利用弃牌率获利。"
        else:
            strategy += "❌ **最高盈利：及时止损 (Fold)**\n这手牌长期看是赔钱的。弃牌是目前盈利最高的动作，把筹码留到下一把优势局。"

    return strategy

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州决策终端", layout="wide")

st.title("📟 德州扑克实战决策终端 (极速版)")

# 侧边栏：全局设置
with st.sidebar:
    st.header("⚙️ 游戏设置")
    num_players = st.slider("玩家人数 (含自己)", 2, 10, 6)
    st.markdown("---")
    pot_size = st.number_input("当前总底池 ($)", 0, 1000000, 100)
    opp_bet = st.number_input("对方下注额 ($)", 0, 1000000, 50)
    st.markdown("---")
    opp_type = st.selectbox("对手性格", ["未知", "跟注站 (不弃牌)", "疯子 (乱加注)", "紧逼 (没牌不打)"])

# 主界面：极速输入
col_h, col_b = st.columns(2)

with col_h:
    st.subheader("🎯 你的底牌")
    p1_raw = st.text_input("连打字母 (如 ak)", key="p1", placeholder="无需空格逗号")
    p1_cards = parse_cards(p1_raw)
    st.markdown(f"确认：{display_cards(p1_cards)}")

with col_b:
    st.subheader("🌊 公共牌")
    board_raw = st.text_input("连打字母 (如 4skst)", key="board")
    board_cards = parse_cards(board_raw)
    st.markdown(f"确认：{display_cards(board_cards)}")

st.markdown("---")

if st.button("⚡ 秒出最高盈利方案", type="primary", use_container_width=True):
    if len(p1_cards) != 2:
        st.error("请输入 2 张底牌")
    else:
        with st.spinner("量子计算中..."):
            equity, err = simulate_multi_equity(p1_cards, board_cards, num_players)
            
            if err: st.error(err)
            else:
                c1, c2 = st.columns(2)
                c1.metric("你的真实胜率", f"{equity*100:.1f}%")
                c2.metric("保本所需胜率", f"{(opp_bet/(pot_size+opp_bet))*100:.1f}%")
                
                st.markdown("---")
                st.info(get_max_profit_strategy(equity, pot_size, opp_bet, num_players, opp_type))

# 快速重置按钮
if st.button("🧹 清空重置"):
    st.rerun()
