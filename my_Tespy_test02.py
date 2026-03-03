import streamlit as st
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection
import graphviz
import pandas as pd

st.set_page_config(layout="wide", page_title="TESPy Designer")
st.title("🌡️ TESPy 시각적 네트워크 설계기")

# 1. 세션 상태에 네트워크 데이터 저장
if "connections" not in st.session_state:
    st.session_state.connections = [] # [{'source': 'src1', 'target': 'hx1', 's_port': 'out1', 't_port': 'in1'}]

# 2. 레이아웃 분할
col_input, col_canvas = st.columns([1, 2])

with col_input:
    st.header("🔗 연결 추가")
    comp_list = ["Source_Hot", "Source_Cold", "HeatExchanger", "Pump", "Sink_Hot", "Sink_Cold"]
    
    src = st.selectbox("출발 컴포넌트 (Source)", comp_list)
    trg = st.selectbox("도착 컴포넌트 (Target)", comp_list)
    
    # 열교환기용 포트 선택 (다중 포트 대응)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        s_port = st.selectbox("출구 포트", ["out1", "out2"])
    with col_p2:
        t_port = st.selectbox("입구 포트", ["in1", "in2"])

    if st.button("연결 추가 (+)", use_container_width=True):
        st.session_state.connections.append({
            "source": src, "target": trg, "s_port": s_port, "t_port": t_port
        })
    
    if st.button("초기화 (Reset)", type="primary"):
        st.session_state.connections = []
        st.rerun()

with col_canvas:
    st.header("🖼️ 네트워크 구조도")
    # Graphviz를 이용한 시각화
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR') # 왼쪽에서 오른쪽으로 흐름
    
    for conn in st.session_state.connections:
        label = f"{conn['s_port']} → {conn['t_port']}"
        dot.edge(conn['source'], conn['target'], label=label)
    
    st.graphviz_chart(dot)

# 3. TESPy 시뮬레이션 섹션
st.divider()
if st.button("🚀 TESPy 해석 실행", use_container_width=True):
    if not st.session_state.connections:
        st.warning("먼저 컴포넌트를 연결해 주세요.")
    else:
        try:
            nw = Network(fluids=['water'], T_unit='C', p_unit='bar')
            
            # 컴포넌트 객체 생성 자동화
            comps = {}
            for conn in st.session_state.connections:
                for name in [conn['source'], conn['target']]:
                    if name not in comps:
                        if "Source" in name: comps[name] = Source(name)
                        elif "Sink" in name: comps[name] = Sink(name)
                        elif "HeatExchanger" in name: comps[name] = HeatExchanger(name)
                        elif "Pump" in name: comps[name] = Pump(name)

            # 커넥션 객체 생성
            tespy_conns = []
            for conn in st.session_state.connections:
                c = Connection(comps[conn['source']], conn['s_port'], 
                               comps[conn['target']], conn['t_port'])
                
                # 기본 경계 조건 (Source일 경우)
                if isinstance(comps[conn['source']], Source):
                    c.set_attr(fluid={'water': 1}, m=2, p=1, T=80 if "Hot" in conn['source'] else 20)
                
                tespy_conns.append(c)
            
            nw.add_conns(*tespy_conns)
            
            # 열교환기 기본 설정
            for obj in comps.values():
                if isinstance(obj, HeatExchanger):
                    obj.set_attr(pr1=0.98, pr2=0.98)

            nw.solve(mode='design')
            
            st.success("해석 완료!")
            st.dataframe(nw.results['Connection'])
            
        except Exception as e:
            st.error(f"해석 오류: {e}")
