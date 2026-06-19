import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "../../../shared/api/supabase";

function groupMetricsByConnection(metrics = []) {
  const byConnection = new Map();

  metrics.forEach((metric) => {
    const connectionId = metric?.connection_id;
    if (!connectionId) return;
    const current = byConnection.get(connectionId) || [];
    current.push(metric);
    byConnection.set(connectionId, current);
  });

  return byConnection;
}

function createEmptySocialState(userId = null) {
  return {
    userId,
    connections: [],
    metrics: [],
    error: null,
    isLoading: false,
  };
}

function useSocialConnections(user) {
  const userId = user?.id || null;
  const [state, setState] = useState(() => createEmptySocialState());

  const fetchSocialConnections = useCallback(async (targetUserId) => {
    if (!targetUserId) {
      return createEmptySocialState();
    }

    const { data: connections, error: connectionsError } = await supabase
      .from("social_connections")
      .select("*")
      .eq("user_id", targetUserId)
      .order("created_at", { ascending: false });

    if (connectionsError) {
      return {
        ...createEmptySocialState(targetUserId),
        error: connectionsError,
      };
    }

    const connectionIds = (connections || []).map((connection) => connection.id);
    const { data: metrics, error: metricsError } = connectionIds.length > 0
      ? await supabase
        .from("social_metrics")
        .select("*")
        .in("connection_id", connectionIds)
        .order("captured_at", { ascending: false })
      : { data: [], error: null };

    return {
      userId: targetUserId,
      connections: connections || [],
      metrics: metrics || [],
      error: metricsError || null,
      isLoading: false,
    };
  }, []);

  const loadSocialConnections = useCallback(async (targetUserId = userId) => {
    if (!targetUserId) {
      const emptyState = createEmptySocialState();
      setState(emptyState);
      return emptyState;
    }

    setState((prev) => ({
      ...prev,
      userId: targetUserId,
      error: null,
      isLoading: true,
    }));

    const nextState = await fetchSocialConnections(targetUserId);
    setState(nextState);
    return nextState;
  }, [fetchSocialConnections, userId]);

  useEffect(() => {
    if (!userId) return undefined;

    let isActive = true;
    const loadInitialSocialConnections = async () => {
      const nextState = await fetchSocialConnections(userId);
      if (isActive) setState(nextState);
    };

    void loadInitialSocialConnections();
    return () => {
      isActive = false;
    };
  }, [fetchSocialConnections, userId]);

  const isCurrentUserState = state.userId === userId;
  const metricsByConnection = useMemo(
    () => groupMetricsByConnection(isCurrentUserState ? state.metrics : []),
    [isCurrentUserState, state.metrics],
  );

  return {
    connections: isCurrentUserState ? state.connections : [],
    metrics: isCurrentUserState ? state.metrics : [],
    metricsByConnection,
    error: isCurrentUserState ? state.error : null,
    isLoading: isCurrentUserState ? state.isLoading : false,
    loadSocialConnections,
  };
}

export default useSocialConnections;
