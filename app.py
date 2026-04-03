import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 核心逻辑：智能解析与可视化 =================

def parse_cards(input_str):
    if not input_str: return []
    s = input_str.upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    return [c[0] + c[1].lower() for c in cards]

def display_cards(card_list):
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
            for card in hand1 + hand2 + board: deck.cards.remove(card)
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

def get_pro_advice(equity, street, opp_type):
    # 第一部分：基于数学概率的基础建议
    advice = f"💡 **基础行动指南** (实战胜率 **{equity*100:.1f}%**)：\n\n"
    if equity > 0.85: advice += "👑 **绝对碾压**：你在场上是霸主！尽情下注造大底池。"
    elif equity > 0.65: advice += "🔥 **强势领跑**：优势很大，应进行**价值下注**，不给对手免费买牌的机会。"
    elif equity > 0.35: advice += "⚖️ **势均力敌 / 听牌**：大概率在买花或买顺。根据对手下注大小算赔率决定是否跟注。"
    else: advice += "🛑 **严重落后**：对方大概率已击中强牌。面对任何下注都应**立刻弃牌 (Fold)**。"

    # 第二部分：基于对手类型的无情剥削对策
    opp_advice = ""
    if "跟注站" in opp_type:
        opp_advice = "🐟 **【剥削对策 - 松被动/跟注站】**\n- 🎯 **死穴**：什么烂牌都爱跟，绝对不弃牌。\n- 🔪 **杀招**：**绝对不要诈唬他！** 拿到中对、顶对以上的牌，就无脑狠狠做大尺寸的价值下注（Value Bet），他会用各种底对甚至A高给你支付。"
    elif "大紧逼" in opp_type:
        opp_advice = "🪨 **【剥削对策 - 紧被动/老石头】**\n- 🎯 **死穴**：没有坚果牌绝不主动打钱。\n- 🔪 **杀招**：他在盲注位时，疯狂加注偷他的池！但他一旦在翻后主动下注或加注，说明他拿了天牌，除非你是绝杀，否则立刻果断弃牌，一毛钱都别多给！"
    elif "紧凶" in opp_type:
        opp_advice = "🦈 **【硬核对策 - 紧凶型/常客玩家】**\n- 🎯 **死穴**：打法过于标准，保护盲注意识强。\n- 🔪 **杀招**：尊重他的加注，少用边缘牌去硬碰硬。当你拿到超强牌时，多用**过牌-加注（Check-Raise）**给他设下陷阱，让他以为你在诈唬从而反咬你一口。"
    elif "疯子" in opp_type:
        opp_advice = "🌪️ **【降维打击 - 松凶型/疯子玩家】**\n- 🎯 **死穴**：极其爱演，把把想靠诈唬把别人打跑。\n- 🔪 **杀招**：**让他自己送死！** 稍微收紧起手牌，一旦击中顶对以上，就一直过牌（Check）装弱，引诱他用空气牌诈唬全下（All-in）。千万别被他激怒。"

    if opp_advice:
        return advice + "\n\n---\n\n" + opp_advice
    return advice

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州胜率与剥削大师", layout="centered")

st.title("🃏 德州胜率与剥削大师")
st.markdown("输入手牌算出胜率，选择对手性格，获取一击必杀的**剥削策略**。")
st.markdown("---")

# UI 输入区
col1, col2 = st.columns(2)
with col1:
    p1_raw = st.text_input("🎯 你的底牌 (如: as2s)", value="")
    p1_cards = parse_cards(p1_raw)
    st.markdown(f"**{display_cards(p1_cards)}**")

with col2:
    p2_raw = st.text_input("❓ 对手底牌 (未知请留空)", value="")
    p2_cards = parse_cards(p2_raw)
    st.markdown(f"**{display_cards(p2_cards)}**")

board_raw = st.text_input("🌊 公共牌 (如: 4sks10h)", value="")
board_cards = parse_cards(board_raw)
st.markdown(f"**{display_cards(board_cards)}**")

st.markdown("---")
st.markdown("### 🕵️ 锁定你的对手")
opp_type = st.selectbox(
    "他在牌桌上是个什么样的人？",
    ["❓ 未知对手 (提供纯概率基础建议)",
     "🐟 松被动 / 跟注站 (玩得多，极少加注，就爱跟注)",
     "🌪️ 松凶型 / 疯子 (玩得多，疯狂下注/满天飞诈唬)",
     "🪨 紧被动 / 大紧逼 (只玩超强牌，等死不主动打钱)",
     "🦈 紧凶型 / 常客 (只挑好牌打，一旦入池攻击性极强)"]
)

# 计算按钮
if st.button("⚡ 计算胜率 & 获取针对对策", type="primary", use_container_width=True):
    if len(p1_cards) != 2:
        st.error("❌ 你的底牌必须是 2 张！(比如打: a s 2 s)")
    elif len(p2_cards) not in [0, 2]:
        st.error("❌ 对手底牌必须是 2 张，或者直接清空留白！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("❌ 公共牌只能是 0张(翻前), 3张(翻牌), 4张 或 5张！")
    else:
        with st.spinner("🧠 深度推演中，正在生成剥削方案..."):
            eq1, eq2, err = simulate_equity(p1_cards, p2_cards, board_cards)

            if err:
                st.error(f"❌ {err}")
            else:
                st.success("✅ 推演完成！")
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="🎯 你的胜率", value=f"{eq1 * 100:.1f}%")
                with res_col2:
                    label_text = "🌪️ 范围胜率 (未知对手)" if len(p2_cards) == 0 else "😈 对手胜率"
                    st.metric(label=label_text, value=f"{eq2 * 100:.1f}%")
                
                street = "翻牌前" if len(board_cards) == 0 else "翻牌后"
                st.info(get_pro_advice(eq1, street, opp_type))
