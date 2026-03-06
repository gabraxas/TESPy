import streamlit as st
from tespy.networks import Network
from tespy.components import (
    CycleCloser, Compressor, Condenser, Valve, 
    Sink, Source, Turbine, HeatExchanger
)
from tespy.connections import Connection, Bus
from tespy.tools import ExergyAnalysis

import graphviz
import pandas as pd
import plotly.graph_objects as go


def draw_example_refrigeration_cycle():
    """
    Streamlit '시스템 다이어그램' 영역에서 참고용으로 보여줄
    기본 냉동 사이클(증기 압축 냉동 사이클) 예시 그림을 생성한다.
    """
    dot_ex = graphviz.Digraph()
    dot_ex.attr(rankdir='LR', bgcolor='#ffffff')

    # 노드 스타일
    node_style = {
        "style": "filled",
        "shape": "box",
        "fontname": "NanumGothic, Malgun Gothic, Arial",
        "fontsize": "10"
    }

    # 기본 사이클 노드
    dot_ex.node("Evap",   "Evaporator\n(증발기)",  fillcolor="#80cbc4", **node_style)
    dot_ex.node("Comp",   "Compressor\n(압축기)", fillcolor="#ffcc80", **node_style)
    dot_ex.node("Cond",   "Condenser\n(응축기)",  fillcolor="#ef9a9a", **node_style)
    dot_ex.node("Valve",  "Expansion Valve\n(팽창밸브)", fillcolor="#ce93d8", **node_style)

    # 화살표 및 상태점 (1~4)
    edge_style = {"fontsize": "9", "fontname": "NanumGothic, Malgun Gothic, Arial"}

    dot_ex.edge("Evap", "Comp",   label="1 → 2\n저압·저온 증기", **edge_style)
    dot_ex.edge("Comp", "Cond",   label="2 → 3\n고압·고온 증기", **edge_style)
    dot_ex.edge("Cond", "Valve",  label="3 → 4\n고압 액",       **edge_style)
    dot_ex.edge("Valve","Evap",   label="4 → 1\n저압 액/증기 혼합", **edge_style)

    # 간단한 설명 박스
    dot_ex.attr(label=(
        "기본 증기 압축 냉동 사이클 예시\n"
        "1: 증발기 출구 (저압·저온 증기)\n"
        "2: 압축기 출구 (고압·고온 증기)\n"
        "3: 응축기 출구 (고압 액)\n"
        "4: 팽창밸브 출구 (저��� 액/증기 혼합)"
    ))
    dot_ex.attr(labelloc="b", fontsize="9")

    st.graphviz_chart(dot_ex, use_container_width=True)


# ─────────────────────────────────────────────
# Exergy 네트워크 예시 (간단 버전, 버튼으로 실행)
# ─────────────────────────────────────────────

