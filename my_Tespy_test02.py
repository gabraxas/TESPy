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
from pathlib import Path
#from PIL import Image


def load_example_refrigeration_cycle():
    """
    Show an example basic vapor compression refrigeration cycle diagram
    using a local SVG file in the same directory as this script.
    """
    # 현재 파일(my_Tespy_test02.py) 기준으로 같은 디렉토리의 SVG
    svg_path = Path(__file__).parent / "aa.png"  # 파일 이름만 바꿔주면 됨

    if not svg_path.exists():
        st.warning(f"Example cycle SVG not found: {svg_path}")
        return

    # 방법 1: st.image로 SVG 표시
    with open(svg_path, "rb") as f:
        svg_bytes = f.read()

    st.image(
        svg_bytes,
        caption="Example of a basic vapor compression refrigeration cycle",
        use_container_width=400,
    )


# 1. Page config
st.set_page_config(layout="wide", page_title="TESPy Refrigerator Designer")
st.title("TESPy Refrigeration Cycle System Designer (v2.0)")

# --- Fixed component list for refrigeration cycle ---
REFRIG_COMP_LIST = ["Source", "Sink", "CycleCloser", "Compressor", "Turbine", "HeatExchanger"]

# --- 2. Session state management (data persistence) ---
if "connections" not in st.session_state:
    st.session_state.connections = []
if "comp_params" not in st.session_state:
    # Default parameter set for the refrigeration cycle
    st.session_state.comp_params = {
        "Source":{"T":-10, "pr":1},
        "Sink":{"T":25,"pr":1.5},
        "CycleCloser": {},
        "Turbine":{"eta_s":0.8},
        "Compressor":  {"eta_s": 0.8},
        "HeatExchanger":   {"pr": 0.99, "T_out": 40.0, "x_out": 0.0},        
    }
if "fluid" not in st.session_state:
    st.session_state.fluid = "water"
if "mass_flow" not in st.session_state:
    st.session_state.mass_flow = 0.05

