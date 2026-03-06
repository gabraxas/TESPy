import streamlit as st
from tespy.networks import Network
from tespy.components import (CycleCloser, Compressor, Condenser, Valve, HeatExchangerSimple)
from tespy.connections import Connection
import graphviz
import pandas as pd

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

    # 냉동 사이클 P-h 다이어그램 안내
    st.info(
        "**표준 냉동 사이클 구성:**\n"
        "CycleCloser → Compressor → Condenser → Valve → Evaporator → CycleCloser\n\n"
        "'🔄 표준 냉동 사이클 자동 구성' 버튼으로 빠르게 연결하세요."
    )

with col_res:
    st.subheader("🚀 시뮬레이션 결과")

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
                        comps[name] = HeatExchangerSimple(name)
                    elif name == "Evaporator":
                        comps[name] = HeatExchangerSimple(name)
                    elif name == "Valve":
                        comps[name] = Valve(name)

                # 컴포넌트 파라미터 할당
                params_all = st.session_state.comp_params
                for name, obj in comps.items():
                    p = params_all.get(name, {})
                    if isinstance(obj, Compressor):
                        obj.set_attr(eta_s=p.get('eta_s', 0.8))
                    elif isinstance(obj, HeatExchangerSimple):
                        obj.set_attr(pr=p.get('pr', 0.99))
                    elif isinstance(obj, Valve):
                        # Valve의 pr은 자동 계산 (DOF 처리)
                        pass

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

                # Condenser → Valve: 응 condensate 출구 온도 & 건도 지정
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

                # 압축기 소비 동력
                comp_obj = comps.get("Compressor")
                evap_obj = comps.get("Evaporator")

                if comp_obj is not None and evap_obj is not None:
                    try:
                        W_comp = abs(nw.results['Compressor'].loc['Compressor', 'P'])  # W
                        Q_evap = abs(nw.results['HeatExchangerSimple'].loc['Evaporator', 'Q'])  # W

                        COP = Q_evap / W_comp if W_comp > 0 else float('nan')

                        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
                        kpi_col1.metric("압축기 소비 동력 (kW)", f"{W_comp/1000:.3f}")
                        kpi_col2.metric("냉동 능력 Q_evap (kW)", f"{Q_evap/1000:.3f}")
                        kpi_col3.metric("냉동 COP", f"{COP:.3f}")
                    except Exception as kpi_err:
                        st.warning(f"성능 지표 계산 중 오류: {kpi_err}")

            except Exception as e:
                st.error(f"❌ 해석 실패: {e}")
                st.markdown("""
                **문제를 해결하려면?**
                - **표준 사이클 구성 확인**: `🔄 표준 냉동 사이클 자동 구성` 버튼으로 연결을 초기화하세요.
                - **CycleCloser 필수**: 냉동 사이클은 반드시 `CycleCloser`로 루프를 닫아야 합니다.
                - **경계 조건**: 증발기 출구(T, x)와 응축기 출구(T, x) 값이 유효한지 확인하세요.
                - **냉매 범위**: 설정한 온도가 선택 냉매의 동작 범위 내에 있는지 확인하세요.
                """)
