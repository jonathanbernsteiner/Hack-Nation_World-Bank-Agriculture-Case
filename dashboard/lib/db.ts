import postgres from "postgres";

const globalForDb = globalThis as unknown as { __dashboardSql?: postgres.Sql };

function createClient(): postgres.Sql {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error("DATABASE_URL is not set. Add it to dashboard/.env.local.");
  }
  return postgres(url, { ssl: "require", prepare: false, max: 1, idle_timeout: 20 });
}

/** Lazy singleton so importing this module never fails at build time. */
export function getSql(): postgres.Sql {
  if (!globalForDb.__dashboardSql) {
    globalForDb.__dashboardSql = createClient();
  }
  return globalForDb.__dashboardSql;
}
