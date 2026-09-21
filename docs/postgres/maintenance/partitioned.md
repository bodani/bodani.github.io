ALTER SYSTEM SET idle_in_transaction_session_timeout = '2h';
SELECT pg_reload_conf();