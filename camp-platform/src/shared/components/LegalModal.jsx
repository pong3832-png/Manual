import { useState } from "react";
import {
  isAnalyticsOptedOut,
  setAnalyticsOptOut,
  trackAnalyticsEvent,
} from "../../features/analytics/lib/analytics";
import {
  LEGAL_UPDATED_AT,
  PUBLIC_CONTACT_EMAIL,
  PUBLIC_OPERATOR_NAME,
  PUBLIC_SITE_URL,
  SITE_NAME,
  getContactMailto,
} from "../config/site";

const TABS = [
  { key: "privacy", label: "개인정보처리방침" },
  { key: "terms", label: "이용약관" },
  { key: "contact", label: "문의" },
];

function ContactBlock() {
  const mailto = getContactMailto(`${SITE_NAME} 문의`);

  return (
    <div className="legal-contact-card">
      <div>
        <strong>문의 이메일</strong>
        {PUBLIC_CONTACT_EMAIL ? (
          <a href={mailto}>{PUBLIC_CONTACT_EMAIL}</a>
        ) : (
          <span>배포 전 실제 문의 이메일을 설정해야 합니다.</span>
        )}
      </div>
      <p>
        {PUBLIC_CONTACT_EMAIL
          ? "광고 제휴, 개인정보 요청, 서비스 오류 신고는 이 주소로 접수합니다."
          : "실제 발매 전 VITE_PUBLIC_CONTACT_EMAIL에 운영 이메일을 넣어 주세요."}
      </p>
    </div>
  );
}

function AnalyticsPreferenceBlock() {
  const [isOptedOut, setIsOptedOutState] = useState(() => isAnalyticsOptedOut());

  const handleToggle = () => {
    const nextIsOptedOut = !isOptedOut;
    setAnalyticsOptOut(nextIsOptedOut);
    setIsOptedOutState(nextIsOptedOut);
    trackAnalyticsEvent(
      nextIsOptedOut ? "analytics_opt_out" : "analytics_opt_in",
      { metadata: { source: "privacy_modal" } },
      null,
      { ignoreOptOut: true },
    );
  };

  return (
    <section className="analytics-preference-card">
      <div>
        <h3>서비스 이용 분석 설정</h3>
        <p>
          검색 조건, 카테고리 선택, 캠페인 상세 열기, 즐겨찾기, 신청 버튼 클릭처럼 서비스 개선에 필요한 행동만 최소 범위로 기록합니다.
          검색어 원문, 비밀번호, 쿠키 값은 분석 이벤트에 저장하지 않습니다.
        </p>
      </div>
      <button
        type="button"
        className={`analytics-toggle ${isOptedOut ? "" : "active"}`}
        aria-pressed={!isOptedOut}
        onClick={handleToggle}
      >
        <span aria-hidden="true" />
        {isOptedOut ? "분석 수집 꺼짐" : "분석 수집 켜짐"}
      </button>
    </section>
  );
}

function PrivacyPanel() {
  return (
    <div className="legal-content">
      <p>
        {SITE_NAME}은 체험단 캠페인 검색, 즐겨찾기, 지원 현황 관리, 문의 응대를 위해 필요한 범위의
        개인정보만 처리합니다.
      </p>

      <section>
        <h3>수집 항목</h3>
        <ul>
          <li>회원가입 및 로그인: 이메일, 비밀번호 인증 정보, 이름, 선택 입력한 블로그 URL</li>
          <li>서비스 이용: 즐겨찾기, 지원 현황, 클릭한 캠페인 링크, 광고 노출 및 클릭 기록</li>
          <li>문의 처리: 문의자가 제공한 이메일 주소와 문의 내용</li>
        </ul>
      </section>

      <section>
        <h3>이용 목적</h3>
        <ul>
          <li>계정 생성, 로그인, 비밀번호 재설정</li>
          <li>사용자가 저장한 캠페인과 지원 현황 표시</li>
          <li>광고 성과 확인, 서비스 오류 분석, 부정 이용 방지</li>
          <li>문의 답변 및 운영 공지 전달</li>
        </ul>
      </section>

      <section>
        <h3>보관 및 파기</h3>
        <p>
          회원 정보와 저장 기록은 회원 탈퇴 또는 삭제 요청 시 지체 없이 파기합니다. 법령상 보관이 필요한
          기록은 해당 기간 동안 분리 보관합니다.
        </p>
      </section>

      <section>
        <h3>제3자 제공 및 처리 위탁</h3>
        <p>
          인증과 데이터 저장에는 Supabase가 사용됩니다. 캠페인 상세 지원은 각 원문 플랫폼에서 진행되며,
          원문 플랫폼 접속 이후의 개인정보 처리는 해당 플랫폼 정책을 따릅니다.
        </p>
      </section>

      <section>
        <h3>이용자 권리</h3>
        <p>
          이용자는 개인정보 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다. 요청은 문의 이메일로 접수합니다.
        </p>
      </section>

      <section>
        <h3>행태정보와 분석 이벤트</h3>
        <ul>
          <li>기록 항목: 화면 탭, 탐색 필터, 검색 사용 여부와 길이, 캠페인 상세 열기, 즐겨찾기, 신청 버튼 클릭</li>
          <li>식별 기준: 로그인 사용자는 계정 ID, 비로그인 사용자는 브라우저에 저장된 임의 ID와 세션 ID</li>
          <li>이용 목적: 인기 카테고리/지역 파악, UX 개선, 광고 성과 확인, 오류와 비정상 이용 탐지</li>
          <li>제외 항목: 검색어 원문, 비밀번호, 쿠키 값, 결제 정보, 외부 플랫폼 로그인 정보</li>
        </ul>
      </section>

      <AnalyticsPreferenceBlock />

      <ContactBlock />
    </div>
  );
}