# --- 3. Sidebar: UI layout ---
with st.sidebar:
    st.header("Refrigeration Cycle Builder")

    # Working fluid selection
    st.session_state.fluid = st.selectbox(
        "Working fluid",
        ["Air", "water"],
        index=["Air","water"].index(st.session_state.fluid)
    )
    st.session_state.mass_flow = st.number_input(
        "Mass flow rate (kg/s)",
        min_value=0.001,
        value=st.session_state.mass_flow,
        step=0.005
    )
    st.divider()

    tab1, tab2 = st.tabs(["Connection Management", "Component Parameters"])

    with tab1:
        st.subheader("Add new connection")
        src = st.selectbox("From (source component)", REFRIG_COMP_LIST, key="sel_src")
        trg = st.selectbox("To (target component)",   REFRIG_COMP_LIST, key="sel_trg")

        c1, c2 = st.columns(2)
        s_port = c1.selectbox("Source port", ["out1", "out2"], key="src_p")
        t_port = c2.selectbox("Target port", ["in1", "in2"],  key="trg_p")

        if st.button("Add connection (+)", use_container_width=True):
            st.session_state.connections.append({
                "source": src, "target": trg,
                "s_port": s_port, "t_port": t_port
            })

        # Auto-build standard refrigeration cycle
        if st.button("Build standard refrigeration cycle", use_container_width=True):
            st.session_state.connections = [
                {"source": "HeatExchanger(Cold)", "target": "CycleCloser", "s_port": "out2", "t_port": "in1"},
                {"source": "CycleCloser",  "target": "Compressor",  "s_port": "out1", "t_port": "in1"},
                {"source": "Compressor",   "target": "HeatExchanger(Hot)",      "s_port": "out1", "t_port": "in1"},
                {"source": "HeatExchanger(Hot)",       "target": "Turbine", "s_port": "out1", "t_port": "in1"},
                {"source": "Turbine",  "target": "HeatExchanger(Cold)","s_port": "out1", "t_port": "in1"},
                {"source": "Source(Air)",  "target": "HeatExchanger(Cold)","s_port": "out1", "t_port": "in1"},                
                {"source": "HeatExchanger(Cold)",  "target": "Sink(Air)","s_port": "out1", "t_port": "in1"},
                {"source": "Source(Water)",  "target": "HeatExchanger(Hot)","s_port": "out1", "t_port": "in2"},                
                {"source": "HeatExchanger(Hot)",  "target": "Sink(Water)","s_port": "out2", "t_port": "in1"},
            ]
            st.rerun()

        if st.button("Reset all", type="primary", use_container_width=True):
            st.session_state.connections = []
            st.rerun()

        # Show current connection list
        if st.session_state.connections:
            st.subheader("Current connections")
            for i, c in enumerate(st.session_state.connections):
                cols = st.columns([4, 1])
                cols[0].caption(
                    f"{i+1}. {c['source']}({c['s_port']}) → "
                    f"{c['target']}({c['t_port']})"
                )
                if cols[1].button("Delete", key=f"del_{i}"):
                    st.session_state.connections.pop(i)
                    st.rerun()

    with tab2:
        st.subheader("Component specifications")
        active_comps = list(dict.fromkeys(
            [c['source'] for c in st.session_state.connections] +
            [c['target'] for c in st.session_state.connections]
        ))

        if not active_comps:
            st.info("Please create at least one connection first.")
        else:
            selected = st.selectbox("Component to edit", active_comps)
            params = st.session_state.comp_params.get(selected, {})

            if selected == "Compressor":
                params['eta_s'] = st.slider(
                    "Isentropic efficiency (η_s)",
                    0.1, 1.0,
                    float(params.get('eta_s', 0.8)),
                    step=0.01
                )

            elif selected == "Condenser":
                params['pr'] = st.slider(
                    "Pressure ratio (pr)",
                    0.5, 1.0,
                    float(params.get('pr', 0.99)),
                    step=0.01
                )
                params['T_out'] = st.number_input(
                    "Condenser outlet temperature (°C)",
                    value=float(params.get('T_out', 40.0))
                )
                params['x_out'] = st.number_input(
                    "Condenser outlet vapor quality (x, 0 = saturated liquid)",
                    min_value=0.0, max_value=1.0,
                    value=float(params.get('x_out', 0.0)),
                    step=0.1
                )

            elif selected == "Evaporator":
                params['pr'] = st.slider(
                    "Pressure ratio (pr)",
                    0.5, 1.0,
                    float(params.get('pr', 0.99)),
                    step=0.01
                )
                params['T_out'] = st.number_input(
                    "Evaporator outlet temperature (°C)",
                    value=float(params.get('T_out', 5.0))
                )
                params['x_out'] = st.number_input(
                    "Evaporator outlet vapor quality (x, 1 = saturated vapor)",
                    min_value=0.0, max_value=1.0,
                    value=float(params.get('x_out', 1.0)),
                    step=0.1
                )

            elif selected == "Valve":
                params['pr'] = st.slider(
                    "Pressure ratio (pr, 1.0 = automatic from calculation)",
                    0.01, 1.0,
                    float(params.get('pr', 1.0)),
                    step=0.01
                )

            elif selected == "CycleCloser":
                st.info("CycleCloser has no adjustable parameters.")

            st.session_state.comp_params[selected] = params

# --- 4. Main area: visualization and analysis ---
col_graph, col_res = st.columns([1, 1])

with col_graph:
    st.subheader("System Diagram")

    # Component colors
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
        dot.edge(
            c['source'], c['target'],
            label=f"{c['s_port']}→{c['t_port']}",
            fontsize='9'
        )

    st.graphviz_chart(dot)

    # Example refrigeration cycle diagram
    st.caption(
        "The following is an example of a basic vapor compression "
        "refrigeration cycle that you can use as a reference when "
        "building your system."
    )
    load_example_refrigeration_cycle()

    # Standard refrigeration cycle info
    st.info(
        "**Standard refrigeration cycle configuration:**\n"
        "CycleCloser → Compressor → Condenser → Valve → Evaporator → CycleCloser\n\n"
        "Use the 'Build standard refrigeration cycle' button to quickly create the connections."
    )

