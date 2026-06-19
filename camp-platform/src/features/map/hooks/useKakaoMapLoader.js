import { useEffect, useState } from "react";
import { publicEnv } from "../../../shared/config/publicEnv.js";

const KAKAO_MAP_KEY = publicEnv.kakaoMapAppKey;
const SCRIPT_ID = "kakao-map-sdk";
const LOAD_TIMEOUT_MS = 15000;

function getKakaoMapScriptUrl() {
  if (!KAKAO_MAP_KEY) return "";
  return `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_MAP_KEY}&autoload=false&libraries=clusterer`;
}

function getMissingKeyError() {
  return "카카오맵 JavaScript 키가 없어 지도를 불러올 수 없습니다.";
}

function getDomainGuideError() {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `카카오맵 SDK를 불러오지 못했습니다. 카카오 디벨로퍼스의 사이트 도메인에 ${origin} 이 등록되어 있는지 확인해 주세요.`;
}

// ✅ Fix 1: 스크립트 로드 여부 (kakao.maps.load 함수 존재) — 초기화 완료 아님
function isKakaoSdkScriptLoaded() {
  return typeof window !== "undefined" && typeof window.kakao?.maps?.load === "function";
}

// ✅ Fix 1: 실제 SDK 초기화 완료 여부 — Map 생성자가 있어야 진짜 사용 가능
function isKakaoMapReady() {
  return typeof window !== "undefined" && typeof window.kakao?.maps?.Map === "function";
}

export default function useKakaoMapLoader() {
  const [state, setState] = useState(() => {
    if (!KAKAO_MAP_KEY) return { ready: false, error: getMissingKeyError() };
    // ✅ Fix 1: 초기 state는 Map 생성자가 실제로 있을 때만 ready: true
    if (isKakaoMapReady()) return { ready: true, error: "" };
    return { ready: false, error: "" };
  });

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    if (!KAKAO_MAP_KEY) return undefined;

    let canceled = false;
    let timeoutId = null;

    const finishWithError = (message) => {
      if (!canceled) setState({ ready: false, error: message });
    };

    // kakao.maps.load() 실행 — 이 콜백 안에서야 Map 등 실제 클래스 사용 가능
    const runKakaoLoad = () => {
      if (!isKakaoSdkScriptLoaded()) {
        finishWithError(getDomainGuideError());
        return;
      }
      window.kakao.maps.load(() => {
        if (!canceled) setState({ ready: true, error: "" });
      });
    };

    // ✅ Fix 2: 스크립트가 이미 로드 완료 상태 → load 이벤트 안 기다리고 바로 실행
    if (isKakaoSdkScriptLoaded()) {
      runKakaoLoad();
      return undefined;
    }

    // 스크립트 주입
    const nextSrc = getKakaoMapScriptUrl();
    let script = document.getElementById(SCRIPT_ID);

    if (script && script.getAttribute("src") !== nextSrc) {
      script.remove();
      script = null;
    }

    if (!script) {
      script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.src = nextSrc;
      script.async = true;
      document.head.appendChild(script);
    }

    // ✅ Fix 2: script가 DOM에 있지만 이미 로드 완료 상태인 경우 (이벤트 놓친 경우)
    if (script.readyState === "complete" || isKakaoSdkScriptLoaded()) {
      runKakaoLoad();
      return undefined;
    }

    const handleLoad = () => runKakaoLoad();
    const handleError = () => finishWithError(getDomainGuideError());

    script.addEventListener("load", handleLoad);
    script.addEventListener("error", handleError);

    timeoutId = window.setTimeout(() => {
      if (!isKakaoMapReady()) handleError();
    }, LOAD_TIMEOUT_MS);

    return () => {
      canceled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
      script?.removeEventListener("load", handleLoad);
      script?.removeEventListener("error", handleError);
    };
  }, []);

  return state;
}