function TermsPanel() {
  return (
    <div className="legal-content">
      <p>
        {SITE_NAME}은 여러 체험단 플랫폼의 공개 캠페인 정보를 모아 탐색할 수 있게 돕는 검색 및 관리
        서비스입니다. 실제 캠페인 신청, 선정, 혜택 제공은 각 원문 플랫폼에서 진행됩니다.
      </p>

      <section>
        <h3>서비스 범위</h3>
        <ul>
          <li>캠페인 목록, 지역, 마감일, 경쟁률, 지도 위치 정보 제공</li>
          <li>회원의 즐겨찾기와 지원 현황 저장</li>
          <li>원문 플랫폼으로 이동하는 외부 링크 제공</li>
        </ul>
      </section>

      <section>
        <h3>정보 정확성</h3>
        <p>
          캠페인 정보는 크롤링 시점의 데이터를 기반으로 하므로 원문 플랫폼의 최신 내용과 다를 수 있습니다.
          신청 전 모집 조건, 제공 내역, 마감일, 방문 가능 일정을 원문 페이지에서 다시 확인해야 합니다.
        </p>
      </section>

      <section>
        <h3>이용자 책임</h3>
        <p>
          이용자는 본인의 계정 정보를 안전하게 관리해야 하며, 캠페인 신청과 리뷰 작성 과정에서 각 원문
          플랫폼의 약관과 광고 표시 기준을 준수해야 합니다.
        </p>
      </section>

      <section>
        <h3>광고 및 제휴 링크</h3>
        <p>
          서비스에는 제휴 링크 또는 광고가 포함될 수 있으며, 광고 영역에는 광고 또는 제휴 사실을 표시합니다.
        </p>
      </section>

      <ContactBlock />
    </div>
  );
}

function ContactPanel() {
  return (
    <div className="legal-content">
      <ContactBlock />
      <section>
        <h3>운영 정보</h3>
        <dl className="legal-definition-list">
          <div>
            <dt>서비스명</dt>
            <dd>{SITE_NAME}</dd>
          </div>
          <div>
            <dt>운영자</dt>
            <dd>{PUBLIC_OPERATOR_NAME || "배포 전 설정 필요"}</dd>
          </div>
          <div>
            <dt>서비스 URL</dt>
            <dd>{PUBLIC_SITE_URL || "배포 전 설정 필요"}</dd>
          </div>
        </dl>
      </section>
      <section>
        <h3>처리 기준</h3>
        <p>
          개인정보 열람, 정정, 삭제 요청과 광고 제휴 문의는 동일한 문의 이메일로 접수합니다.
          접수 후 운영자가 내용과 계정 소유 여부를 확인한 뒤 처리합니다.
        </p>
      </section>
    </div>
  );
}

function LegalModal({ view = "privacy", onSelectView, onClose }) {
  const activeView = TABS.some((tab) => tab.key === view) ? view : "privacy";
  const activeTab = TABS.find((tab) => tab.key === activeView);

  return (
    <div className="modal-backdrop legal-backdrop" onClick={onClose}>
      <div className="modal-sheet legal-modal-sheet" onClick={(event) => event.stopPropagation()}>
        <div className="legal-modal-header">
          <div>
            <div className="legal-eyebrow">Legal</div>
            <h2>{activeTab.label}</h2>
            <p>최종 업데이트: {LEGAL_UPDATED_AT}</p>
          </div>
          <button type="button" className="legal-close-btn" onClick={onClose} aria-label="닫기">
            x
          </button>
        </div>

        <div className="legal-tabs" aria-label="정책 문서">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              className={`legal-tab ${activeView === tab.key ? "active" : ""}`}
              onClick={() => onSelectView(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeView === "privacy" && <PrivacyPanel />}
        {activeView === "terms" && <TermsPanel />}
        {activeView === "contact" && <ContactPanel />}
      </div>
    </div>
  );
}

export default LegalModal;
