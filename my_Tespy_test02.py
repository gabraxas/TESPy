import streamlit as st
from tespy.networks import Network
from tespy.components import Sink, Source, HeatExchanger
from tespy.connections import Connection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="TESPy Thermal Network Designer", layout="wide")
st.title("🌡️ TESPy 열유체 네트워크 시뮬레이터")

# 2. 사이드바: 유저 입력 인터페이스
st.sidebar.header("Network Parameters")
fluid = st.sidebar.selectbox("Fluid Type", ["water", "air", "NH3"])
p_in = st.sidebar.slider("Inlet Pressure (bar)", 1.0, 20.0, 10.0)
t_in = st.sidebar.slider("Inlet Temperature (°C)", 10, 200, 80)
m_flow = st.sidebar.number_input("Mass Flow (kg/s)", value=5.0)

if st.sidebar.button("Run Simulation"):
    try:
        # 3. TESPy 네트워크 구축
        nw = Network(fluids=[fluid], T_unit='C', p_unit='bar', h_unit='kJ / kg')
        
        # 컴포넌트 생성
        so1 = Source('Hot Source')
        si1 = Sink('Hot Sink')
        so2 = Source('Cold Source')
        si2 = Sink('Cold Sink')
        hx = HeatExchanger('Heat Exchanger')
        
        # 커넥션 설정
        c1 = Connection(so1, 'out1', hx, 'in1', label='hot_in')
        c2 = Connection(hx, 'out1', si1, 'in1', label='hot_out')
        c3 = Connection(so2, 'out1', hx, 'in2', label='cold_in')
        c4 = Connection(hx, 'out2', si2, 'in1', label='cold_out')
        
        nw.add_conns(c1, c2, c3, c4)
        
        # 경계 조건 입력
        c1.set_attr(fluid={fluid: 1}, m=m_flow, p=p_in, T=t_in)
        c3.set_attr(fluid={fluid: 1}, p=2, T=20)
        hx.set_attr(pr1=0.98, pr2=0.98, ttd_u=5)
        
        # 4. 시뮬레이션 실행
        nw.solve(mode='design')
        
        # 5. 결과 출력
        st.success("Simulation Successful!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Connection Results")
            st.dataframe(nw.results['Connection'])
            
        with col2:
            st.subheader("Component Results")
            st.dataframe(nw.results['HeatExchanger'])

    except Exception as e:
        st.error(f"Error during simulation: {e}")

else:
    st.info("왼쪽 사이드바에서 파라미터를 설정하고 'Run Simulation'을 클릭하세요.")
