import streamlit as st
from streamlit_drawable_canvas import st_canvas
from tespy.networks import Network
from tespy.components import Source, Sink, HeatExchanger, Pump
from tespy.connections import Connection

st.title("🎨 Draw your Thermal Network")

# 1. 사이드바에서 컴포넌트 타입 선택
comp_type = st.sidebar.selectbox("Select Component to Draw", ["Source", "Sink", "Pump", "HeatExchanger"])
drawing_mode = st.sidebar.selectbox("Drawing tool:", ("rect", "line")) # rect는 컴포넌트, line은 커넥션

# 2. 캔버스 설정
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",  # 도형 내부 색상
    stroke_width=3,
    stroke_color="#000",
    background_color="#eee",
    height=400,
    drawing_mode=drawing_mode,
    key="canvas",
)

# 3. 캔버스 데이터를 TESPy 네트워크로 변환하는 로직
if st.button("Build & Solve Network"):
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        
        # 실제 구현 시에는 각 도형의 ID와 좌표를 저장하여 TESPy 객체와 매핑합니다.
        # 여기서는 개념 증명을 위해 감지된 객체의 개수를 출력합니다.
        components_found = [obj for obj in objects if obj["type"] == "rect"]
        connections_found = [obj for obj in objects if obj["type"] == "line"]
        
        st.write(f"Detected {len(components_found)} Components and {len(connections_found)} Connections.")

        # 시뮬레이션 엔진 가동 (예시)
        try:
            nw = Network(fluids=['water'], T_unit='C', p_unit='bar')
            
            # (심화 로직 필요) objects의 좌표를 분석하여 
            # 선(line)의 시작점과 끝점에 있는 사각형(rect)을 찾아 
            # Connection(comp1, 'out1', comp2, 'in1')을 자동으로 생성합니다.
            
            st.success("네트워크 구조가 성공적으로 인식되었습니다! (상세 매핑 로직 구현 필요)")
        except Exception as e:
            st.error(f"Error: {e}")
