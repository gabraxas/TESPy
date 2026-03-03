import streamlit as st
import time

# ---------------------------------------------------------
# 1. Tespi 연동 함수 (가상)
# ---------------------------------------------------------
def save_to_tespi(name, category, description):
    """
    Tespi 시스템(DB 또는 API)에 데이터를 저장하는 함수입니다.
    현재는 시뮬레이션을 위해 1초 대기 후 성공(True)을 반환하도록 작성되었습니다.
    """
    # 실제 연동 시 아래와 같은 API 호출 또는 DB 쿼리 코드가 들어갑니다.
    # import requests
    # response = requests.post("https://api.tespi.com/components", json={...})
    
    time.sleep(1) # 네트워크 지연(저장 시간) 시뮬레이션
    return True

# ---------------------------------------------------------
# 2. Streamlit UI 구성
# ---------------------------------------------------------
# 페이지 탭 기본 설정
st.set_page_config(page_title="Tespi Component Manager", page_icon="⚙️")

st.title("⚙️ Tespi 콤포넌트 추가")
st.markdown("Tespi 시스템에 새로운 콤포넌트를 등록합니다. 아래 양식을 정확히 입력해 주세요.")

st.divider()

# 폼(Form)을 생성하여 입력 데이터 묶기
with st.form(key="component_form"):
    st.subheader("📝 콤포넌트 정보 입력")
    
    # 입력 필드 구성
    comp_name = st.text_input("콤포넌트 이름", placeholder="예: 회원가입 모듈, 결제 API 등")
    comp_category = st.selectbox(
        "콤포넌트 유형", 
        ["Frontend (UI/UX)", "Backend (API)", "Database", "Infra", "기타"]
    )
    comp_desc = st.text_area("상세 설명", placeholder="해당 콤포넌트의 주요 역할과 특징을 설명해 주세요.")
    
    # 제출 버튼 (이 버튼을 눌러야만 폼 안의 데이터가 전송됨)
    submitted = st.form_submit_button("Tespi에 등록하기")

# ---------------------------------------------------------
# 3. 폼 제출 후 동작 처리
# ---------------------------------------------------------
if submitted:
    if not comp_name.strip():
        # 필수 입력값 검증
        st.warning("⚠️ 콤포넌트 이름을 입력해 주세요.")
    else:
        # 등록 진행 중 스피너 표시
        with st.spinner(f"'{comp_name}'을(를) Tespi에 등록하고 있습니다..."):
            is_success = save_to_tespi(comp_name, comp_category, comp_desc)
            
            if is_success:
                st.success(f"✅ '{comp_name}' 콤포넌트가 성공적으로 추가되었습니다!")
            else:
                st.error("❌ 등록 중 오류가 발생했습니다. 시스템을 확인해 주세요.")
