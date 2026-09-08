"""모든 페이지에서 사용하는 워크스페이스 UI."""
from html import escape

import streamlit as st


def apply_workspace_style():
    st.markdown("""
<style>
/* Streamlit 상단 도구 모음 아래에 페이지 제목이 온전히 보이도록 공간을 확보한다. */
.block-container {max-width:1440px;padding:5.5rem 2.5rem 3rem;}
.workspace-header {border-bottom:1px solid color-mix(in srgb,currentColor 18%,transparent);
 padding:0 0 18px;margin-bottom:24px;}
.workspace-header h1 {font-size:22px;font-weight:750;line-height:1.4;margin:0;padding:0;overflow-wrap:anywhere;}
.workspace-header p {font-size:13px;opacity:.7;margin:6px 0 0;}
.workspace-brand {display:flex;align-items:center;gap:12px;margin-bottom:16px;}
.workspace-mark {display:grid;place-items:center;width:38px;height:38px;border-radius:9px;
 background:#E8D6ED;color:#4A154B;font-size:21px;font-weight:800;flex-shrink:0;}
.workspace-brand strong {font-size:20px;letter-spacing:-.5px;}
.workspace-brand small {display:block;font-size:12px;opacity:.75;margin-top:2px;}
[data-testid="stSidebarContent"] {overflow:hidden;}
[data-testid="stSidebarUserContent"] {padding:1rem 1rem 0;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap:.5rem;}
[data-testid="stSidebar"] hr {margin:1.25rem 0;}
[data-testid="stSidebar"] h3 {font-size:13px;opacity:.8;padding:0 8px 8px;}
[data-testid="stSidebar"] button {justify-content:flex-start;text-align:left;min-height:36px;}
[data-testid="stSidebar"] .st-key-sidebar_navigation button {
 justify-content:flex-start !important;text-align:left !important;padding-inline:12px;}
[data-testid="stSidebar"] .st-key-sidebar_navigation button > div {
 width:100%;justify-content:flex-start !important;text-align:left;gap:10px;}
[data-testid="stSidebar"] .st-key-sidebar_navigation button [data-testid="stMarkdownContainer"] {
 flex:1;text-align:left;}
[data-testid="stSidebar"] .st-key-sidebar_navigation button p {text-align:left !important;}
[data-testid="stSidebar"] button[kind="secondary"] {background:transparent;border-color:transparent;}
[data-testid="stSidebar"] button[kind="secondary"]:hover {background:color-mix(in srgb,currentColor 12%,transparent);}
[data-testid="stSidebar"] .st-key-sidebar_conversations {
 margin-top:8px;height:auto;max-height:max(100px,calc(100dvh - 428px));
 overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;gap:12px;}
[data-testid="stSidebar"] .st-key-sidebar_conversations [data-testid="stVerticalBlock"] {gap:12px;}
[data-testid="stSidebar"] .st-key-sidebar_conversations button {
 min-height:44px;padding:10px 12px;justify-content:flex-start !important;text-align:left !important;}
[data-testid="stSidebar"] .st-key-sidebar_conversations button > div {
 width:100%;justify-content:flex-start !important;text-align:left;}
[data-testid="stSidebar"] .st-key-sidebar_conversations button [data-testid="stMarkdownContainer"] {
 flex:1;min-width:0;text-align:left;}
[data-testid="stSidebar"] .st-key-sidebar_conversations [data-testid="stCaptionContainer"] {padding-left:16px;}
.st-key-sidebar_conversations button p {white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:210px;text-align:left !important;}
[data-testid="stChatMessage"] {background:transparent;border-radius:6px;padding:14px 12px;gap:12px;}
[data-testid="stChatMessage"]:hover {background:color-mix(in srgb,currentColor 3%,transparent);}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {border-radius:8px;}
[data-testid="stChatMessageContent"] p {line-height:1.7;}
[data-testid="stChatInput"] {border:1px solid color-mix(in srgb,currentColor 30%,transparent);border-radius:9px;}
.st-key-login_panel {max-width:460px;margin:6vh auto 0;padding:32px;
 border:1px solid color-mix(in srgb,currentColor 18%,transparent);border-radius:12px;}
.st-key-login_panel h1 {font-size:28px;letter-spacing:-.8px;}
.st-key-welcome_panel {max-width:760px;margin:clamp(24px,8vh,80px) auto;padding:36px 24px;
 border:1px solid color-mix(in srgb,currentColor 14%,transparent);border-radius:12px;
 background:color-mix(in srgb,currentColor 2%,transparent);}
.welcome-copy {text-align:center;}
.welcome-copy .workspace-mark {width:64px;height:64px;font-size:34px;border-radius:14px;margin:0 auto 24px;}
.welcome-copy h2 {font-size:28px;font-weight:750;letter-spacing:-.7px;padding:0;}
.welcome-copy p {line-height:1.8;font-size:15px;opacity:.8;margin:16px 0;}
.welcome-topics {display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:22px 0 28px;}
.welcome-topics span {font-size:13px;border:1px solid color-mix(in srgb,currentColor 18%,transparent);
 border-radius:6px;padding:6px 12px;}
.st-key-welcome_cta {max-width:240px;margin:0 auto;}
.st-key-welcome_cta button {min-height:46px;}
.welcome-hint {text-align:center;font-size:12px;opacity:.7;margin:12px 0 0;}
.st-key-new_conversation {max-width:960px;padding:24px 0;}
.conversation-intro {padding:8px 12px 24px;border-bottom:1px solid color-mix(in srgb,currentColor 15%,transparent);}
.conversation-intro .workspace-mark {width:56px;height:56px;font-size:32px;border-radius:12px;margin-bottom:20px;}
.conversation-intro h2 {font-size:26px;font-weight:750;letter-spacing:-.6px;margin:0;padding:0;}
.conversation-intro p {font-size:15px;line-height:1.7;opacity:.75;margin:10px 0 0;}
.st-key-conversation_starters {padding:12px;}
.st-key-conversation_starters button {text-align:left;justify-content:flex-start;min-height:64px;
 border-radius:8px;background:color-mix(in srgb,currentColor 3%,transparent);}
.st-key-conversation_starters button:hover {background:color-mix(in srgb,currentColor 8%,transparent);}
@media(max-width:700px) {
 .block-container {padding:5rem 1rem 2rem;}
 .st-key-login_panel {margin:1rem auto;padding:22px;}
}
</style>
""", unsafe_allow_html=True)


def workspace_brand():
    st.markdown('<div class="workspace-brand"><div class="workspace-mark">H</div>'
                '<div><strong>AskHR</strong><small>우리 회사 HR 워크스페이스</small></div></div>',
                unsafe_allow_html=True)


def page_header(title, subtitle):
    st.markdown(f'<header class="workspace-header"><h1>{escape(title)}</h1>'
                f'<p>{escape(subtitle)}</p></header>', unsafe_allow_html=True)