def run_exergy_example():
    """
    간단한 TESPy 네트워크 + ExergyAnalysis 예시를 실행하고
    COP 비슷한 지표 및 Sankey를 반환하는 헬퍼 함수.

    원본 예시 구조를 최대한 유지하되,
    - 파일 출력, CSV 검증 등은 생략
    - Streamlit에 표시하기 좋은 형태로 요약
    """

    # ambient state
    pamb = 1
    Tamb = 25

    # setting up network
    nw = Network()
    nw.set_attr(
        T_unit='C', p_unit='bar', h_unit='kJ / kg', m_unit='kg / s',
        s_unit="kJ / kgK"
    )

    # components definition
    water_in = Source('Water source')
    water_out = Sink('Water sink')

    air_in = Source('Air source')
    air_out = Sink('Air sink')

    closer = CycleCloser('Cycle closer')

    cp = Compressor('Compressor')
    turb = Turbine('Turbine')

    cold = HeatExchanger('Cooling heat exchanger')
    hot = HeatExchanger('Heat sink heat exchanger')

    # connections definition
    # power cycle
    c0 = Connection(cold, 'out2', closer, 'in1', label='0')
    c1 = Connection(closer, 'out1', cp, 'in1', label='1')
    c2 = Connection(cp, 'out1', hot, 'in1', label='2')
    c3 = Connection(hot, 'out1', turb, 'in1', label='3')
    c4 = Connection(turb, 'out1', cold, 'in2', label='4')

    c11 = Connection(air_in, 'out1', cold, 'in1', label='11')
    c12 = Connection(cold, 'out1', air_out, 'in1', label='12')

    c21 = Connection(water_in, 'out1', hot, 'in2', label='21')
    c22 = Connection(hot, 'out2', water_out, 'in1', label='22')

    # add connections to network
    nw.add_conns(c0, c1, c2, c3, c4, c11, c12, c21, c22)

    # power bus
    power = Bus('power input')
    power.add_comps(
        {'comp': turb, 'char': 1, 'base': 'component'},
        {'comp': cp, 'char': 1, 'base': 'bus'}
    )

    cool_product_bus = Bus('cooling')
    cool_product_bus.add_comps(
        {'comp': air_in, 'base': 'bus'},
        {'comp': air_out}
    )

    heat_loss_bus = Bus('heat sink')
    heat_loss_bus.add_comps(
        {'comp': water_in, 'base': 'bus'},
        {'comp': water_out}
    )

    nw.add_busses(power, cool_product_bus, heat_loss_bus)

    # connection parameters
    c0.set_attr(T=-30, p=1, fluid={'Air': 1, 'water': 0})
    c2.set_attr(p=5.25)
    c3.set_attr(p=5, T=35)
    c4.set_attr(p=1.05)

    c11.set_attr(fluid={'Air': 1, 'water': 0}, T=-10, p=1)
    c12.set_attr(p=1, T=-20)

    c21.set_attr(fluid={'Air': 0, 'water': 1}, T=25, p=1.5)
    c22.set_attr(p=1.5, T=40)

    # component parameters
    turb.set_attr(eta_s=0.8)
    cp.set_attr(eta_s=0.8)
    cold.set_attr(Q=-100e3)

    # 1차 해석
    nw.solve(mode='design')

    # 효율 조정 (원본 예시의 eta 사용)
    eta = 0.961978
    nw.del_busses(power)
    power = Bus('power input')
    power.add_comps(
        {'comp': turb, 'char': eta, 'base': 'component'},
        {'comp': cp, 'char': eta, 'base': 'bus'}
    )
    nw.add_busses(power)
    nw.solve(mode='design')

    # Exergy 분석
    ean = ExergyAnalysis(
        nw,
        E_P=[cool_product_bus],
        E_F=[power],
        E_L=[heat_loss_bus]
    )
    ean.analyse(pamb=pamb, Tamb=Tamb)

    # Sankey 입력
    links, nodes = ean.generate_plotly_sankey_input(display_thresold=1000)
    # 정규화 (연료 exergy 기준)
    if links['value']:
        base = links['value'][0]
        if base != 0:
            links['value'] = [v / base for v in links['value']]

    # 간단한 성능 지표: Exergy 효율 및 주요 exergy 흐름 요약
    # (ean.network_data는 Series)
    net_data = ean.network_data
    epsilon = float(net_data.get('epsilon', float('nan')))
    E_F = float(net_data.get('E_F', float('nan')))
    E_P = float(net_data.get('E_P', float('nan')))
    E_L = float(net_data.get('E_L', float('nan')))

    return {
        "nw": nw,
        "ean": ean,
        "links": links,
        "nodes": nodes,
        "epsilon": epsilon,
        "E_F": E_F,
        "E_P": E_P,
        "E_L": E_L
    }


# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="TESPy Refrigerator Designer")
st.title("❄️ TESPy 냉동 사이클 시스템 설계기 (v2.0)")

# --- 냉동 사이클 고정 컴포넌트 목록 ---
REFRIG_COMP_LIST = ["CycleCloser", "Compressor", "Condenser", "Valve", "Evaporator"]

# --- 2. 세션 상태 관리 (데이터 유지) ---
if "connections" not in st.session_state:
    st.session_state.connections = []
if "comp_params" not in st.session_state:
    # 냉동 사이클 기본 파라미터 셋
    st.session_state.comp_params = {
        "CycleCloser": {},
        "Compressor":  {"eta_s": 0.8},
        "Condenser":   {"pr": 0.99, "T_out": 40.0, "x_out": 0.0},
        "Valve":       {"pr": 1.0},
        "Evaporator":  {"pr": 0.99, "T_out": 5.0,  "x_out": 1.0},
    }
if "fluid" not in st.session_state:
    st.session_state.fluid = "R134a"
if "mass_flow" not in st.session_state:
    st.session_state.mass_flow = 0.05

