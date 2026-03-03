import streamlit as st
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection
import graphviz
import pandas as pd

st.set_page_config(layout="wide", page_title="TESPy Pro Designer")
st.title("🌡️ TESPy 파라미터 제어 시뮬레이터")

# --- 1. 세션 상태 초기화 ---
if "connections" not in st.session_state:
    st.session_state.connections = []
if "comp_params" not in st.session_state:
    st.session_state.comp_params = {} # { 'Source_Hot': {'T': 80, 'p': 1, 'm': 2}, ... }

# --- 2. 사이드바: 네트워크 구성 및 수치 입력 ---
with st.sidebar:
    st.header("🛠️ 설계 및 파라미터")
    
    # A. 연결 관리 탭
    tab1, tab2 = st.tabs(["연결 추가", "수치 입력"])
    
    with tab1:
        comp_options = ["Source_Hot", "Source_Cold", "HeatExchanger", "Pump", "Sink_Hot", "Sink_Cold"]
        src = st.selectbox("출발 (Source)", comp_options)
        trg = st.selectbox("도착 (Target)", comp_options)
        
        c1, c2 = st.columns(2)
        s_port = c1.selectbox("출구 포트", ["out1", "out2"], key="sp")
        t_port = c2.selectbox("입구 포트", ["in1", "in2"], key="tp")
        
        if st.button("연결 추가 (+)", use_container_width=True):
            st.session_state.connections.append({
                "source": src, "target": trg, "s_port": s_port, "t_port": t_port
            })
            # 컴포넌트 파라미터 초기화 (없을 경우만)
            if src not in st.session_state.comp_params: st.session_state.comp_params[src] = {}
            if trg not in st.session_state.comp_params: st.session_state.comp_params[trg] = {}

        if st.button("전체 초기화", type="primary"):
            st.session_state.connections = []
            st.session_state.comp_params = {}
            st.rerun()

    with tab2:
        if not st.session_state.comp_params:
            st.info("먼저 연결을 추가하세요.")
        else:
            selected_comp = st.selectbox("수정할 컴포넌트", list(st.session_state.comp_params.keys()))
            st.subheader(f"📍 {selected_comp} 설정")
            
            # 컴포넌트 종류별 동적 입력창
            if "Source" in selected_comp:
                st.session_state.comp_params[selected_comp]['T'] = st.number_input("온도 (°C)", value=80.0 if "Hot" in selected_comp else 20.0)
                st.session_state.comp_params[selected_comp]['p'] = st.number_input("압력 (bar)", value=1.0)
                st.session_state.comp_params[selected_comp]['m'] = st.number_input("유량 (kg/s)", value=2.0)
            
            elif "Pump" in selected_comp:
                st.session_state.comp_params[selected_comp]['eta_s'] = st.slider("등엔트로피 효율", 0.1, 1.0, 0.8)
                st.session_state.comp_params[selected_comp]['P'] = st.number_input("소비 전력 (W)", value=1000)
            
            elif "HeatExchanger" in selected_comp:
                st.session_state.comp_params[selected_comp]['pr1'] = st.slider("압력비 1 (Hot)", 0.8, 1.0, 0.98)
                st.session_state.comp_params[selected_comp]['pr2'] = st.slider("압력비 2 (Cold)", 0.8, 1.0, 0.98)

# --- 3. 메인 화면: 구조도 및 결과 ---
col_canvas, col_result = st.columns([1, 1])

with col_canvas:
    st.subheader("🖼️ 네트워크 구조도")
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR')
    for conn in st.session_state.connections:
        dot.edge(conn['source'], conn['target'], label=f"{conn['s_port']}→{conn['t_port']}")
    st.graphviz_chart(dot)

with col_result:
    st.subheader("🚀 시뮬레이션 결과")
    if st.button("TESPy 해석 실행", use_container_width=True):
    try:
        nw = Network(fluids=['water'], T_unit='C', p_unit='bar')
        
        # 1. 컴포넌트 생성 (기존과 동일)
        comps = {}
        for name in st.session_state.comp_params.keys():
            if "Source" in name: comps[name] = Source(name)
            elif "Sink" in name: comps[name] = Sink(name)
            elif "HeatExchanger" in name: comps[name] = HeatExchanger(name)
            elif "Pump" in name: comps[name] = Pump(name)

        # 2. 커넥션 및 '모든' Source 조건 할당
        tespy_conns = []
        for conn in st.session_state.connections:
            c = Connection(comps[conn['source']], conn['s_port'], 
                           comps[conn['target']], conn['t_port'])
            
            # 중요: 모든 Source에서 나가는 커넥션에 기본값이라도 할당
            if isinstance(comps[conn['source']], Source):
                p = st.session_state.comp_params.get(conn['source'], {})
                # 유입 조건이 누락되지 않도록 기본값(default) 설정
                c.set_attr(
                    fluid={'water': 1}, 
                    T=p.get('T', 20.0), 
                    p=p.get('p', 1.0), 
                    m=p.get('m', 1.0)
                )
            tespy_conns.append(c)
        
        nw.add_conns(*tespy_conns)
        
        # 3. 컴포넌트 파라미터 강제 할당
        for name, obj in comps.items():
            p = st.session_state.comp_params.get(name, {})
            if isinstance(obj, HeatExchanger):
                # HX는 pr1, pr2가 없으면 에러가 날 확률이 높음
                obj.set_attr(pr1=p.get('pr1', 0.98), pr2=p.get('pr2', 0.98))
            elif isinstance(obj, Pump):
                # 펌프도 효율이나 전력 중 하나는 명시되어야 함
                obj.set_attr(eta_s=p.get('eta_s', 0.8))

        # 해석 전 체크: 커넥션 수가 너무 적으면 에러 메시지 출력
        if len(tespy_conns) < 2:
            st.error("네트워크가 너무 단순합니다. 최소 2개 이상의 연결이 필요합니다.")
        else:
            nw.solve(mode='design')
            st.success("해석 성공!")
            st.dataframe(nw.results['Connection'])

    except Exception as e:
        st.error(f"TESPy Solver 오류: {e}")
        st.info("💡 힌트: 모든 Source에 온도(T), 압력(p), 유량(m)이 입력되었는지 확인하세요.")
