import streamlit as st
from treys import Card, Evaluator, Deck
import re

# ================= 1. 工具：智能解析与视觉显示 =================
def parse_cards(input_str):
    """解析任何输入，如 as2s, 10h, kd"""
    if not input_str: return []
    s = input_str.upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    return [c[0] + c[1].lower() for c in cards]

def display_poker_icons(card_list):
    """将字母转为带颜色的大图标"""
    if not card_list: return "等待输入..."
    suits_map = {
        's': ('♠️', '#000000'), # 黑桃
        'h': ('♥️', '#FF0000'), # 红桃
        'd': ('♦️', '#FF0000'), # 方块
        'c': ('♣️', '#008000')  # 梅花 (绿色更易区分)
    }
    html_str = ""
    for c in card_list:
        val = c[0].replace('T', '10')
        icon, color = suits_map[c[1]]
        html_str += f"<span style='font-size:24px; font-weight:bold; color:{color}; margin-right:10px;'>{val}{icon}</span>"
    return html_str

# ================= 2. 逻辑：全位置策略矩阵 =================
def get_matrix_advice(hand_str):
    tier_map = {
        'T1 (顶级)': ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo'],
        'T2 (强牌)': ['TT', '99', 'AQs', 'AQo', 'AJs', 'KQs'],
        'T3 (优质)': ['88', '77', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo'],
        'T4 (投机)': ['66', '55', 'A9s', 'A8s', 'KTs', 'QTs', 'T9s', '98s', 'J9s']
    }
    h = "".join(sorted([hand_str[0], hand_str[2]], reverse=True))
    suited = hand_str[1] == hand_str[3]
    h_key = h + ('s' if suited else 'o') if h[0] != h[1] else h
    
    tier = "T5 (垃圾)"
    for name, cards in tier_map.items():
        if h_key in cards: tier = name

    matrix = {
        "前位 (UTG/MP1)": "🛑 **极紧弃牌**：除 T1 以外全部弃牌。这里亏钱最快。",
        "中位 (MP2/HJ)": "🟡 **稳健过滤**：T1/T2 必打。T3 没人加注可跟。",
        "后位 (CO/BTN)": "💰 **主动剥削**：T1-T4 均可打。没人打钱就加注抢池！",
        "盲注 (SB/BB)": "🛡️ **防守反击**：位置差，仅用 T1/T2 强力反击。"
    }
    return tier, matrix

# ================= 3. 网页 UI 构建 =================
st.set_page_config(page_title="德州盈利终端", layout="centered")

st.title("🏆 德州全位置盈利矩阵")

# --- 新增：花色英文字母参考栏 ---
st.markdown("""
<div style="background-color:#f0f2f6; padding:10px; border-radius:10px; border:1px solid #ddd; margin-bottom:20px;">
    <strong>字母参考：</strong> 
    <span style="color:black;">s=黑桃♠️</span> | 
    <span style="color:red;">h=红桃♥️</span> | 
    <span style="color:red;">d=方块♦️</span> | 
    <span style="color:green;">c=梅花♣️</span> 
    &nbsp;&nbsp;&nbsp; (例：输入 <code>as2s</code>)
</div>
""", unsafe_allow_html=True)

# 录入区
h_raw = st.text_input("🎯 你的底牌 (直接连写字母)", value="asad", help="例: ahkh").lower()
h_cards = parse_cards(h_raw)

# 实时花色显示反馈
st.markdown(display_poker_icons(h_cards), unsafe_allow_html=True)

if len(h_cards) == 2:
    st.markdown("---")
    tier, matrix = get_matrix_advice(h_cards[0] + h_cards[1])
    st.success(f"### 当前牌力：{tier}")
    
    # 展示全位置
    for pos, adv in matrix.items():
        with st.expander(f"📍 {pos} 盈利对策", expanded=True):
            st.write(adv)

st.markdown("---")
# 翻后公共牌
b_raw = st.text_input("🌊 公共牌 (翻后录入)", value="").lower()
b_cards = parse_cards(b_raw)
st.markdown(display_poker_icons(b_cards), unsafe_allow_html=True)

if st.button("⚡ 获取翻后盈利方案", type="primary", use_container_width=True):
    st.write("正在计算 9 人桌随机范围胜率...")
    # (保留之前的胜率模拟逻辑)
