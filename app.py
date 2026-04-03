import streamlit as st
import json

def analyze_player_stats(hand_histories, target_player):
    total_hands = 0
    vpip_count = 0
    pfr_count = 0
    aggressive_actions = 0 
    passive_actions = 0    

    for hand in hand_histories:
        if target_player in hand.get('players', []):
            total_hands += 1
            player_actions = hand.get('actions', {}).get(target_player, [])
            
            if not player_actions:
                continue

            if any(act in ['call', 'raise', 'bet'] for act in player_actions):
                vpip_count += 1
            
            if 'raise' in player_actions: 
                pfr_count += 1

            for act in player_actions:
                if act in ['bet', 'raise']:
                    aggressive_actions += 1
                elif act == 'call':
                    passive_actions += 1

    vpip_pct = (vpip_count / total_hands) * 100 if total_hands > 0 else 0
    pfr_pct = (pfr_count / total_hands) * 100 if total_hands > 0 else 0
    
    if passive_actions > 0:
        af = aggressive_actions / passive_actions
    else:
        af = float('inf') if aggressive_actions > 0 else 0.0

    diagnostics = []
    if vpip_pct > 35:
        diagnostics.append("VPIP 过高 (松)：打得太松，参与了太多边缘牌，建议收紧起手牌范围。")
    if (vpip_pct - pfr_pct) > 10:
        diagnostics.append("VPIP/PFR 差距大 (被动)：跟注太多而加注太少，容易被对手剥削，应增加主动性。")
    if af < 1.0 and total_hands > 0:
        diagnostics.append("AF 偏低 (跟注站)：打法过于被动，应在拿到好牌时增加价值下注的频率。")
    if not diagnostics and total_hands > 0:
        diagnostics.append("数据表现均衡，继续保持！")

    return total_hands, vpip_pct, pfr_pct, af, diagnostics

st.set_page_config(page_title="德州扑克数据分析看板", layout="wide")

st.title("📈 德州扑克玩家数据分析看板")
st.markdown("解析牌局日志，自动计算 **VPIP**, **PFR**, **AF** 并生成打法漏洞诊断。")
st.markdown("---")

default_json = """[
    {
        "hand_id": 1,
        "players": ["Hero", "Villain_1"],
        "actions": {"Hero": ["raise", "bet", "fold"], "Villain_1": ["call", "call", "raise"]}
    },
    {
        "hand_id": 2,
        "players": ["Hero", "Villain_1", "Villain_2"],
        "actions": {"Hero": ["fold"], "Villain_1": ["raise", "bet", "bet"], "Villain_2": ["call", "call", "fold"]}
    },
    {
        "hand_id": 3,
        "players": ["Hero", "Villain_2"],
        "actions": {"Hero": ["call", "fold"], "Villain_2": ["raise", "bet"]}
    }
]"""

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 导入牌局记录 (JSON 格式)")
    user_input = st.text_area("在此粘贴你的手牌历史数据：", value=default_json, height=300)
    
    try:
        hand_data = json.loads(user_input)
        all_players = set()
        for hand in hand_data:
            all_players.update(hand.get('players', []))
        all_players = list(all_players)
    except json.JSONDecodeError:
        st.error("JSON 格式错误，请检查输入！")
        all_players = []

with col2:
    st.subheader("⚙️ 分析设置")
    if all_players:
        selected_player = st.selectbox("选择要分析的玩家：", all_players)
        
        if st.button("🚀 生成分析报告", use_container_width=True):
            total, vpip, pfr, af, diagnostics = analyze_player_stats(hand_data, selected_player)
            
            st.markdown("### 📊 核心数据")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("总手数", total)
            m2.metric("VPIP (主动入池)", f"{vpip:.1f}%")
            m3.metric("PFR (翻前加注)", f"{pfr:.1f}%")
            
            af_display = "∞" if af == float('inf') else f"{af:.2f}"
            m4.metric("AF (激进系数)", af_display)
            
            st.markdown("### 🤖 智能诊断")
            for diag in diagnostics:
                if "保持" in diag:
                    st.success(diag)
                else:
                    st.warning(diag)
    else:
        st.info("请在左侧输入有效的牌局数据以继续。")