with col_res:
    st.subheader("Simulation Results")

    # Run user-defined refrigeration cycle analysis
    if st.button("Run simulation (Solve)", use_container_width=True):
        if not st.session_state.connections:
            st.warning("No connections found. Please add at least one connection.")
        else:
            try:
                fluid = st.session_state.fluid

                # Define TESPy network
                nw = Network(
                    fluids=[fluid],
                    T_unit='C', p_unit='bar', h_unit='kJ / kg', m_unit='kg / s'
                )

                # Create component objects
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

                # Assign component parameters
                params_all = st.session_state.comp_params
                for name, obj in comps.items():
                    p = params_all.get(name, {})
                    if isinstance(obj, Compressor):
                        obj.set_attr(eta_s=p.get('eta_s', 0.8))
                    elif isinstance(obj, Evaporator):
                        obj.set_attr(pr=p.get('pr', 0.99))
                    elif isinstance(obj, Valve):
                        # pr for Valve is treated as DOF and can be solved by TESPy
                        pass
                    elif isinstance(obj, Condenser):
                        obj.set_attr(pr=p.get('pr', 0.99))

                # Create connections
                tespy_conns = []
                conn_map = {}  # name -> Connection object

                for conn in st.session_state.connections:
                    c = Connection(
                        comps[conn['source']], conn['s_port'],
                        comps[conn['target']], conn['t_port'],
                        label=f"{conn['source']}__{conn['target']}"
                    )
                    tespy_conns.append(c)
                    conn_map[f"{conn['source']}__{conn['target']}"] = c

                nw.add_conns(*tespy_conns)

                # --- Boundary conditions (DOF) ---
                m = st.session_state.mass_flow

                key_ev_out = "Evaporator__CycleCloser"
                key_cd_out = "Condenser__Valve"
                key_cc_out = "CycleCloser__Compressor"

                # CycleCloser → Compressor: fluid, mass flow, evap outlet conditions
                if key_cc_out in conn_map:
                    p_ev = params_all.get("Evaporator", {})
                    conn_map[key_cc_out].set_attr(
                        fluid={fluid: 1},
                        m=m,
                        T=p_ev.get('T_out', 5.0),
                        x=p_ev.get('x_out', 1.0)
                    )

                # Condenser → Valve: condenser outlet temperature & quality
                if key_cd_out in conn_map:
                    p_cd = params_all.get("Condenser", {})
                    conn_map[key_cd_out].set_attr(
                        T=p_cd.get('T_out', 40.0),
                        x=p_cd.get('x_out', 0.0)
                    )

                # Solve network
                nw.solve(mode='design')
                nw.print_results()

                st.success("Simulation finished successfully.")

                # Result table
                result_df = nw.results['Connection'][['m', 'p', 'T', 'h', 'x']]
                st.dataframe(result_df.style.format("{:.4f}"), use_container_width=True)

                # --- Performance indices (COP) ---
                st.subheader("Performance indicators of the refrigeration cycle")

                comp_obj = comps.get("Compressor")
                evap_obj = comps.get("Evaporator")

                if comp_obj is not None and evap_obj is not None:
                    try:
                        # NOTE: Depending on TESPy result structure, this part may need adjustment.
                        W_comp = abs(nw.results['Component'].loc['Compressor', 'P'])  # W
                        Q_evap = abs(nw.results['Component'].loc['Evaporator', 'Q'])  # W

                        COP = Q_evap / W_comp if W_comp > 0 else float('nan')

                        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
                        kpi_col1.metric("Compressor power (kW)", f"{W_comp/1000:.3f}")
                        kpi_col2.metric("Cooling capacity Q_evap (kW)", f"{Q_evap/1000:.3f}")
                        kpi_col3.metric("Refrigeration COP", f"{COP:.3f}")
                    except Exception as kpi_err:
                        st.warning(f"Error while calculating performance indicators: {kpi_err}")
                else:
                    st.info("Compressor or Evaporator is not present in the network.")

            except Exception as e:
                st.error(f"Simulation failed: {e}")
                st.markdown(
                    """
                    **How to debug the problem:**
                    - **Check standard cycle configuration**: use the
                      'Build standard refrigeration cycle' button to reset connections.
                    - **CycleCloser required**: the cycle must be closed with `CycleCloser`.
                    - **Boundary conditions**: check if the evaporator outlet (T, x) and
                      condenser outlet (T, x) are valid values.
                    - **Working fluid range**: make sure the temperatures are within the
                      valid range for the selected working fluid.
                    """
                )
