import streamlit as st

from common import (
    ApiError, 
    api, 
    conversation_label, 
    SessionExpired,
    auth_headers,
    stream_answer,
    SERVICE_NAME
)

from analytics_dashboard import render_dashboard

st.set_page_config(page_title=SERVICE_NAME, layout="centered")

st.session_state.setdefault("access_token", None) # RLS 적용한 /me 라우터용
st.session_state.setdefault("user_email", None)
st.session_state.setdefault("conversation_id", None)

# 버튼으로 보낼 질문을 잠시 담아두는 곳. 버튼 안에서 바로 보내면
# 화면이 다시 그려지는 도중이라 결과가 화면에 안 나타난다.
st.session_state.setdefault("pending_question", None)

# 세션이 풀린 이유를 다음 실행에서 보여주려고 남겨둔다.
# 토큰만 지우고 끝내면 사용자는 자기가 왜 로그아웃됐는지 모른다.
st.session_state.setdefault("expired_notice", None)

# 답을 못 받은 질문. `다시 시도` 버튼이 이것을 쓴다.
st.session_state.setdefault("failed_question", None)

# 현재 페이지 상태
st.session_state.setdefault("current_page", "chat")

# 시작 질문 예시
EXAMPLE_QUESTIONS = [
    "예제 질문1 - 대화를 시작해 주세요.",
    "예제 질문2",
    "예제 질문3",
]

def on_conversation_change(conversation_id: str) -> None:
    st.session_state.conversation_id = conversation_id
    st.session_state.current_page = "chat"


