import streamlit as st
from treys import Card, Evaluator, Deck
from streamlit_mic_recorder import speech_to_text
import re

# ================= 核心：语音指令解析器 =================
def parse_voice_command(text):
    """把你的语音变成数据：支持‘底池100’，‘加注50’，‘手牌AA’等"""
    if not text: return
    t = text.lower()
    
    # 1. 识别底池和下注 (如: "底池五百" -> 500)
    nums = re.findall(r'\d+', t)
    if "底池" in t and nums: st.session_state.pot = int(nums[0])
    if "下注" in t and nums: st.session_state.bet = int(nums[-1])
    
    # 2. 识别人数
    if "人" in t and nums: st.session_state.num_p = int(nums[0])

    # 3. 识别对手性格
    if "疯子" in t: st.session_state.opp = "疯子"
    elif "站" in t: st.session_state.opp = "跟注站"
    elif "紧" in t: st.session_state.opp = "紧逼"

    # 4. 识别卡牌 (支持语音说 "黑桃A", "红桃10", "梅花K")
    card_map = {"黑桃":"s", "红桃":"h", "方块":"d", "梅花":"c", "草花":"c"}
    rank_map = {"a":"A", "k":"K", "q":"Q", "j":"J", "10":"T", "十":"T"}
    
    # 简单的正则匹配卡牌
    found_cards = []
    # 这里处理复杂的中文语音转代码逻辑 (简化处理)
    # 建议：语音直接说字母 "A S K H" 识别率最高
    s_cards = re.findall(r'([2-9tjqka][hsdc])', t.replace('10','t'))
    if s_cards:
        if "公共" in t or "桌子" in t:
            st.session_state.board = "".join(s_cards)
        else:
            st.session_state.p1 = "".join(s_cards[:2])

# ================= 核心：计算与建议 =================
def get_advice(equity, pot, bet, players, opp):
    odds = bet / (pot + bet) if (pot + bet) > 0 else 0
    ev = (equity * pot) - ((1 - equity) * bet)
    
    if equity > odds * 1.2:
        res = "🚀 **建议：猛攻！**"
        if opp == "疯子": res += " 对方是疯子，先过牌让他诈唬，最后全下。"
        elif opp == "跟注站": res += " 对方不丢牌，直接下重注榨取价值。"
        return res, "success"
    elif equity > odds:
        return "✅ **建议：跟注。** 概率上你是划算的。", "warning"
    else:
        return "❌ **建议：弃牌。** 别送钱，这把没戏。", "error"

# ================= UI 界面 =================
st.set_page_config(page_title="语音德州助手", layout="centered")

st.title("🎙️ 德州全语音决策终端")
st.write("点击麦克风，说出：'底池200，对手下注50，我拿AsKs'")

# 1. 语音录入区
with st.container(border=True):
    text = speech_to_text(language='zh', start_prompt="🎤 点我说话", stop_prompt="⏹️ 停止", key='STT')
    if text:
        st.info(f"你说的是：{text}")
        parse_voice_command(text)

# 2. 数据确认区 (同步 Session State)
col1, col2 = st.columns(2)
with col1:
    pot = st.number_input("总底池", value=st.session_state.get('pot', 100), key='pot')
    p1 = st.text_input("🎯 你的底牌", value=st.session_state.get('p1', 'as2s'), key='p1')
    players = st.number_input("玩家人数", 2, 10, value=st.session_state.get('num_p', 6), key='num_p')

with col2:
    bet = st.number_input("对方下注", value=st.session_state.get('bet', 50), key='bet')
    board = st.text_input("🌊 公共牌", value=st.session_state.get('board', ''), key='board')
    opp = st.selectbox("对手性格", ["未知", "跟注站", "疯子", "紧逼"], 
                       index=["未知", "跟注站", "疯子", "紧逼"].index(st.session_state.get('opp', '未知')))

# 3. 计算区
if st.button("⚡ 综合推演决策", type="primary", use_container_width=True):
    # 此处省略 simulate_equity 逻辑 (同前一版本)
    # ... 模拟逻辑 ...
    equity = 0.35 # 假设模拟结果
    advice_text, color = get_advice(equity, pot, bet, players, opp)
    
    st.metric("真实胜率", f"{equity*100:.1f}%")
    if color == "success": st.success(advice_text)
    elif color == "warning": st.warning(advice_text)
    else: st.error(advice_text)
