import streamlit as st
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection
import graphviz
import pandas as pd

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="TESPy System Designer")
st.title("🌡️ TESPy 통합 시스템 설계기 (v1.0)")

# --- 2. 세션 상태 관리 (데이터 유지) ---
if "connections" not in st.session_state:
    st.session_state.connections = []
if "comp_params" not in st.session_state:
    # 기본 컴포넌트들의 초기 파라미터 셋
    st.session_state.comp_params = {
        "Source_Hot": {"T": 80.0, "p": 1.0, "m": 1.0},
        "Source_Cold": {"T": 20.0, "p": 1.0, "m": 1.0},
        "HeatExchanger": {"pr1": 0.98, "pr2": 0.98},
        "Pump": {"eta_s": 0.8, "P": 1000}
    }

# --- 3. 사이드바: 인터페이스 구성 ---
with st.sidebar:
    st.header("🛠️ 네트워크 빌더")
    tab1, tab2 = st.tabs(["🔗 연결 관리", "📝 수치 설정"])
    
    with tab1:
        st.subheader("새 연결 추가")
        comp_list = ["Source_Hot", "Source_Cold", "HeatExchanger", "Pump", "Sink_Hot", "Sink_Cold"]
        src = st.selectbox("출발 (From)", comp_list)
        trg = st.selectbox("도착 (To)", comp_list)
        
        c1, c2 = st.columns(2)
        s_port = c1.selectbox("출구 포트", ["out1", "out2"], key="src_p")
        t_port = c2.selectbox("입구 포트", ["in1", "in2"], key="trg_p")
        
        if st.button("연결 추가 (+)", use_container_width=True):
            st.session_state.connections.append({
                "source": src, "target": trg, "s_port": s_port, "t_port": t_port
            })
            if src not in st.session_state.comp_params: st.session_state.comp_params[src] = {}
            if trg not in st.session_state.comp_params: st.session_state.comp_params[trg] = {}

        if st.button("초기화 (Reset All)", type="primary"):
            st.session_state.connections = []
            st.rerun()

    with tab2:
        st.subheader("컴포넌트 스펙")
        active_comps = list(set([c['source'] for c in st.session_state.connections] + 
                                [c['target'] for c in st.session_state.connections]))
        
        if not active_comps:
            st.info("연결을 먼저 만드세요.")
        else:
            selected = st.selectbox("수정할 부품", active_comps)
            params = st.session_state.comp_params.get(selected, {})
            
            if "Source" in selected:
                params['T'] = st.number_input("온도 (°C)", value=params.get('T', 20.0))
                params['p'] = st.number_input("압력 (bar)", value=params.get('p', 1.0))
                params['m'] = st.number_input("유량 (kg/s)", value=params.get('m', 1.0))
            elif "HeatExchanger" in selected:
                params['pr1'] = st.slider("압력비 1 (Hot)", 0.5, 1.0, params.get('pr1', 0.98))
                params['pr2'] = st.slider("압력비 2 (Cold)", 0.5, 1.0, params.get('pr2', 0.98))
            elif "Pump" in selected:
                params['eta_s'] = st.slider("효율", 0.1, 1.0, params.get('eta_s', 0.8))
            
            st.session_state.comp_params[selected] = params

# --- 4. 메인 화면: 시각화 및 해석 ---
col_graph, col_res = st.columns([1, 1])

with col_graph:
    st.subheader("🖼️ 시스템 다이어그램")
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', style='filled', color='lightgrey')
    for c in st.session_state.connections:
        dot.edge(c['source'], c['target'], label=f"{c['s_port']}→{c['t_port']}")
    st.graphviz_chart(dot)

with col_res:
    st.subheader("🚀 시뮬레이션 결과")
    if st.button("해석 실행 (Solve)", use_container_width=True):
        try:
            # 네트워크 정의
            nw = Network(fluids=['water'], T_unit='C', p_unit='bar', h_unit='kJ / kg')
            
            # 컴포넌트 객체화
            comps = {}
            # 등장하는 모든 이름을 객체로 변환
            unique_names = list(set([c['source'] for c in st.session_state.connections] + 
                                    [c['target'] for c in st.session_state.connections]))
            for name in unique_names:
                if "Source" in name: comps[name] = Source(name)
                elif "Sink" in name: comps[name] = Sink(name)
                elif "HeatExchanger" in name: comps[name] = HeatExchanger(name)
                elif "Pump" in name: comps[name] = Pump(name)

            # 연결 및 속성 할당 (DOF 에러 방지 핵심 로직)
            tespy_conns = []
            for conn in st.session_state.connections:
                c = Connection(comps[conn['source']], conn['s_port'], 
                               comps[conn['target']], conn['t_port'])
                
                # 만약 출발지가 Source라면, 반드시 T, p, m, fluid를 줘야 함
                if isinstance(comps[conn['source']], Source):
                    p = st.session_state.comp_params.get(conn['source'], {"T": 20, "p": 1, "m": 1})
                    c.set_attr(fluid={'water': 1}, T=p['T'], p=p['p'], m=p['m'])
                
                tespy_conns.append(c)
            
            nw.add_conns(*tespy_conns)
            
            # 컴포넌트 파라미터 강제 할당 (HX, Pump 등)
            for name, obj in comps.items():
                p = st.session_state.comp_params.get(name, {})
                if isinstance(obj, HeatExchanger):
                    obj.set_attr(pr1=p.get('pr1', 0.98), pr2=p.get('pr2', 0.98))
                elif isinstance(obj, Pump):
                    obj.set_attr(eta_s=p.get('eta_s', 0.8))

            # 시뮬레이션
            nw.solve(mode='design')
            
            st.success("✅ 시뮬레이션 성공!")
            st.dataframe(nw.results['Connection'][['m', 'p', 'T', 'h']])
            
        except Exception as e:
            st.error(f"❌ 해석 실패: {e}")
            st.markdown("""
            **문제를 해결하려면?**
            - **입구 조건 확인**: 모든