def render_sidebar(conversations: list) -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarContent"] {
            overflow: hidden;
        }
        [data-testid="stSidebar"] .st-key-sidebar_conversations {
            height: auto;
            max-height: max(120px, calc(100dvh - 390px));
            overflow-y: auto;
            overflow-x: hidden;
            overscroll-behavior: contain;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        with st.container(key="sidebar_navigation"):
            # 로그인한 사용자 이메일 출력
            # st.caption(st.session_state.user_email)

            if st.button("홈", use_container_width=True):
                st.session_state.current_page = "chat"

            # 1. 새 대화 버튼
            if st.button("새 대화", use_container_width=True):
            # and job_title:
                # 대화 생성 엔드포인트 호출
                try:
                    st.session_state.current_page = "chat"
                    created = api(
                        "POST",
                        "/me/conversations",
                        # 첫 사용자 메시지를 저장할 때 백엔드가 제목을 갱신한다.
                        json={"title": "새 대화"},
                        headers=auth_headers(),
                    )
                except ApiError as error:
                    st.error(str(error))
                    return

                st.session_state.conversation_id = created["id"]
                st.rerun()

            # 2. 로그 및 데이터 분석 버튼
            if st.button("로그 및 데이터 분석", use_container_width=True):
                st.session_state.current_page = "analytics"

            if st.button("로그아웃", use_container_width=True):
                sign_out()

        st.divider()

        st.subheader("최근 대화")

        with st.container(key="sidebar_conversations"):
            if conversations:
                labels = {c["id"]: conversation_label(c) for c in conversations}
                ids = list(labels)

                # 처음 진입하거나 선택한 대화가 사라졌다면 첫 대화를 선택한다.
                if st.session_state.conversation_id not in ids:
                    st.session_state.conversation_id = ids[0]

                for conversation_id in ids:
                    st.button(
                        labels[conversation_id],
                        key=f"conversation_{conversation_id}",
                        use_container_width=True,
                        type="primary" if (
                            st.session_state.current_page == "chat"
                            and st.session_state.conversation_id == conversation_id
                        ) else "secondary",
                        on_click=on_conversation_change,
                        args=(conversation_id,),
                    )
            else:
                st.caption("대화를 시작하세요.")


def render_empty(message: str, hint: str) -> None:
    """빈 화면은 "없다"가 아니라 "다음에 무엇을 하면 되는지"를 말해야 한다."""
    st.info(message)
    st.caption(hint)

def ask(conversation_id: str, question: str) -> None:
    """질문을 보내고 답을 받는다. 실패하면 화면에 이유를 남긴다."""
    # user 메시지 먼저 출력
    with st.chat_message("user"):
        st.write(question)

    # 어시스턴트 메시지는 스트림으로 다 올 때 까지 출력
    with st.chat_message("assistant"):
        try:
            # st.write_stream 은 조각을 받아 화면에 이어 붙이고, 커서도 그려준다.
            st.write_stream(
                stream_answer(
                    f"/conversations/{conversation_id}/chat",
                    {
                        "content": question,
                    },
                    auth_headers(),
                )
            )
        except ApiError as error:
            # 실패한 질문을 기억해 둔다. 다시 시도 버튼이 이것을 쓴다.
            # 사용자가 긴 답변을 다시 타이핑하게 만들면 안 된다.
            st.session_state.failed_question = question
            st.error(str(error))
            return

    st.session_state.failed_question = None
    st.rerun()

def render_examples(conversation_id: str) -> None:
    """새로운 대화를 시작한 상태에서 출발 질문을 제시하는 함수"""
    st.caption("아래 질문 중에서 선택해보세요.")
    columns = st.columns(len(EXAMPLE_QUESTIONS))
    for col, question in zip(columns, EXAMPLE_QUESTIONS):
        if col.button(question, use_container_width=True):
            st.session_state.pending_question = question
            st.rerun()

def render_conversation(conversation_id: str) -> None:
    """가운데: 주고받은 내용과 입력칸."""

    messages = api("GET", f"/conversations/{conversation_id}/messages", headers=auth_headers())

    if not messages:
        render_empty(
            "아직 주고받은 내용이 없습니다.",
            "아래 입력칸에 첫 답변을 적어보세요.",
        )
        # 예시 질문을 추가합니다.
        render_examples(conversation_id)      

    # 메시지 목록 출력
    last_index = len(messages) - 1
    for index, message in enumerate(messages):
        if message["role"] == "system":
            # 맥락을 끊은 지점. 말풍선이 아니라 구분선으로 그린다.
            # 누가 한 말이 아니라 "여기서 끊겼다"는 표시이기 때문이다.
            st.divider()
            st.caption(message["content"])
            continue #그 다음 메시지로 간다        
        with st.chat_message(message["role"]):
            st.write(message["content"])      

    # 버튼이 담아둔 질문이 있으면 먼저 보낸다.
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        ask(conversation_id, question)

    # 메시지 입력 위젯 출력
    if answer := st.chat_input("답변을 입력하세요"):
        ask(conversation_id, answer)      

def render_login() -> None:
    """비로그인 상태의 화면 - 전체영역."""
    # 세션만료 확인
    if st.session_state.expired_notice:
        st.warning(st.session_state.expired_notice)

    st.write("사용 기록은 개인 계정에 저장됩니다.")

    # email, password 입력
    # api / auth/login, /auth/signup 호출

    email = st.text_input("이메일", placeholder="you@example.com")
    password = st.text_input("비밀번호", type="password")

    login_column, signup_column = st.columns(2)
    action = None
    if login_column.button("로그인", use_container_width=True):
        action = "login"
    if signup_column.button("회원가입", use_container_width=True):
        action = "signup"

    if not action:
        return
    if not email or not password:
        st.error("이메일과 비밀번호를 모두 입력하세요.")
        return

    try:
        result = api(
            "POST", f"/auth/{action}", json={"email": email, "password": password}
        )
    except ApiError as error:
        st.error(str(error))
        return

    if not result.get("access_token"):
        # 가입은 됐는데 토큰이 없는 경우가 있다 (이메일 확인이 켜져 있을 때).
        st.error("가입은 되었지만 바로 로그인되지 않았습니다.")
        return

    st.session_state.access_token = result["access_token"]
    st.session_state.user_email = result["email"]
    st.session_state.expired_notice = None
    st.rerun()

def sign_out(notice: str | None = None) -> None:
    """로그인 관련 상태를 한 번에 지운다.

    지울 것을 빠뜨리면 다음 사용자에게 앞사람의 대화가 잠깐 보인다.
    그래서 로그아웃과 세션 만료가 같은 함수를 쓰게 해둔다.
    """
    st.session_state.access_token = None
    st.session_state.user_email = None
    st.session_state.conversation_id = None
    st.session_state.pending_question = None
    st.session_state.expired_notice = notice
    st.session_state.failed_question = None

    st.rerun() # 로그인 화면 렌더링

def render_signed_in() -> None:
    """로그인한 이후 화면 전체.

    이 안에서 나는 SessionExpired 는 아래에서 한 번에 받는다.
    호출마다 try 를 쓰면 스무 군데가 되고, 한 곳만 빠뜨려도
    거기서 화면이 비어 보인다.
    """

    conversations = api("GET", "/me/conversations", headers=auth_headers())
    render_sidebar(conversations)

    # 로그 및 데이터 분석
    if st.session_state.current_page == "analytics":
        render_dashboard()
        return    

    # 챗봇
    if not conversations:
        render_empty(
            "아직 대화 기록이 없습니다.",
            "`새 대화 시작` 을 누르세요.",
        )
    # 방어 가지. 사이드바에서 첫 항목을 자동으로 고르므로 평소에는 닿지 않는다.
    # 목록이 있는데 선택이 비면 render_conversation(None) 이 되어 422 가 난다.
    elif not st.session_state.conversation_id:
        render_empty(
            "대화를 고르세요.",
            "왼쪽 `지난 대화` 에서 하나를 선택하면 됩니다.",
        )
    else:
        render_conversation(st.session_state.conversation_id)

try:
    if st.session_state.access_token:
        # 대화목록으로 사이드바 렌더링
        render_signed_in()
    else:
        # 로그인 페이지 렌더링
        st.title(SERVICE_NAME)
        render_login()
except SessionExpired as error:
    sign_out(str(error))

except ApiError as error:
    st.error(str(error))
