import streamlit as st
from streamlit_elements import elements, mui, html, sync, event
from streamlit_elements import nivo # 결과 시각화용 (선택)
import json

# TESPy 관련 임포트
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection
import pandas as pd

# 페이지 설정
st.set_page_config(layout="wide", page_title="TESPy Flow Designer")
st.title("🌡️ TESPy React-Flow Designer")

# --- 1. 세션 상태 초기화 (노드 및 에지 저장) ---
if "nodes" not in st.session_state:
    st.session_state.nodes = [
        {"id": "src_hot", "type": "input", "data": {"label": "Hot Source", "type": "source"}, "position": {"x": 50, "y": 50}},
        {"id": "src_cold", "type": "input", "data": {"label": "Cold Source", "type": "source"}, "position": {"x": 50, "y": 250}},
        {"id": "hx", "data": {"label": "Heat Exchanger", "type": "heatexchanger"}, "position": {"x": 300, "y": 150}},
        {"id": "snk_hot", "type": "output", "data": {"label": "Hot Sink", "type": "sink"}, "position": {"x": 550, "y": 50}},
        {"id": "snk_cold", "type": "output", "data": {"label": "Cold Sink", "type": "sink"}, "position": {"x": 550, "y": 250}},
    ]
if "edges" not in st.session_state:
    st.session_state.edges = []

# --- 2. 사이드바: 컴포넌트 파라미터 입력 ---
st.sidebar.header("⚙️ Component Settings")
all_node_ids = [n['id'] for n in st.session_state.nodes]
target_id = st.sidebar.selectbox("Select Node", all_node_ids)

# 컴포넌트별 설정 값 저장소 (간소화를 위해 딕셔너리 사용)
if "params" not in st.session_state:
    st.session_state.params = {}

with st.sidebar:
    selected_node = next(n for n in st.session_state.nodes if n['id'] == target_id)
    ctype = selected_node['data']['type']
    
    st.subheader(f"Editing: {target_id}")
    if ctype == "source":
        st.session_state.params[f"{target_id}_T"] = st.number_input("Temp (°C)", value=80.0 if "hot" in target_id else 20.0, key=f"t_{target_id}")
        st.session_state.params[f"{target_id}_p"] = st.number_input("Pressure (bar)", value=1.0, key=f"p_{target_id}")
        st.session_state.params[f"{target_id}_m"] = st.number_input("Mass Flow (kg/s)", value=2.0, key=f"m_{target_id}")
    elif ctype == "heatexchanger":
        st.session_state.params[f"{target_id}_pr1"] = st.slider("Pressure Ratio 1", 0.0, 1.0, 0.98)
        st.session_state.params[f"{target_id}_pr2"] = st.slider("Pressure Ratio 2", 0.0, 1.0, 0.98)

# --- 3. React-flow 캔버스 구현 ---
# streamlit-elements는 자바스크립트 기반 React 라이브러리를 직접 호출합니다.
with elements("tespy_designer"):
    from streamlit_elements import react_flow
    
    with mui.Box(sx={"height": 500, "border": 1, "borderColor": "divider", "borderRadius": 1}):
        react_flow.ReactFlow(
            nodes=st.session_state.nodes,
            edges=st.session_state.edges,
            onNodesChange=sync("nodes"), # 위치 이동 시 자동 저장
            onEdgesChange=sync("edges"), # 연결 변경 시 자동 저장
            onConnect=event.remotely(lambda params: st.session_state.edges.append(params)),
            fitView=True
        )

# --- 4. TESPy Solver 실행 로직 ---
if st.button("🚀 Run TESPy Simulation", use_container_width=True):
    try:
        nw = Network(fluids=['water'], T_unit='C', p_unit='bar', h_unit='kJ / kg')
        
        # A. 컴포넌트 생성
        comps = {}
        for node in st.session_state.nodes:
            nid, ct = node['id'], node['data']['type']
            if ct == "source": comps[nid] = Source(nid)
            elif ct == "sink": comps[nid] = Sink(nid)
            elif ct == "pump": comps[nid] = Pump(nid)
            elif ct == "heatexchanger": comps[nid] = HeatExchanger(nid)

        # B. 에지 연결 및 다중 포트 처리
        conns = []
        for edge in st.session_state.edges:
            sid, tid = edge['source'], edge['target']
            
            # 포트 핸들 로직 (열교환기의 경우 in1, in2 구분)
            # React-flow의 Handle ID가 'in2' 등으로 설정되어 있다고 가정하거나
            # 여기서는 연결 순서나 ID 이름을 기준으로 로직을 짤 수 있습니다.
            s_port = edge.get('sourceHandle', 'out1')
            t_port = edge.get('targetHandle', 'in1')
            
            # 실제 연결
            c = Connection(comps[sid], s_port, comps[tid], t_port)
            
            # Source 경계 조건 부여
            if isinstance(comps[sid], Source):
                p = st.session_state.params
                c.set_attr(fluid={'water': 1}, 
                           m=p.get(f"{sid}_m", 2), 
                           p=p.get(f"{sid}_p", 1), 
                           T=p.get(f"{sid}_T", 20))
            conns.append(c)

        nw.add_conns(*conns)
        
        # C. 컴포넌트 파라미터 부여
        for nid, obj in comps.items():
            if isinstance(obj, HeatExchanger):
                p = st.session_state.params
                obj.set_attr(pr1=p.get(f"{nid}_pr1", 0.98), pr2=p.get(f"{nid}_pr2", 0.98))

        # D. 풀이
        nw.solve(mode='design')
        
        st.divider()
        st.success("해석 성공!")
        st.dataframe(nw.results['Connection'])

    except Exception as e:
        st.error(f"해석 실패: {e}")
        st.info("Tip: 모든 컴포넌트가 올바른 포트(in1, out1 등)로 연결되었는지 확인하세요.")
