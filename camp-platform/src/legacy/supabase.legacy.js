import { createClient } from "@supabase/supabase-js";
import { publicEnv } from "../shared/config/publicEnv.js";

const supabaseUrl = publicEnv.supabaseUrl;
const supabaseKey = publicEnv.supabaseAnonKey;

export const supabase = createClient(supabaseUrl, supabaseKey);