# --- 3. 사이드바: 인터페이스 구성 ---
with st.sidebar:
    st.header("🛠️ 냉동 사이클 빌더")

    # 냉매 선택
    st.session_state.fluid = st.selectbox(
        "냉매 선택", ["R134a", "R22", "R410A", "R32", "R600a"],
        index=["R134a", "R22", "R410A", "R32", "R600a"].index(st.session_state.fluid)
    )
    st.session_state.mass_flow = st.number_input(
        "냉매 유량 (kg/s)", min_value=0.001, value=st.session_state.mass_flow, step=0.005
    )
    st.divider()

    tab1, tab2 = st.tabs(["🔗 연결 관리", "📝 수치 설정" ])

    with tab1:
        st.subheader("새 연결 추가")
        src = st.selectbox("출발 (From)", REFRIG_COMP_LIST, key="sel_src")
        trg = st.selectbox("도착 (To)",   REFRIG_COMP_LIST, key="sel_trg")

        c1, c2 = st.columns(2)
        s_port = c1.selectbox("출구 포트", ["out1", "out2"], key="src_p")
        t_port = c2.selectbox("입구 포트", ["in1", "in2"],  key="trg_p")

        if st.button("연결 추가 (+)", use_container_width=True):
            st.session_state.connections.append({
                "source": src, "target": trg,
                "s_port": s_port, "t_port": t_port
            })

        # 표준 냉동 사이클 자동 구성 버튼
        if st.button("🔄 표준 냉동 사이클 자동 구성", use_container_width=True):
            st.session_state.connections = [
                {"source": "CycleCloser", "target": "Compressor", "s_port": "out1", "t_port": "in1"},
                {"source": "Compressor",  "target": "Condenser",  "s_port": "out1", "t_port": "in1"},
                {"source": "Condenser",   "target": "Valve",      "s_port": "out1", "t_port": "in1"},
                {"source": "Valve",       "target": "Evaporator", "s_port": "out1", "t_port": "in1"},
                {"source": "Evaporator",  "target": "CycleCloser","s_port": "out1", "t_port": "in1"},
            ]
            st.rerun()

        if st.button("초기화 (Reset All)", type="primary", use_container_width=True):
            st.session_state.connections = []
            st.rerun()

        # 현재 연결 목록 표시
        if st.session_state.connections:
            st.subheader("현재 연결 목록")
            for i, c in enumerate(st.session_state.connections):
                cols = st.columns([4, 1])
                cols[0].caption(f"{i+1}. {c['source']}({c['s_port']}) → {c['target']}({c['t_port']})")
                if cols[1].button("❌", key=f"del_{i}"):
                    st.session_state.connections.pop(i)
                    st.rerun()

    with tab2:
        st.subheader("컴포넌트 스펙")
        active_comps = list(dict.fromkeys(
            [c['source'] for c in st.session_state.connections] +
            [c['target'] for c in st.session_state.connections]
        ))

        if not active_comps:
            st.info("연결을 먼저 만드세요.")
        else:
            selected = st.selectbox("수정할 부품", active_comps)
            params = st.session_state.comp_params.get(selected, {})

            if selected == "Compressor":
                params['eta_s'] = st.slider(
                    "등엔트로피 효율 (η_s)", 0.1, 1.0,
                    float(params.get('eta_s', 0.8)), step=0.01
                )

            elif selected == "Condenser":
                params['pr']    = st.slider(
                    "압력비 (pr)", 0.5, 1.0, float(params.get('pr', 0.99)), step=0.01
                )
                params['T_out'] = st.number_input(
                    "응축 출구 온도 (°C)", value=float(params.get('T_out', 40.0))
                )
                params['x_out'] = st.number_input(
                    "응축 출구 건도 (x, 0=포화액)", min_value=0.0, max_value=1.0,
                    value=float(params.get('x_out', 0.0)), step=0.1
                )

            elif selected == "Evaporator":
                params['pr']    = st.slider(
                    "압력비 (pr)", 0.5, 1.0, float(params.get('pr', 0.99)), step=0.01
                )
                params['T_out'] = st.number_input(
                    "증발 출구 온도 (°C)", value=float(params.get('T_out', 5.0))
                )
                params['x_out'] = st.number_input(
                    "증발 출구 건도 (x, 1=포화증기)", min_value=0.0, max_value=1.0,
                    value=float(params.get('x_out', 1.0)), step=0.1
                )

            elif selected == "Valve":
                params['pr'] = st.slider(
                    "압력비 (pr, 1.0=계산값 자동)", 0.01, 1.0,
                    float(params.get('pr', 1.0)), step=0.01
                )

            elif selected == "CycleCloser":
                st.info("CycleCloser는 설정 파라미터가 없습니다.")

            st.session_state.comp_params[selected] = params

