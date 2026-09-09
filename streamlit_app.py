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
from ui import apply_workspace_style, page_header, workspace_brand

st.set_page_config(page_title=SERVICE_NAME, layout="wide")
apply_workspace_style()

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
    "연차는 어떻게 신청하나요?",
    "경조사 휴가 기준을 알려주세요.",
    "복리후생 제도를 알려주세요.",
]

def on_conversation_change(conversation_id: str) -> None:
    st.session_state.conversation_id = conversation_id
    st.session_state.current_page = "chat"


def start_conversation() -> None:
    """사이드바와 첫 방문 CTA가 같은 대화 생성 흐름을 사용한다."""
    current = st.session_state.conversation_id
    if current:
        messages = api("GET", f"/conversations/{current}/messages", headers=auth_headers())
        if not messages:
            st.session_state.current_page = "chat"
            return

    created = api(
        "POST", "/me/conversations",
        json={"title": "새 대화"}, headers=auth_headers(),
    )
    st.session_state.conversation_id = created["id"]
    st.session_state.current_page = "chat"
    st.session_state.pending_question = None
    st.session_state.failed_question = None
    st.rerun()


def render_welcome() -> None:
    with st.container(key="welcome_panel"):
        st.markdown(
            '<div class="welcome-copy"><div class="workspace-mark" aria-hidden="true">H</div>'
            '<h2>AskHR에 오신 것을 환영합니다</h2>'
            '<p>궁금한 사내 제도, 이제 대화로 확인하세요.<br>'
            'HR 도우미가 필요한 규정을 찾는 데 도움을 드립니다.</p>'
            '<div class="welcome-topics"><span>연차·휴가</span><span>복리후생</span>'
            '<span>사내 규정</span></div></div>', unsafe_allow_html=True,
        )
        with st.container(key="welcome_cta"):
            if st.button("새 대화 시작", icon=":material/edit_square:",
                         type="primary", key="welcome_start", width="stretch"):
                try:
                    start_conversation()
                except ApiError as error:
                    st.error(str(error))
        st.markdown('<p class="welcome-hint">첫 질문을 보내면 대화 제목이 자동으로 만들어집니다.</p>',
                    unsafe_allow_html=True)


def render_sidebar(conversations: list) -> None:
    with st.sidebar:
        workspace_brand()
        with st.container(key="sidebar_navigation"):
            if st.button("홈", icon=":material/home:", width="stretch"):
                st.session_state.current_page = "chat"

            # 1. 새 대화 버튼
            if st.button("새 대화", icon=":material/edit_square:", width="stretch"):
                try:
                    start_conversation()
                except ApiError as error:
                    st.error(str(error))
                    return


            # 2. 로그 및 데이터 분석 버튼
            if st.button("로그 및 데이터 분석", icon=":material/bar_chart:", width="stretch"):
                st.session_state.current_page = "analytics"

            if st.button("로그아웃", icon=":material/logout:", width="stretch"):
                confirm_sign_out()

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
                        width="stretch",
                        type="primary" if (
                            st.session_state.current_page == "chat"
                            and st.session_state.conversation_id == conversation_id
                        ) else "secondary",
                        on_click=on_conversation_change,
                        args=(conversation_id,),
                    )
            else:
                st.caption("대화를 시작하세요.")

        # 로그인한 사용자 이메일 출력
        clean_email = st.session_state.user_email.replace("@", "@\u200b")
        st.caption(clean_email)              


def render_empty(message: str, hint: str) -> None:
    """빈 화면은 "없다"가 아니라 "다음에 무엇을 하면 되는지"를 말해야 한다."""
    st.info(message)
    st.caption(hint)

def ask(conversation_id: str, question: str) -> None:
    """질문을 보내고 답을 받는다. 실패하면 화면에 이유를 남긴다."""
    # user 메시지 먼저 출력
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown("**나**")
        st.write(question)

    # 어시스턴트 메시지는 스트림으로 다 올 때 까지 출력
    with st.chat_message("assistant", avatar=":material/support_agent:"):
        st.markdown("**AskHR** · HR 도우미")
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
    with st.container(key="conversation_starters"):
        st.caption("추천 질문 · 하나를 선택해 대화를 시작하세요")
        columns = st.columns(len(EXAMPLE_QUESTIONS))
        for index, (col, question) in enumerate(zip(columns, EXAMPLE_QUESTIONS)):
            if col.button(
                question, icon=":material/chat_bubble_outline:",
                key=f"starter_{conversation_id}_{index}", width="stretch",
            ):
                st.session_state.pending_question = question
                st.rerun()


