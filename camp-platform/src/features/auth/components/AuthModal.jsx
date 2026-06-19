import { useEffect, useMemo, useState } from "react";
import { supabase } from "../../../shared/api/supabase";
import { SITE_NAME } from "../../../shared/config/site";

function normalizeBlogUrl(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

async function syncSignupProfile(user, name, blogUrl) {
  if (!user?.id) return;

  const profilePayload = {
    name: String(name || "").trim(),
    blog_url: blogUrl,
  };

  const { data: updatedProfile, error: updateError } = await supabase
    .from("profiles")
    .update(profilePayload)
    .eq("id", user.id)
    .select("id")
    .maybeSingle();

  const { error: insertError } = !updateError && !updatedProfile
    ? await supabase.from("profiles").insert({
      id: user.id,
      ...profilePayload,
    })
    : { error: null };

  const error = updateError || insertError;
  if (error) {
    console.warn("Profile metadata will be synced by database trigger when available.", error.message);
  }
}

function AuthModal({ mode, setMode, onClose, showToast }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [blogUrl, setBlogUrl] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const isRecoveryLink = useMemo(() => window.location.hash.includes("type=recovery"), []);

  useEffect(() => {
    if (isRecoveryLink && mode !== "reset") {
      setMode("reset");
    }
  }, [isRecoveryLink, mode, setMode]);

  async function handleLogin() {
    if (!email || !password) {
      showToast("이메일과 비밀번호를 입력해 주세요.", "error");
      return;
    }

    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);

    if (error) {
      showToast("이메일 또는 비밀번호가 올바르지 않습니다.", "error");
      return;
    }

    showToast("로그인되었습니다.");
    onClose();
  }

  async function handleSignup() {
    if (!email || !password || !name) {
      showToast("이름, 이메일, 비밀번호를 모두 입력해 주세요.", "error");
      return;
    }

    const normalizedName = name.trim();
    const normalizedBlogUrl = normalizeBlogUrl(blogUrl);

    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: {
          name: normalizedName,
          blog_url: normalizedBlogUrl,
        },
      },
    });

    if (!error) {
      await syncSignupProfile(data?.user, normalizedName, normalizedBlogUrl);
    }

    setLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("가입이 완료되었습니다. 이메일 인증이 필요한 경우 메일함을 확인해 주세요.");
    onClose();
  }

  async function handleResetRequest() {
    if (!email) {
      showToast("비밀번호를 재설정할 이메일을 입력해 주세요.", "error");
      return;
    }

    setLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    setLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("비밀번호 재설정 메일을 보냈습니다.");
    setMode("login");
  }

  async function handlePasswordUpdate() {
    if (!resetPassword || !resetPasswordConfirm) {
      showToast("새 비밀번호를 모두 입력해 주세요.", "error");
      return;
    }

    if (resetPassword.length < 8) {
      showToast("비밀번호는 8자 이상이어야 합니다.", "error");
      return;
    }

    if (resetPassword !== resetPasswordConfirm) {
      showToast("비밀번호 확인이 일치하지 않습니다.", "error");
      return;
    }

    setLoading(true);
    const { error } = await supabase.auth.updateUser({ password: resetPassword });
    setLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    window.history.replaceState({}, "", window.location.pathname + window.location.search);
    setResetPassword("");
    setResetPasswordConfirm("");
    showToast("비밀번호를 변경했습니다. 새 비밀번호로 다시 로그인해 주세요.");
    setMode("login");
  }

  const isLogin = mode === "login";
  const isSignup = mode === "signup";
  const isForgot = mode === "forgot";
  const isReset = mode === "reset";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet auth-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="modal-handle"><div className="modal-handle-bar" /></div>
        <div style={{ padding: "20px 24px 24px" }}>
          <div className="auth-hero">
            <div className="auth-hero-kicker">
              {isLogin ? "Welcome Back" : isSignup ? "Start Clean" : isForgot ? "Password Support" : "Secure Reset"}
            </div>
            <div className="auth-hero-copy">
              {isLogin && "저장한 후보와 지원 현황을 이어서 관리할 수 있습니다."}
              {isSignup && "필수 정보만 입력하면 바로 저장과 현황 추적을 시작할 수 있습니다."}
              {isForgot && "가입한 이메일로 비밀번호 재설정 링크를 보냅니다."}
              {isReset && "보안을 위해 새로운 비밀번호로 교체합니다."}
            </div>
          </div>

          {!isForgot && !isReset && (
            <div className="auth-tabs">
              {["login", "signup"].map((tabMode) => (
                <div key={tabMode} className={`auth-tab ${mode === tabMode ? "active" : ""}`} onClick={() => setMode(tabMode)}>
                  {tabMode === "login" ? "로그인" : "회원가입"}
                </div>
              ))}
            </div>
          )}

          {isLogin && (
            <>
              <div style={{ fontSize: 22, fontWeight: 900, marginBottom: 6 }}>다시 돌아오셨군요</div>
              <div style={{ fontSize: 13, color: "#aaa", marginBottom: 24 }}>저장한 체험단과 지원 현황을 이어서 볼 수 있습니다.</div>
              <div className="auth-field">
                <label>이메일</label>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="example@email.com" />
              </div>
              <div className="auth-field">
                <label>비밀번호</label>
                <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="비밀번호 입력" />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -6, marginBottom: 16 }}>
                <button type="button" onClick={() => setMode("forgot")} style={{ border: "none", background: "transparent", color: "#888", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                  비밀번호를 잊으셨나요?
                </button>
              </div>
              <button className="auth-submit" onClick={handleLogin} disabled={loading}>{loading ? "로그인 중..." : "로그인"}</button>
              <div className="auth-footnote">{SITE_NAME}는 원본 플랫폼의 지원 링크만 연결합니다.</div>
            </>
          )}

          {isSignup && (
            <>
              <div style={{ fontSize: 22, fontWeight: 900, marginBottom: 6 }}>{SITE_NAME} 시작하기</div>
              <div style={{ fontSize: 13, color: "#aaa", marginBottom: 24 }}>필수 정보만 입력하면 바로 즐겨찾기와 현황 관리를 시작할 수 있습니다.</div>
              <div className="auth-field">
                <label>이름</label>
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="표시 이름" />
              </div>
              <div className="auth-field">
                <label>이메일</label>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="example@email.com" />
              </div>
              <div className="auth-field">
                <label>비밀번호</label>
                <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="8자 이상" />
              </div>
              <div className="auth-field">
                <label>블로그 URL (선택)</label>
                <input value={blogUrl} onChange={(event) => setBlogUrl(event.target.value)} placeholder="blog.naver.com/myid" />
              </div>
              <button className="auth-submit" onClick={handleSignup} disabled={loading}>{loading ? "가입 중..." : "무료로 시작하기"}</button>
              <div className="auth-footnote">가입 후 바로 즐겨찾기와 지원 현황 기능을 사용할 수 있습니다.</div>
            </>
          )}

          {isForgot && (
            <>
              <div style={{ fontSize: 22, fontWeight: 900, marginBottom: 6 }}>비밀번호 재설정</div>
              <div style={{ fontSize: 13, color: "#aaa", marginBottom: 24 }}>가입한 이메일로 비밀번호 재설정 링크를 보냅니다.</div>
              <div className="auth-field">
                <label>이메일</label>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="example@email.com" />
              </div>
              <button className="auth-submit" onClick={handleResetRequest} disabled={loading}>{loading ? "메일 전송 중..." : "재설정 메일 보내기"}</button>
              <button type="button" onClick={() => setMode("login")} style={{ width: "100%", marginTop: 10, border: "none", background: "transparent", color: "#888", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                로그인으로 돌아가기
              </button>
            </>
          )}

          {isReset && (
            <>
              <div style={{ fontSize: 22, fontWeight: 900, marginBottom: 6 }}>새 비밀번호 설정</div>
              <div style={{ fontSize: 13, color: "#aaa", marginBottom: 24 }}>보안을 위해 8자 이상으로 설정해 주세요.</div>
              <div className="auth-field">
                <label>새 비밀번호</label>
                <input type="password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} placeholder="8자 이상" />
              </div>
              <div className="auth-field">
                <label>새 비밀번호 확인</label>
                <input type="password" value={resetPasswordConfirm} onChange={(event) => setResetPasswordConfirm(event.target.value)} placeholder="한 번 더 입력" />
              </div>
              <button className="auth-submit" onClick={handlePasswordUpdate} disabled={loading}>{loading ? "변경 중..." : "비밀번호 변경"}</button>
              <div className="auth-footnote">변경 후에는 새 비밀번호로 다시 로그인하면 됩니다.</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthModal;
