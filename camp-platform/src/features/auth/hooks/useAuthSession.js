import { useEffect, useState } from "react";
import { supabase } from "../../../shared/api/supabase";

export default function useAuthSession() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active) {
        return;
      }
      setUser(session?.user ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return { user };
}
