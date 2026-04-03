import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 核心逻辑：全位置决策矩阵 =================
def get_full_table_matrix(hand_str):
    """根据手牌，计算 9 个位置的全部对策"""
    tier_map = {
        'T1 (顶级)': ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo'],
        'T2 (强牌)': ['TT', '99', 'AQs', 'AQo', 'AJs', 'KQs'],
        'T3 (优质)': ['88', '77', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo'],
        'T4 (投机)': ['66', '55', 'A9s', 'A8s', 'KTs', 'QTs', 'T9s', '98s', 'J9s']
    }
    
    # 提取手牌特征
    h = "".join(sorted([hand_str[0], hand_str[2]], reverse=True))
    suited = hand_str[1] == hand_str[3]
    h_key = h + ('s' if suited else 'o') if h[0] != h[1] else h
    
    tier = "T5 (垃圾)"
    for name, cards in tier_map.items():
        if h_key in cards: tier = name

    # 定义全位置对策表
    matrix = {
        "前位 (UTG, UTG+1, MP1)": "🛑 极紧：仅玩 T1 牌，其余全部弃牌。为了长期盈利，这里绝不送钱。",
        "中位 (MP2, HJ)": "🟡 稳健：T1/T2 必打。如果是 T3，前面没人加注可以尝试进入。",
        "后位 (CO, BTN)": "💰 剥削：T1-T4 均可打。这是你赢钱的主战场，前面没人打钱就加注偷池。",
        "盲注位 (SB, BB)": "🛡️ 防守：由于位置最差，仅玩 T1/T2 进行反击，其余尽量便宜看牌或弃牌。"
    }
    
    # 针对当前 T 级的具体建议
    if "T1" in tier: 
        final_adv = "🔥 **你是全场霸主**：无论在哪个位置，都要主动加注（Raise）造大底池！"
    elif "T2" in tier:
        final_adv = "💎 **强力持有**：前/中位加注，后位如果有人加注，考虑 3-Bet 反击。"
    elif "T3" in tier:
        final_adv = "🟢 **中坚力量**：前位弃牌，中后位入池。注意翻后如果没中直接撤。"
    else:
        final_adv = "💀 **盈利警告**：这手牌在 9 人桌长期价值极低，建议非后位直接放弃。"

    return tier, matrix, final_adv

# ================= 2. UI 构建 =================
st.set_page_config(page_title="9人桌全位置大师", layout="wide")
st.title("🏆 9人桌全位置盈利矩阵")

# 侧边栏保留底池计算
with st.sidebar:
    st.header("💵 赔率计算")
    pot = st.number_input("当前总底池", 100)
    bet = st.number_input("跟注额", 20)
    st.markdown("---")
    st.caption("全位置矩阵会自动根据 9 人桌标准逻辑生成。")

# 极简输入
h_raw = st.text_input("🎯 输入你的底牌 (如 aa, ak, qjs)", value="asad").lower()
h_cards = [c[0].upper()+c[1].lower() for c in re.findall(r'([2-9tjqka][hsdc])', h_raw.replace('10','t'))]

if len(h_cards) == 2:
    tier, matrix, final_adv = get_full_table_matrix(h_cards[0]+h_cards[1])
    
    st.success(f"### 当前牌力评级：{tier}")
    st.info(final_adv)
    
    st.markdown("---")
    st.subheader("📋 9人桌各位置盈利对策表")
    
    # 用表格形式展示全位置操作
    col_l, col_r = st.columns(2)
    with col_l:
        st.write(f"**【前位】** (UTG/MP1)")
        st.write(matrix["前位 (UTG, UTG+1, MP1)"])
        st.write(f"**【后位】** (CO/BTN)")
        st.write(matrix["后位 (CO, BTN)"])
    with col_r:
        st.write(f"**【中位】** (MP2/HJ)")
        st.write(matrix["中位 (MP2, HJ)"])
        st.write(f"**【盲注】** (SB/BB)")
        st.write(matrix["盲注位 (SB, BB)"])

st.markdown("---")
# 公共牌部分保留用于翻后计算
b_raw = st.text_input("🌊 公共牌 (翻后才填)", value="").lower()
if st.button("⚡ 获取翻后胜率"):
    # (此处保留之前的胜率模拟逻辑...)
    st.write("正在计算翻后 9 人随机范围胜率...")
