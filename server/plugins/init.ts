// Init phase.

import { applyMigrationsIfNeeded } from "~/utils/migration";

export default defineNitroPlugin(async (nitroApp) => {
  console.log("Initializing...")

  await applyMigrationsIfNeeded();

  console.log('Initialization completed.')
})
