import streamlit as st
from streamlit_react_flow import react_flow
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection
import pandas as pd

st.set_page_config(layout="wide")
st.title("🔗 React-flow 기반 열유체 네트워크 설계기")

# 1. 노드 및 에지(연결선) 초기 설정
# 각 노드의 'data' 필드에 TESPy 컴포넌트 타입을 지정합니다.
initial_nodes = [
    {"id": "source_1", "type": "input", "data": {"label": "Source (Inlet)", "comp_type": "source"}, "position": {"x": 50, "y": 50}},
    {"id": "pump_1", "data": {"label": "Pump", "comp_type": "pump"}, "position": {"x": 250, "y": 50}},
    {"id": "sink_1", "type": "output", "data": {"label": "Sink (Outlet)", "comp_type": "sink"}, "position": {"x": 450, "y": 50}},
]
initial_edges = []

# 2. React-flow 인터페이스 레이아웃
col_canvas, col_settings = st.columns([3, 1])

with col_canvas:
    st.subheader("Network Canvas (Drag to Connect)")
    # 사용자가 웹에서 노드를 움직이거나 선을 연결하면 elements가 업데이트됩니다.
    elements = react_flow("tespy_flow", nodes=initial_nodes, edges=initial_edges, interactive=True)

with col_settings:
    st.subheader("Parameters")
    fluid = st.selectbox("Fluid", ["water", "air"])
    p_in = st.number_input("Inlet Pressure (bar)", value=1.0)
    t_in = st.number_input("Inlet Temp (°C)", value=20.0)
    mass_flow = st.number_input("Mass Flow (kg/s)", value=2.0)
    run_button = st.button("🚀 Run TESPy Solve")

# 3. React-flow 데이터를 TESPy 모델로 변환하는 핵심 로직
def build_tespy_from_flow(flow_data):
    nw = Network(fluids=[fluid], T_unit='C', p_unit='bar', h_unit='kJ / kg')
    
    # 노드 ID를 키로, TESPy 객체를 값으로 하는 딕셔너리
    comps = {}
    
    # A. 노드 생성
    for node in flow_data['nodes']:
        n_id = node['id']
        c_type = node['data']['comp_type']
        
        if c_type == "source": comps[n_id] = Source(n_id)
        elif c_type == "sink": comps[n_id] = Sink(n_id)
        elif c_type == "pump": comps[n_id] = Pump(n_id)
        elif c_type == "heat_exchanger": comps[n_id] = HeatExchanger(n_id)

    # B. 에지(연결선) 생성 및 TESPy Connection 설정
    conns = []
    for edge in flow_data['edges']:
        source_id = edge['source']
        target_id = edge['target']
        
        # 실제 TESPy 객체 연결
        c = Connection(comps[source_id], 'out1', comps[target_id], 'in1')
        
        # 첫 번째 연결선(Source 출발)에 경계 조건 부여
        if comps[source_id].__class__.__name__ == 'Source':
            c.set_attr(fluid={fluid: 1}, m=mass_flow, p=p_in, T=t_in)
        
        conns.append(c)
    
    nw.add_conns(*conns)
    
    # 펌프 등 개별 컴포넌트 기본 특성 부여 (예시)
    for c in comps.values():
        if isinstance(c, Pump):
            c.set_attr(eta_s=0.8, P=1000) # 기본값 설정
            
    return nw

# 4. 실행 결과 출력
if run_button and elements:
    try:
        nw_model = build_tespy_from_flow(elements)
        nw_model.solve(mode='design')
        
        st.divider()
        st.success("해석 완료!")
        st.dataframe(nw_model.results['Connection'])
    except Exception as e:
        st.error(f"해석 중 오류 발생: {e}")
