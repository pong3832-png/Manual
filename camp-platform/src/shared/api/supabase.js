import { createClient } from "@supabase/supabase-js";
import { publicEnv } from "../config/publicEnv.js";

const supabaseUrl = publicEnv.supabaseUrl;
const supabaseKey = publicEnv.supabaseAnonKey;

const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);

function createEmptyQueryBuilder() {
  const builder = {
    select() {
      return builder;
    },
    eq() {
      return builder;
    },
    in() {
      return builder;
    },
    order() {
      return builder;
    },
    limit() {
      return builder;
    },
    insert() {
      return builder;
    },
    delete() {
      return builder;
    },
    update() {
      return builder;
    },
    single() {
      return Promise.resolve({ data: null, error: null });
    },
    maybeSingle() {
      return Promise.resolve({ data: null, error: null });
    },
    then(resolve) {
      return Promise.resolve(resolve({ data: [], error: null }));
    },
  };

  return builder;
}

function createDisabledAuth() {
  const disabledError = { message: "Supabase 설정이 없어 인증 기능을 사용할 수 없습니다." };

  return {
    getSession() {
      return Promise.resolve({ data: { session: null }, error: null });
    },
    onAuthStateChange() {
      return {
        data: {
          subscription: {
            unsubscribe() {},
          },
        },
      };
    },
    signInWithPassword() {
      return Promise.resolve({ data: null, error: disabledError });
    },
    signUp() {
      return Promise.resolve({ data: null, error: disabledError });
    },
    resetPasswordForEmail() {
      return Promise.resolve({ data: null, error: disabledError });
    },
    updateUser() {
      return Promise.resolve({ data: null, error: disabledError });
    },
    signOut() {
      return Promise.resolve({ error: null });
    },
  };
}

const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseKey)
  : {
      from() {
        return createEmptyQueryBuilder();
      },
      auth: createDisabledAuth(),
    };

export { isSupabaseConfigured, supabase };
