import streamlit as st
from streamlit_react_flow import react_flow
from tespy.networks import Network
from tespy.components import Source, Sink, Pump, HeatExchanger
from tespy.connections import Connection

st.set_page_config(page_title="TESPy Advanced Designer", layout="wide")

# 1. 초기 노드 구성 (열교환기 추가)
if 'nodes' not in st.session_state:
    st.session_state.nodes = [
        {"id": "src_hot", "type": "input", "data": {"label": "Hot Inlet", "comp_type": "source"}, "position": {"x": 50, "y": 50}},
        {"id": "src_cold", "type": "input", "data": {"label": "Cold Inlet", "comp_type": "source"}, "position": {"x": 50, "y": 250}},
        {"id": "hx", "data": {"label": "Heat Exchanger", "comp_type": "heatexchanger"}, "position": {"x": 300, "y": 150}},
        {"id": "snk_hot", "type": "output", "data": {"label": "Hot Outlet", "comp_type": "sink"}, "position": {"x": 550, "y": 50}},
        {"id": "snk_cold", "type": "output", "data": {"label": "Cold Outlet", "comp_type": "sink"}, "position": {"x": 550, "y": 250}},
    ]
if 'edges' not in st.session_state:
    st.session_state.edges = []

# 2. 사이드바 설정
st.sidebar.header("⚙️ Component Parameters")
selected_node_id = st.sidebar.selectbox("Select Node", [n['id'] for n in st.session_state.nodes])
node_data = next(n for n in st.session_state.nodes if n['id'] == selected_node_id)
ctype = node_data['data']['comp_type']

params = {}
with st.sidebar.container():
    if ctype == "source":
        params[f"{selected_node_id}_T"] = st.number_input(f"{selected_node_id} Temp (°C)", value=80 if "hot" in selected_node_id else 20)
        params[f"{selected_node_id}_p"] = st.number_input(f"{selected_node_id} Press (bar)", value=1.0)
    elif ctype == "heatexchanger":
        params[f"{selected_node_id}_pr1"] = st.slider("Pressure Ratio Side 1", 0.8, 1.0, 0.98)
        params[f"{selected_node_id}_pr2"] = st.slider("Pressure Ratio Side 2", 0.8, 1.0, 0.98)

# 3. 메인 인터페이스
col1, col2 = st.columns([3, 1])
with col1:
    elements = react_flow("tespy_canvas", nodes=st.session_state.nodes, edges=st.session_state.edges)

with col2:
    st.subheader("Solve")
    if st.button("Run Simulation", use_container_width=True):
        try:
            # 네트워크 설정 (다중 유체 대응을 위해 리스트업)
            nw = Network(fluids=['water'], T_unit='C', p_unit='bar')
            
            # 컴포넌트 객체화
            comps = {}
            for node in elements['nodes']:
                nid, ct = node['id'], node['data']['comp_type']
                if ct == "source": comps[nid] = Source(nid)
                elif ct == "sink": comps[nid] = Sink(nid)
                elif ct == "heatexchanger": comps[nid] = HeatExchanger(nid)
            
            # 연결 로직 (포트 매핑 핵심)
            conns = []
            for edge in elements['edges']:
                s_id, t_id = edge['source'], edge['target']
                # React-flow의 handle ID가 없으면 기본값 in1, out1 사용
                s_port = edge.get('sourceHandle', 'out1')
                t_port = edge.get('targetHandle', 'in1')
                
                # 열교환기 판별 (Hot/Cold 입출력 매핑)
                # 실제 구현 시 React-flow 노드에서 핸들 ID를 'in1', 'in2' 등으로 넘겨줘야 함
                c = Connection(comps[s_id], s_port, comps[t_id], t_port)
                
                # 소스 노드인 경우 경계 조건 할당
                if isinstance(comps[s_id], Source):
                    c.set_attr(fluid={'water': 1}, 
                               T=params.get(f"{s_id}_T", 20), 
                               p=params.get(f"{s_id}_p", 1), 
                               m=2)
                conns.append(c)
            
            nw.add_conns(*conns)
            
            # 열교환기 특성 할당
            for nid, obj in comps.items():
                if isinstance(obj, HeatExchanger):
                    obj.set_attr(pr1=params.get(f"{nid}_pr1", 0.98), 
                                 pr2=params.get(f"{nid}_pr2", 0.98))
            
            nw.solve(mode='design')
            st.success("Analysis Complete!")
            st.dataframe(nw.results['Connection'])
            
        except Exception as e:
            st.error(f"Error: {e}")
