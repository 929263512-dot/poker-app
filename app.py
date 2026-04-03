import streamlit as st
from treys import Card, Evaluator, Deck
import easyocr
import cv2
import numpy as np
import re
from PIL import Image

# ================= 1. 核心 AI 识别引擎 =================
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

def fast_parse_image(img_file, reader):
    """从相机快照中极速抓取卡牌"""
    if img_file is None: return []
    img = Image.open(img_file)
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    # 灰度处理提高识别率
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    results = reader.readtext(gray, detail=0)
    
    # 过滤卡牌逻辑 (A-K, 10->T)
    s = "".join(results).upper().replace('10', 'T')
    s = re.sub(r'[^2-9TJQKAHDSC]', '', s)
    cards = re.findall(r'([2-9TJQKA][HDSC])', s)
    return [c[0] + c[1].lower() for c in cards]

# ================= 2. 战术策略引擎 =================
def get_tier(hand):
    if len(hand) != 2: return "未知", ""
    r1, s1, r2, s2 = hand[0][0].upper().replace('10','T'), hand[0][1], hand[1][0].upper().replace('10','T'), hand[1][1]
    order = "23456789TJQKA"
    v1, v2 = sorted([order.find(r1), order.find(r2)], reverse=True)
    h_str = f"{order[v1]}{order[v2]}{'s' if s1==s2 else 'o'}"
    if r1==r2: h_str = r1*2
    
    if h_str in ['AA','KK','QQ','JJ','AKs']: return "🔥 T1: 顶级天牌", "必打！翻前无脑加注。"
    if h_str in ['TT','AQs','AQo','AJs','KQs','AKo']: return "💎 T2: 强力起手", "扎实。适合主动加注。"
    if v1 >= 10: return "🟢 T3: 优质牌", "潜力大，控制底池。"
    return "🟡 T4: 投机/垃圾", "谨慎进场。"

def simulate_equity(hand, board, num_players):
    evaluator = Evaluator()
    h1 = [Card.new(c) for c in hand]
    b = [Card.new(c) for c in board]
    wins = 0
    for _ in range(2000): # 提速：模拟2000次
        deck = Deck()
        for c in h1 + b: deck.cards.remove(c)
        others = [deck.draw(2) for _ in range(num_players - 1)]
        cards_needed = 5 - len(b)
        full_board = b + deck.draw(cards_needed) if cards_needed > 0 else b
        my_score = evaluator.evaluate(full_board, h1)
        if all(evaluator.evaluate(full_board, o) >= my_score for o in others): wins += 1
    return wins / 2000

# ================= 3. UI 界面 =================
st.set_page_config(page_title="德州决策终端", layout="wide")
st.title("🎴 德州实战决策终端 (快拍版)")

with st.sidebar:
    st.header("⚙️ 实战参数")
    num_players = st.slider("玩家人数", 2, 10, 6)
    pot = st.number_input("底池金额", 0, 10000, 100)
    bet = st.number_input("跟注额", 0, 10000, 50)
    opp = st.selectbox("对手性格", ["未知", "跟注站", "疯子", "紧逼"])

# 快拍区
with st.expander("📸 快速扫描屏幕/手牌", expanded=False):
    cam_image = st.camera_input("对着牌桌拍一下")
    if cam_image:
        reader = load_ocr()
        detected = fast_parse_image(cam_image, reader)
        if detected:
            st.success(f"扫描成功: {', '.join(detected)}")
            # 自动尝试分配 (前2张为底牌，其余公共)
            if len(detected) >= 2: st.session_state.p1 = "".join(detected[:2])
            if len(detected) >= 5: st.session_state.board = "".join(detected[2:])

# 手动修正区 (极致精简)
c1, c2 = st.columns(2)
with c1:
    p1_raw = st.text_input("🎯 你的底牌", key="p1", help="如: ak")
    p1_cards = parse_cards_raw = re.findall(r'([2-9TJQKA][HDSC])', p1_raw.upper().replace('10','T'))
    p1_cards = [c[0]+c[1].lower() for c in p1_cards]
    if len(p1_cards) == 2:
        t_name, t_desc = get_tier(p1_cards)
        st.caption(f"{t_name} | {t_desc}")

with c2:
    board_raw = st.text_input("🌊 公共牌", key="board")
    board_cards = parse_cards_raw = re.findall(r'([2-9TJQKA][HDSC])', board_raw.upper().replace('10','T'))
    board_cards = [c[0]+c[1].lower() for c in board_cards]

if st.button("⚡ 获取最高盈利决策", type="primary", use_container_width=True):
    if len(p1_cards) == 2:
        equity = simulate_multi_equity(p1_cards, board_cards, num_players)
        odds = bet / (pot + bet) if pot+bet > 0 else 0
        ev = (equity * pot) - ((1-equity) * bet)
        
        col_a, col_b = st.columns(2)
        col_a.metric("真实胜率", f"{equity*100:.1f}%")
        col_b.metric("期望盈利 (EV)", f"{ev:+.1f}")
        
        st.markdown("---")
        if equity > odds * 1.2:
            if "疯子" in opp: st.success("🚀 **策略：慢打 (Trap)**。引诱他继续疯狂诈唬，在河牌全下。")
            else: st.success("🚀 **策略：重炮下注**。获取最大价值。")
        elif equity > odds:
            st.warning("✅ **策略：跟注 (Call)**。胜率足以覆盖赔率。")
        else:
            st.error("❌ **策略：止损弃牌 (Fold)**。长期打这把牌是亏损的。")
