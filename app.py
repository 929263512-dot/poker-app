import streamlit as st
from treys import Card, Evaluator, Deck

def simulate_equity(hand1_str, hand2_str, board_str=[], iterations=5000):
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        hand2 = [Card.new(c) for c in hand2_str]
        board = [Card.new(c) for c in board_str]
    except Exception as e:
        return None, None, f"卡牌输入格式有误，请检查！(错误: {e})"

    wins1, wins2, ties = 0, 0, 0

    for i in range(iterations):
        deck = Deck()
        for card in hand1 + hand2 + board:
            try:
                deck.cards.remove(card)
            except ValueError:
                return None, None, "输入了重复的卡牌，请检查！"

        cards_needed = 5 - len(board)
        simulated_board = board + deck.draw(cards_needed) if cards_needed > 0 else board

        score1 = evaluator.evaluate(simulated_board, hand1)
        score2 = evaluator.evaluate(simulated_board, hand2)

        if score1 < score2: wins1 += 1
        elif score2 < score1: wins2 += 1
        else: ties += 1

    eq1 = (wins1 + 0.5 * ties) / iterations
    eq2 = (wins2 + 0.5 * ties) / iterations
    return eq1, eq2, None

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="实时胜率计算器", layout="centered")

st.title("🃏 德州实时胜率计算器")
st.markdown("输入底牌和桌上的公共牌，利用蒙特卡洛算法秒算赢面。")
st.markdown("---")

st.info("💡 格式提示：红桃A = `Ah`, 黑桃Q = `Qs`, 方块10 = `Td`, 梅花2 = `2c`")

col1, col2 = st.columns(2)
with col1:
    p1_input = st.text_input("你的手牌 (例如: Ah, Kh)", value="Ah, Kh")
with col2:
    p2_input = st.text_input("对手手牌 (例如: Qs, Qc)", value="Qs, Qc")

board_input = st.text_input("桌上公共牌 (翻牌前不填，例如填入: 2d, 5c, Jd)", value="")

if st.button("⚡ 计算实时胜率", type="primary", use_container_width=True):
    # 处理输入格式
    p1_hand = [c.strip() for c in p1_input.split(",") if c.strip()]
    p2_hand = [c.strip() for c in p2_input.split(",") if c.strip()]
    board_cards = [c.strip() for c in board_input.split(",") if c.strip()]

    if len(p1_hand) != 2 or len(p2_hand) != 2:
        st.error("每位玩家必须输入确切的 2 张手牌！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("公共牌数量必须是 0张(翻牌前), 3张(翻牌圈), 4张(转牌) 或 5张(河牌)！")
    else:
        with st.spinner("大脑飞速计算中... (模拟发牌5000次)"):
            eq1, eq2, err = simulate_equity(p1_hand, p2_hand, board_cards, iterations=5000)

            if err:
                st.error(err)
            else:
                st.success("计算完成！")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="✅ 你的胜率", value=f"{eq1 * 100:.2f}%")
                with res_col2:
                    st.metric(label="⚠️ 对手胜率", value=f"{eq2 * 100:.2f}%")
