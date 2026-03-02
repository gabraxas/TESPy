import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tespy.networks import Network
from tespy.components import Turbine, Condenser, Pump, SimpleHeatExchanger
from tespy.connections import Connection
from fluprodia import FluidPropertyDiagram

# 1. 페이지 설정
st.set_page_config(page_title="TESPy + fluprodia Dashboard", layout="wide")
st.title("♨️ Professional T-s Diagram with fluprodia")

# 2. 사이드바 제어판 (입력값)
st.sidebar.header("System Settings")
p_live = st.sidebar.slider("Live Steam Pressure (bar)", 10.0, 150.0, 60.0)
t_live = st.sidebar.slider("Live Steam Temperature (°C)", 300, 600, 480)
p_cond = st.sidebar.slider("Condenser Pressure (bar)", 0.05, 1.0, 0.1)

if st.button("🚀 Run Simulation & Plot"):
    # --- TESPy 시뮬레이션 파트 ---
    nw = Network(fluids=['water'], T_unit='C', p_unit='bar', h_unit='kJ / kg', s_unit='kJ / kgK')
    
    sg = SimpleHeatExchanger('Boiler')
    tur = Turbine('Turbine')
    con = Condenser('Condenser')
    pu = Pump('Pump')
    
    c1 = Connection(sg, 'out1', tur, 'in1', label='1')
    c2 = Connection(tur, 'out1', con, 'in1', label='2')
    c3 = Connection(con, 'out1', pu, 'in1', label='3')
    c4 = Connection(pu, 'out1', sg, 'in1', label='4')
    nw.add_conns(c1, c2, c3, c4)
    
    c1.set_attr(p=p_live, T=t_live, m=10)
    c2.set_attr(p=p_cond)
    tur.set_attr(eta_s=0.85)
    pu.set_attr(eta_s=0.8)
    sg.set_attr(pr=1.0)
    
    try:
        nw.solve(mode='design')
        st.success("Simulation Success!")

        # --- fluprodia를 이용한 T-s 선도 생성 파트 ---
        diagram = FluidPropertyDiagram('water')
        diagram.set_unit_system(T='°C', p='bar', h='kJ/kg')

        # 컴포넌트 데이터 추출 (제공해주신 로직 적용)
        result_dict = {}
        # TESPy 컴포넌트 리스트를 순회하며 플로팅 데이터 획득
        for comp in [sg, tur, con, pu]:
            plotting_data = comp.get_plotting_data()
            if plotting_data is not None:
                result_dict[comp.label] = plotting_data[1]

        for key, data in result_dict.items():
            result_dict[key]['datapoints'] = diagram.calc_individual_isoline(**data)

        # Plot 생성
        fig, ax = plt.subplots(figsize=(10, 6))
        isolines = {
            'Q': np.linspace(0, 1, 11), # 등건도선 추가
            'p': np.array([1, 5, 10, 50, 100, 150]),
            'h': np.arange(500, 4001, 500)
        }
        diagram.set_isolines(**isolines)
        diagram.calc_isolines()
        
        # T-s 배경 그리기 (x_max는 J/kgK 단위이므로 주의)
        diagram.draw_isolines(fig, ax, 'Ts', x_min=0, x_max=9000, y_min=0, y_max=650)

        # 사이클 선 그리기
        for key in result_dict.keys():
            datapoints = result_dict[key]['datapoints']
            ax.plot(datapoints['s'], datapoints['T'], color='#ff0000', linewidth=2.5)
            ax.scatter(datapoints['s'][0], datapoints['T'][0], color='#ff0000', s=30)

        ax.set_xlabel('Entropy (J/kgK)')
        ax.set_ylabel('Temperature (°C)')
        ax.set_title('T-s Diagram of Rankine Cycle (fluprodia)')

        # Streamlit에 차트 표시
        st.pyplot(fig)
        
        # 결과 데이터 테이블 출력
        st.subheader("Process Data")
        st.dataframe(nw.results['Connection'][['p', 'T', 'h', 's', 'x']])

    except Exception as e:
        st.error(f"Simulation Error: {e}")
