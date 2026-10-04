-- pg_cron sweeper (#68, spec section 7): every minute, POST /api/jobs/process-pending on the
-- production alias, so calls the webhook's background task missed (cut-off, crash) still get
-- processed. The admin secret is read from Vault at run time (rotate it without a migration)
-- and is never stored in this file.
--
-- Main agent steps, in order:
--   1. create the Vault secret once with a local psycopg script:
--        select vault.create_secret(%s, 'hotline_admin_secret')   -- value from .env, never printed
--   2. `supabase db push` from the main checkout (never MCP apply_migration)
--   3. checks:
--        select jobname, schedule, active from cron.job;
--          -> hotline-process-pending, * * * * *, true
--        -- after ~2 minutes:
--        select status_code, created from net._http_response order by created desc limit 3;
--          -> 200s (401 means the Vault secret is missing or differs from HOTLINE_ADMIN_SECRET)

create extension if not exists pg_cron;
create extension if not exists pg_net;

select cron.unschedule(jobid) from cron.job where jobname = 'hotline-process-pending';

select cron.schedule(
    'hotline-process-pending',
    '* * * * *',
    $job$
    select net.http_post(
        url := 'https://hack-nation-world-bank-agriculture.vercel.app/api/jobs/process-pending',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Hotline-Admin-Secret',
            (select decrypted_secret from vault.decrypted_secrets where name = 'hotline_admin_secret')
        ),
        body := '{}'::jsonb,
        timeout_milliseconds := 290000
    );
    $job$
);
