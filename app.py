import streamlit as st
from treys import Card, Evaluator, Deck
from streamlit_mic_recorder import speech_to_text
import re

# ================= 核心：德州术语智能纠错字典 =================
def smart_poker_parser(text):
    """智能纠错：把听错的词强行翻译回德州代码"""
    if not text: return
    t = text.lower()
    
    # 1. 纠错点数
    rank_map = {
        '诶': 'A', 'a': 'A', '尖': 'A', '爱': 'A', 
        '开': 'K', 'k': 'K', '老k': 'K',
        '圈': 'Q', 'q': 'Q', '皮蛋': 'Q',
        '勾': 'J', 'j': 'J', '丁': 'J',
        '十': 'T', '10': 'T', 't': 'T'
    }
    # 2. 纠错花色
    suit_map = {
        '黑': 's', '桃': 's', 's': 's',
        '红': 'h', '心': 'h', 'h': 'h',
        '方': 'd', '块': 'd', 'd': 'd',
        '草': 'c', '梅': 'c', 'c': 'c', '青': 'c'
    }

    # 提取数字 (底池/下注/人数)
    nums = re.findall(r'\d+', t)
    if "底池" in t and nums: st.session_state.pot = int(nums[0])
    if "下注" in t and nums: st.session_state.bet = int(nums[-1])
    if "人" in t and nums: st.session_state.num_p = int(nums[0])

    # 复杂匹配：例如识别 "黑桃A" 或 "AS"
    found_cards = []
    # 模式1: 颜色+点数 (如: 黑桃A)
    for s_word, s_code in suit_map.items():
        for r_word, r_code in rank_map.items():
            if f"{s_word}{r_word}" in t or f"{r_word}{s_word}" in t:
                found_cards.append(f"{r_code}{s_code}")
    
    # 模式2: 直接说字母 (如: AS)
    simple_matches = re.findall(r'([2-9tjqka][hsdc])', t.replace('10','t'))
    found_cards.extend([m[0].upper()+m[1].lower() for m in simple_matches])

    # 去重并分配
    found_cards = list(dict.fromkeys(found_cards))
    if found_cards:
        if any(w in t for w in ["公共", "桌面", "发出来"]):
            st.session_state.board = "".join(found_cards)
        else:
            st.session_state.p1 = "".join(found_cards[:2])

# ================= 计算引擎 (略，同前) =================
def simulate_multi_equity(hand, board, num_players):
    evaluator = Evaluator()
    try:
        h = [Card.new(c) for c in hand]
        b = [Card.new(c) for c in board]
    except: return 0.1, "格式错"
    wins = 0
    for _ in range(1500):
        deck = Deck()
        try:
            for c in h + b: deck.cards.remove(c)
        except: break
        others = [deck.draw(2) for _ in range(num_players - 1)]
        full_b = b + deck.draw(5-len(b)) if len(b)<5 else b
        my_s = evaluator.evaluate(full_b, h)
        if all(evaluator.evaluate(full_b, o) >= my_s for o in others): wins += 1
    return wins / 1500, None

# ================= UI 界面 =================
st.set_page_config(page_title="极速德州助手", layout="centered")

# 初始化状态
for k, v in {'pot':100, 'bet':50, 'num_p':6, 'p1':'AA', 'board':''}.items():
    if k not in st.session_state: st.session_state[k] = v

st.title("🎙️ 德州智能语音助手 (纠错版)")
st.caption("提示：语音直接说 '黑桃A' 或字母 'AS' 效果最好")

# 语音输入
text = speech_to_text(language='zh', start_prompt="🎤 按住说话", stop_prompt="⏹️ 停止", key='STT')
if text:
    smart_poker_parser(text)
    st.toast(f"识别中: {text}")

# 数据面板
with st.expander("📊 核心数据确认", expanded=True):
    c1, c2, c3 = st.columns(3)
    pot = c1.number_input("底池", value=st.session_state.pot)
    bet = c2.number_input("对方下注", value=st.session_state.bet)
    num_p = c3.number_input("人数", 2, 10, value=st.session_state.num_p)
    
    p1_str = st.text_input("🎯 你的底牌", value=st.session_state.p1).upper()
    board_str = st.text_input("🌊 公共牌", value=st.session_state.board).upper()

# 策略输出
if st.button("⚡ 获取最高盈利方案", type="primary", use_container_width=True):
    h = [c[0]+c[1].lower() for c in re.findall(r'([2-9TJQKA][HDSC])', p1_str.replace('10','T'))]
    b = [c[0]+c[1].lower() for c in re.findall(r'([2-9TJQKA][HDSC])', board_str.replace('10','T'))]
    
    if len(h) == 2:
        eq, _ = simulate_multi_equity(h, b, num_p)
        odds = bet / (pot + bet) if pot+bet > 0 else 0
        
        st.metric("真实胜率", f"{eq*100:.1f}%", f"需回本: {odds*100:.1f}%", delta_color="inverse")
        
        if eq > odds * 1.3: st.success("🚀 **盈利动作：猛攻/加注！** 你大幅领先。")
        elif eq > odds: st.warning("✅ **盈利动作：跟注。** 概率长期占优。")
        else: st.error("❌ **盈利动作：弃牌。** 胜率不足以回本，撤！")
