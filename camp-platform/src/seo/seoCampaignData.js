import fs from "node:fs";
import path from "node:path";

const PROJECT_ROOT = process.cwd();
const SNAPSHOT_PATH = path.join(PROJECT_ROOT, "public", "campaigns.json");

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function parseCampaignsSnapshot() {
  const raw = JSON.parse(fs.readFileSync(SNAPSHOT_PATH, "utf-8"));
  const campaigns = Array.isArray(raw) ? raw : raw.campaigns || [];
  return {
    updatedAt: cleanText(raw.updatedAt || raw.generatedAt || raw.completedAt),
    campaigns: campaigns.filter((campaign) => cleanText(campaign.id) && cleanText(campaign.title)),
  };
}

export function getSnapshotUpdatedAt() {
  return parseCampaignsSnapshot().updatedAt || new Date().toISOString();
}

export function formatSnapshotUpdatedAt(value = getSnapshotUpdatedAt()) {
  const source = cleanText(value);
  const parsed = Date.parse(source);
  if (!Number.isFinite(parsed)) return source;

  const kstDate = new Date(parsed + (9 * 60 * 60 * 1000));
  const year = kstDate.getUTCFullYear();
  const month = String(kstDate.getUTCMonth() + 1).padStart(2, "0");
  const day = String(kstDate.getUTCDate()).padStart(2, "0");
  const hour = String(kstDate.getUTCHours()).padStart(2, "0");
  const minute = String(kstDate.getUTCMinutes()).padStart(2, "0");
  return `${year}.${month}.${day} ${hour}:${minute} KST`;
}

function campaignSearchText(campaign) {
  return [
    campaign.title,
    campaign.category,
    campaign.platform,
    campaign.platformId,
    campaign.province,
    campaign.city,
    campaign.address,
    campaign.addressRaw,
    campaign.locationRaw,
    campaign.campaignType,
    campaign.campaign_type,
    campaign.type,
    campaign.campaignMode,
    campaign.campaign_mode,
    campaign.point,
    campaign.rewardText,
    campaign.reward_text,
    campaign.channel,
    campaign.media,
  ].map(cleanText).join(" ");
}

function hasKeyword(campaign, keywords = []) {
  if (!keywords.length) return true;
  const text = campaignSearchText(campaign);
  return keywords.some((keyword) => text.includes(keyword));
}

function keywordGroupMatches(text, group) {
  if (Array.isArray(group)) {
    return group.some((keyword) => text.includes(keyword));
  }
  return text.includes(group);
}

function hasTextKeywordGroups(campaign, groups = []) {
  if (!groups.length) return true;
  const text = campaignSearchText(campaign);
  return groups.every((group) => keywordGroupMatches(text, group));
}

function getCampaignTypeValues(campaign) {
  return [
    campaign.campaignType,
    campaign.campaign_type,
    campaign.type,
    campaign.campaignMode,
    campaign.campaign_mode,
  ].map(cleanText).filter(Boolean);
}

function matchesCampaignTypes(campaign, campaignTypes = []) {
  if (!campaignTypes.length) return true;
  const campaignValues = getCampaignTypeValues(campaign);
  return campaignTypes.some((campaignType) => campaignValues.includes(cleanText(campaignType)));
}

function isOpenCampaign(campaign) {
  if (cleanText(campaign.status) && cleanText(campaign.status) !== "open") return false;
  const dDay = Number(campaign.dDay);
  return !Number.isFinite(dDay) || dDay >= 0;
}

function matchesLanding(campaign, filters = {}) {
  if (!isOpenCampaign(campaign)) return false;
  if (filters.platformIds?.length && !filters.platformIds.includes(cleanText(campaign.platformId))) return false;
  if (filters.province && cleanText(campaign.province) !== filters.province) return false;
  if (!matchesCampaignTypes(campaign, filters.campaignTypes || [])) return false;
  if (Number.isFinite(filters.maxDday)) {
    const dDay = Number(campaign.dDay);
    if (!Number.isFinite(dDay) || dDay > filters.maxDday || dDay < 0) return false;
  }
  if (!hasKeyword(campaign, filters.categoryKeywords || [])) return false;
  if (!hasKeyword(campaign, filters.channelKeywords || [])) return false;
  if (!hasTextKeywordGroups(campaign, filters.textKeywords || [])) return false;
  return true;
}

function compareCampaigns(left, right) {
  const leftDday = Number.isFinite(Number(left.dDay)) ? Number(left.dDay) : 999;
  const rightDday = Number.isFinite(Number(right.dDay)) ? Number(right.dDay) : 999;
  if (leftDday !== rightDday) return leftDday - rightDday;
  const leftHasReward = cleanText(left.point || left.rewardText || left.reward_text) ? 1 : 0;
  const rightHasReward = cleanText(right.point || right.rewardText || right.reward_text) ? 1 : 0;
  if (leftHasReward !== rightHasReward) return rightHasReward - leftHasReward;
  return cleanText(left.title).localeCompare(cleanText(right.title), "ko");
}

export function getCampaignsForLanding(page, limit = 12) {
  const { campaigns } = parseCampaignsSnapshot();
  return campaigns
    .filter((campaign) => matchesLanding(campaign, page.filters || {}))
    .sort(compareCampaigns)
    .slice(0, limit)
    .map((campaign) => ({
      id: cleanText(campaign.id),
      title: cleanText(campaign.title),
      platform: cleanText(campaign.platform || campaign.platformId),
      category: cleanText(campaign.category),
      province: cleanText(campaign.province),
      city: cleanText(campaign.city),
      dDay: Number.isFinite(Number(campaign.dDay)) ? Number(campaign.dDay) : null,
      reward: cleanText(campaign.point || campaign.rewardText || campaign.reward_text),
      url: cleanText(campaign.url),
    }));
}

export function countCampaignsForLanding(page) {
  const { campaigns } = parseCampaignsSnapshot();
  return campaigns.filter((campaign) => matchesLanding(campaign, page.filters || {})).length;
}
