const fs = require("fs");
const path = require("path");
const { createClient } = require("@supabase/supabase-js");

const projectRoot = path.resolve(__dirname, "..", "..");

function loadDotEnv() {
  const envPath = path.join(projectRoot, ".env");
  if (!fs.existsSync(envPath)) return;

  const envContent = fs.readFileSync(envPath, "utf-8");
  for (const rawLine of envContent.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) continue;

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    if (key && !(key in process.env)) process.env[key] = value;
  }
}

async function checkTable(supabase, tableName) {
  const { error } = await supabase
    .from(tableName)
    .select("id", { head: true, count: "exact" })
    .limit(1);

  if (error) {
    throw new Error(`${tableName}: ${error.message}`);
  }
}

async function main() {
  loadDotEnv();

  const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.VITE_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error("missing Supabase URL or key");
  }

  const supabase = createClient(supabaseUrl, supabaseKey, {
    auth: { persistSession: false },
  });

  await checkTable(supabase, "platforms");
  await checkTable(supabase, "campaigns");
  console.log("Supabase connection OK: platforms/campaigns reachable");
}

main().catch((error) => {
  console.error(`Supabase connection failed: ${error.message}`);
  process.exit(1);
});