# --- 4. 메인 화면: 시각화 및 해석 ---
col_graph, col_res = st.columns([1, 1])

with col_graph:
    st.subheader("🖼️ 시스템 다이어그램")

    # 컴포넌트 색상 정의
    node_colors = {
        "CycleCloser": "#cccccc",
        "Compressor":  "#ffcc80",
        "Condenser":   "#ef9a9a",
        "Valve":       "#ce93d8",
        "Evaporator":  "#80cbc4",
    }
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', bgcolor='#f9f9f9')

    added_nodes = set()
    for c in st.session_state.connections:
        for node in [c['source'], c['target']]:
            if node not in added_nodes:
                color = node_colors.get(node, "#ffffff")
                dot.node(node, node, style='filled', fillcolor=color, shape='box')
                added_nodes.add(node)
        dot.edge(c['source'], c['target'],
                 label=f"{c['s_port']}→{c['t_port']}", fontsize='9')

    st.graphviz_chart(dot)
    # --- 예시 냉동 사이클 그림 ---
    st.caption("아래는 컴포넌트를 배치할 때 참고할 수 있는 기본 증기 압축 냉동 사이클 예시입니다.")
    draw_example_refrigeration_cycle()
    
    # 냉동 사이클 P-h 다이어그램 안내
    st.info(
        "**표준 냉동 사이클 구성:**\n"
        "CycleCloser → Compressor → Condenser → Valve → Evaporator → CycleCloser\n\n"
        "'🔄 표준 냉동 사이클 자동 구성' 버튼으로 빠르게 연결하세요."
    )

