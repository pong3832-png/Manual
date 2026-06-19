import { useEffect, useState, useCallback } from "react";
import { supabase } from "../../../shared/api/supabase";

export default function useUserActivity(user) {
  const userId = user?.id ?? null;
  const [profileState, setProfileState] = useState({ userId: null, data: null });
  const [favoritesState, setFavoritesState] = useState({ userId: null, data: [] });
  const [applicationsState, setApplicationsState] = useState({ userId: null, data: [] });

  const fetchProfile = useCallback(async (targetUserId) => {
    const { data } = await supabase.from("profiles").select("*").eq("id", targetUserId).single();
    return data || null;
  }, []);

  const fetchFavorites = useCallback(async (targetUserId) => {
    const { data } = await supabase
      .from("favorites")
      .select("*")
      .eq("user_id", targetUserId)
      .order("created_at", { ascending: false });

    return data || [];
  }, []);

  const loadApplications = useCallback(async (userId) => {
    const { data } = await supabase
      .from("applications")
      .select("*")
      .eq("user_id", userId)
      .order("applied_at", { ascending: false });

    setApplicationsState({ userId, data: data || [] });
  }, []);

  const fetchApplications = useCallback(async (targetUserId) => {
    const { data } = await supabase
      .from("applications")
      .select("*")
      .eq("user_id", targetUserId)
      .order("applied_at", { ascending: false });

    return data || [];
  }, []);

  const loadProfile = useCallback(async (targetUserId) => {
    const data = await fetchProfile(targetUserId);
    setProfileState({ userId: targetUserId, data });
    return data;
  }, [fetchProfile]);

  useEffect(() => {
    if (!userId) return;

    let isActive = true;

    const loadUserActivity = async () => {
      const [profile, favorites, applications] = await Promise.all([
        fetchProfile(userId),
        fetchFavorites(userId),
        fetchApplications(userId),
      ]);

      if (!isActive) return;

      setProfileState({ userId, data: profile });
      setFavoritesState({ userId, data: favorites });
      setApplicationsState({ userId, data: applications });
    };

    void loadUserActivity();
    return () => {
      isActive = false;
    };
  }, [userId, fetchProfile, fetchFavorites, fetchApplications]);

  const profile = profileState.userId === userId ? profileState.data : null;
  const favorites = favoritesState.userId === userId ? favoritesState.data : [];
  const applications = applicationsState.userId === userId ? applicationsState.data : [];

  return {
    profile,
    favorites,
    applications,
    setFavorites: (nextValue) => {
      setFavoritesState((prev) => ({
        userId,
        data: typeof nextValue === "function" ? nextValue(prev.userId === userId ? prev.data : []) : nextValue,
      }));
    },
    setApplications: (nextValue) => {
      setApplicationsState((prev) => ({
        userId,
        data: typeof nextValue === "function" ? nextValue(prev.userId === userId ? prev.data : []) : nextValue,
      }));
    },
    loadApplications,
    loadProfile,
  };
}
