import streamlit as st
from treys import Card, Evaluator, Deck

def simulate_equity(hand1_str, hand2_str, board_str=[], iterations=5000):
    evaluator = Evaluator()
    try:
        hand1 = [Card.new(c) for c in hand1_str]
        hand2_known = len(hand2_str) == 2
        hand2 = [Card.new(c) for c in hand2_str] if hand2_known else []
        board = [Card.new(c) for c in board_str]
    except Exception as e:
        return None, None, f"格式错误，请检查大写和小写字母: {e}"

    wins1, wins2, ties = 0, 0, 0
    for i in range(iterations):
        deck = Deck()
        try:
            for card in hand1 + hand2 + board:
                deck.cards.remove(card)
        except ValueError:
            return None, None, "输入了重复卡牌！"

        # 如果对手牌未知，每局随机发两张
        sim_hand2 = hand2 if hand2_known else deck.draw(2)
        cards_needed = 5 - len(board)
        simulated_board = board + deck.draw(cards_needed) if cards_needed > 0 else board

        score1 = evaluator.evaluate(simulated_board, hand1)
        score2 = evaluator.evaluate(simulated_board, sim_hand2)

        if score1 < score2: wins1 += 1
        elif score2 < score1: wins2 += 1
        else: ties += 1

    eq1 = (wins1 + 0.5 * ties) / iterations
    eq2 = (wins2 + 0.5 * ties) / iterations
    return eq1, eq2, None

def get_action_advice(equity, street):
    if street == "翻牌前":
        if equity > 0.65: return "🔥 超强底牌：大胆加注 (Raise)！"
        elif equity > 0.55: return "✅ 优质底牌：适合入池 (Call/Bet)。"
        else: return "⚠️ 边缘或垃圾牌：建议弃牌 (Fold)，除非你在大盲位免费看牌。"

    advice = f"💡 **底池赔率指导**：你的实战赢面约为 **{equity*100:.1f}%**。\n\n"
    if equity > 0.8:
        advice += "📈 绝对优势！你应该**主动下注或加注**，争取赢下更多筹码。"
    elif equity > 0.5:
        advice += "⚔️ 略占优势。可以尝试**价值下注**，如果对手猛烈反击，需警惕对手是在买花/买顺。"
    elif equity > 0.2:
        advice += "🛡️ 你落后了（可能是听牌）。**只在跟注代价很小的情况下才跟注**。如果对手下注超过底池的 1/2，建议弃牌。"
    else:
        advice += "❌ 胜率渺茫。赶紧跑！**果断弃牌 (Fold)**。"
    return advice

# ================= 网页 UI 构建 =================

st.set_page_config(page_title="德州智能教练", layout="centered")

st.title("🛡️ 德州智能教练 (丝滑纯净版)")
st.markdown("已卸载冗余图片模型，彻底告别崩溃！支持**全范围未知底牌胜率推演**与**实战赔率教练**。")
st.markdown("---")

if 'p1_cards' not in st.session_state: st.session_state['p1_cards'] = "As, 2s"
if 'p2_cards' not in st.session_state: st.session_state['p2_cards'] = ""
if 'board_cards' not in st.session_state: st.session_state['board_cards'] = "4s, Ks, Th"

col1, col2 = st.columns(2)
with col1:
    p1_input = st.text_input("🎯 你的手牌 (如: As, 2s)", key='p1_cards')
with col2:
    p2_input = st.text_input("❓ 对手手牌 (未知请留空)", key='p2_cards', placeholder="留空则模拟随机手牌")

board_input = st.text_input("🌊 公共牌 (如: 4s, Ks, Th)", key='board_cards')

if st.button("⚡ 计算实战综合胜率", type="primary", use_container_width=True):
    p1_hand = [c.strip() for c in p1_input.split(",") if c.strip()]
    p2_hand = [c.strip() for c in p2_input.split(",") if c.strip()]
    board_cards = [c.strip() for c in board_input.split(",") if c.strip()]

    if len(p1_hand) != 2:
        st.error("你必须输入自己的 2 张底牌！")
    elif len(p2_hand) not in [0, 2]:
        st.error("对手手牌必须是 2 张，或者直接留空！")
    elif len(board_cards) not in [0, 3, 4, 5]:
        st.error("公共牌数量必须是 0, 3, 4 或 5 张！")
    else:
        with st.spinner("量子大脑模拟中... (进行 5000 次推演)"):
            eq1, eq2, err = simulate_equity(p1_hand, p2_hand, board_cards, iterations=5000)

            if err:
                st.error(err)
            else:
                st.success("推演完成！")
                st.markdown("### 📊 实战胜率")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="✅ 你的预期胜率", value=f"{eq1 * 100:.2f}%")
                with res_col2:
                    label_text = "⚠️ 随机范围胜率" if len(p2_hand) == 0 else "⚠️ 对手胜率"
                    st.metric(label=label_text, value=f"{eq2 * 100:.2f}%")
                
                street = "翻牌前" if len(board_cards) == 0 else "翻牌后"
                st.markdown("### 🤖 战术板")
                st.info(get_action_advice(eq1, street))