with col_res:
    st.subheader("🚀 시뮬레이션 결과")

    # 사용자 정의 냉동 사이클 해석
    if st.button("❄️ 해석 실행 (Solve)", use_container_width=True):
        if not st.session_state.connections:
            st.warning("⚠️ 연결이 없습니다. 먼저 연결을 추가하세요.")
        else:
            try:
                fluid = st.session_state.fluid

                # 네트워크 정의
                nw = Network(
                    fluids=[fluid],
                    T_unit='C', p_unit='bar', h_unit='kJ / kg', m_unit='kg / s'
                )

                # 컴포넌트 객체화
                comps = {}
                unique_names = list(dict.fromkeys(
                    [c['source'] for c in st.session_state.connections] +
                    [c['target'] for c in st.session_state.connections]
                ))
                for name in unique_names:
                    if name == "CycleCloser":
                        comps[name] = CycleCloser(name)
                    elif name == "Compressor":
                        comps[name] = Compressor(name)
                    elif name == "Condenser":
                        comps[name] = Condenser(name)
                    elif name == "Evaporator":
                        comps[name] = Evaporator(name)
                    elif name == "Valve":
                        comps[name] = Valve(name)

                # 컴포넌트 파라미터 할당
                params_all = st.session_state.comp_params
                for name, obj in comps.items():
                    p = params_all.get(name, {})
                    if isinstance(obj, Compressor):
                        obj.set_attr(eta_s=p.get('eta_s', 0.8))
                    elif isinstance(obj, Evaporator):
                        obj.set_attr(pr=p.get('pr', 0.99))
                    elif isinstance(obj, Valve):
                        # Valve의 pr은 자동 계산 (DOF 처리)
                        pass
                    elif isinstance(obj, Condenser):
                        obj.set_attr(pr=p.get('pr', 0.99))

                # 연결 생성
                tespy_conns = []
                conn_map   = {}  # 이름 → Connection 객체

                for conn in st.session_state.connections:
                    c = Connection(
                        comps[conn['source']], conn['s_port'],
                        comps[conn['target']], conn['t_port'],
                        label=f"{conn['source']}__{conn['target']}"
                    )
                    tespy_conns.append(c)
                    conn_map[f"{conn['source']}__{conn['target']}"] = c

                nw.add_conns(*tespy_conns)

                # --- 경계 조건 설정 (DOF 맞추기) ---
                m = st.session_state.mass_flow

                # CycleCloser → Compressor: 유체, 유량, 증발기 출구 조건 지정
                key_ev_out = "Evaporator__CycleCloser"
                key_cd_out = "Condenser__Valve"
                key_cc_out = "CycleCloser__Compressor"

                if key_cc_out in conn_map:
                    p_ev = params_all.get("Evaporator", {})
                    conn_map[key_cc_out].set_attr(
                        fluid={fluid: 1},
                        m=m,
                        T=p_ev.get('T_out', 5.0),
                        x=p_ev.get('x_out', 1.0)
                    )

                # Condenser → Valve: 응축기 출구 온도 & 건도 지정
                if key_cd_out in conn_map:
                    p_cd = params_all.get("Condenser", {})
                    conn_map[key_cd_out].set_attr(
                        T=p_cd.get('T_out', 40.0),
                        x=p_cd.get('x_out', 0.0)
                    )

                # 시뮬레이션 실행
                nw.solve(mode='design')
                nw.print_results()

                st.success("✅ 시뮬레이션 성공!")

                # 결과 테이블
                result_df = nw.results['Connection'][['m', 'p', 'T', 'h', 'x']]
                st.dataframe(result_df.style.format("{:.4f}"), use_container_width=True)

                # --- 성능 지표 계산 (COP) ---
                st.subheader("📊 냉동 사이클 성능 지표")

                comp_obj = comps.get("Compressor")
                evap_obj = comps.get("Evaporator")

                if comp_obj is not None and evap_obj is not None:
                    try:
                        # NOTE: TESPy 결과 구조에 따라 이 부분은 조정이 필요할 수 있음
                        W_comp = abs(nw.results['Component'].loc['Compressor', 'P'])  # W
                        Q_evap = abs(nw.results['Component'].loc['Evaporator', 'Q'])  # W

                        COP = Q_evap / W_comp if W_comp > 0 else float('nan')

                        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
                        kpi_col1.metric("압축기 소비 동력 (kW)", f"{W_comp/1000:.3f}")
                        kpi_col2.metric("냉동 능력 Q_evap (kW)", f"{Q_evap/1000:.3f}")
                        kpi_col3.metric("냉동 COP", f"{COP:.3f}")
                    except Exception as kpi_err:
                        st.warning(f"성능 지표 계산 중 오류: {kpi_err}")
                else:
                    st.info("Compressor 또는 Evaporator가 네트워크에 없습니다.")

            except Exception as e:
                st.error(f"❌ 해석 실패: {e}")
                st.markdown("""
                **문제를 해결하려면?**
                - **표준 사이클 구성 확인**: `🔄 표준 냉동 사이클 자동 구성` 버튼으로 연결을 초기화하세요.
                - **CycleCloser 필수**: 냉동 사이클은 반드시 `CycleCloser`로 루프를 닫아야 합니다.
                - **경계 조건**: 증발기 출구(T, x)와 응축기 출구(T, x) 값이 유효한지 확인하세요.
                - **냉매 범위**: 설정한 온도가 선택 냉매의 동작 범위 내에 있는지 확인하세요.
                """)

    st.markdown("---")
    st.subheader("📘 TESPy 네트워크 예시 (터빈+콤프+열교환기 + Exergy)")

    if st.button("⚙️ 예시 네트워크 실행 (Exergy 예시)", use_container_width=True):
        try:
            example = run_exergy_example()
            st.success("✅ 예시 네트워크 해석 및 Exergy 분석 성공!")

            # 간단한 네트워크 지표
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("연료 Exergy E_F (W)", f"{example['E_F']:.1f}")
            k2.metric("제품 Exergy E_P (W)", f"{example['E_P']:.1f}")
            k3.metric("손실 Exergy E_L (W)", f"{example['E_L']:.1f}")
            k4.metric("Exergy 효율 ε (-)", f"{example['epsilon']:.3f}")

            # Sankey 다이어그램
            st.markdown("#### 🔁 Exergy 흐름 Sankey 다이어그램")
            fig = go.Figure(go.Sankey(
                arrangement="snap",
                textfont={"family": "Linux Libertine O"},
                node={
                    "label": example["nodes"],
                    "pad": 11,
                    "color": "orange",
                },
                link=example["links"],
            ))
            st.plotly_chart(fig, use_container_width=True)

            st.info(
                "이 예시는 TESPy의 `Network`, `Source/Sink`, `Compressor`, `Turbine`, "
                "`HeatExchanger`, `Bus`, `ExergyAnalysis`를 사용해 "
                "전형적인 파워-냉각 사이클의 Exergy 흐름을 보여주는 간단한 데모입니다."
            )

        except Exception as ex:
            st.error(f"❌ 예시 네트워크 실행 실패: {ex}")
            st.write("TESPy 버전 또는 설치 환경에 따라 일부 속성명이 다를 수 있습니다. "
                     "필요하면 `run_exergy_example` 함수 내 파라미터를 조정하세요.")
