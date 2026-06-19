function hasText(value) {
  return String(value || "").trim().length > 0;
}

function getCampaignKey(campaign = {}) {
  const platformId = campaign.platformId || campaign.platform_id || "";
  const id = campaign.id || campaign.external_id || "";
  return `${platformId}:${id}`;
}

function mergeCampaignPointsFromSnapshot(campaigns = [], snapshotCampaigns = []) {
  const snapshotPointByKey = new Map(
    (snapshotCampaigns || [])
      .filter((campaign) => campaign?.platformId === "dinner" || campaign?.platform_id === "dinner")
      .filter((campaign) => hasText(campaign?.point) || hasText(campaign?.reward_text))
      .map((campaign) => [getCampaignKey(campaign), String(campaign.point || campaign.reward_text).trim()]),
  );

  return (campaigns || []).map((campaign) => {
    if ((campaign?.platformId || campaign?.platform_id) !== "dinner" || hasText(campaign?.point)) {
      return campaign;
    }

    const snapshotPoint = snapshotPointByKey.get(getCampaignKey(campaign));
    if (!snapshotPoint) return campaign;

    return {
      ...campaign,
      point: snapshotPoint,
    };
  });
}

export {
  mergeCampaignPointsFromSnapshot,
};