def render_new_conversation(conversation_id: str) -> None:
    """슬랙의 채널 시작 화면처럼 새 대화를 안내한다."""
    with st.container(key="new_conversation"):
        st.markdown(
            '<div class="conversation-intro">'
            '<div class="workspace-mark" aria-hidden="true">#</div>'
            '<h2>새 대화의 시작입니다</h2>'
            '<p>연차부터 복리후생까지, 궁금한 사내 제도를 AskHR에 물어보세요.</p>'
            '</div>', unsafe_allow_html=True,
        )
        with st.chat_message("assistant", avatar=":material/support_agent:"):
            st.markdown("**AskHR** · HR 도우미")
            st.write("안녕하세요! 어떤 제도가 궁금하신가요? 아래 질문을 선택하거나 메시지를 직접 입력해 주세요.")
        render_examples(conversation_id)

def render_conversation(conversation_id: str) -> None:
    """가운데: 주고받은 내용과 입력칸."""

    messages = api("GET", f"/conversations/{conversation_id}/messages", headers=auth_headers())

    if not messages:
        render_new_conversation(conversation_id)

    # 메시지 목록 출력
    last_index = len(messages) - 1
    for index, message in enumerate(messages):
        if message["role"] == "system":
            # 맥락을 끊은 지점. 말풍선이 아니라 구분선으로 그린다.
            # 누가 한 말이 아니라 "여기서 끊겼다"는 표시이기 때문이다.
            st.divider()
            st.caption(message["content"])
            continue #그 다음 메시지로 간다        
        with st.chat_message(message["role"], avatar=":material/person:" if message["role"] == "user" else ":material/support_agent:"):
            st.markdown("**나**" if message["role"] == "user" else "**AskHR** · HR 도우미")
            st.write(message["content"])      

    # 버튼이 담아둔 질문이 있으면 먼저 보낸다.
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        ask(conversation_id, question)

    # 메시지 입력 위젯 출력
    if answer := st.chat_input("AskHR에 메시지 보내기"):
        ask(conversation_id, answer)      

def complete_login(result: dict) -> None:
    st.session_state.access_token = result["access_token"]
    st.session_state.user_email = result["email"]
    st.session_state.expired_notice = None
    st.rerun()


@st.dialog("회원가입")
def render_signup() -> None:
    st.caption("AskHR 계정을 만들고 사내 제도를 편하게 물어보세요.")
    with st.form("signup_form"):
        email = st.text_input("이메일", placeholder="you@example.com", key="signup_email")
        password = st.text_input("비밀번호", type="password", key="signup_password")
        confirmation = st.text_input("비밀번호 확인", type="password", key="signup_confirmation")
        submitted = st.form_submit_button("가입하기", type="primary", width="stretch")
    if not submitted:
        return
    if not email.strip() or not password:
        st.error("이메일과 비밀번호를 모두 입력하세요.")
        return
    if password != confirmation:
        st.error("비밀번호가 일치하지 않습니다.")
        return
    try:
        result = api("POST", "/auth/signup", json={"email": email.strip(), "password": password})
    except ApiError as error:
        st.error(str(error))
        return
    if result.get("access_token"):
        complete_login(result)
    else:
        st.success("회원가입이 완료되었습니다. 이메일 인증이 필요한 경우 받은 메일을 확인한 뒤 로그인해 주세요.")


def render_login() -> None:
    """비로그인 상태의 화면 - 전체영역."""
    # 세션만료 확인
    if st.session_state.expired_notice:
        st.warning(st.session_state.expired_notice)

    st.write("사용 기록은 개인 계정에 저장됩니다.")

    with st.form("login_form", border=False):
        email = st.text_input("이메일", placeholder="you@example.com")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", width="stretch")
    with st.container(key="signup_link"):
        st.caption("아직 계정이 없으신가요?")
        if st.button("회원가입", width="stretch"):
            render_signup()

    if not submitted:
        return
    if not email or not password:
        st.error("이메일과 비밀번호를 모두 입력하세요.")
        return

    try:
        result = api(
            "POST", "/auth/login", json={"email": email, "password": password}
        )
    except ApiError as error:
        st.error(str(error))
        return

    if not result.get("access_token"):
        st.error("로그인되지 않았습니다. 이메일 인증 여부를 확인해 주세요.")
        return

    complete_login(result)

@st.dialog("로그아웃")
def confirm_sign_out() -> None:
    st.write("정말 로그아웃하시겠어요?")
    cancel, confirm = st.columns(2)
    if cancel.button("취소", key="cancel_sign_out", width="stretch"):
        st.rerun()
    if confirm.button("로그아웃", key="confirm_sign_out", type="primary", width="stretch"):
        st.session_state.current_page = "chat"
        sign_out()


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

    title = next((c.get("title") or "새 대화" for c in conversations
                  if c["id"] == st.session_state.conversation_id), "HR 도우미")
    page_header(f"# {title}", "AskHR · 사내 제도와 규정에 대해 질문하세요.")

    # 챗봇
    if not conversations:
        render_welcome()
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
        with st.container(key="login_panel"):
            workspace_brand()
            st.title("워크스페이스에 로그인")
            st.caption("궁금한 사내 제도, 이제 대화로 확인하세요.")
            render_login()
except SessionExpired as error:
    sign_out(str(error))

except ApiError as error:
    st.error(str(error))
