from supabase import create_client, Client

from app.core.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY.get_secret_value(),
)


def get_supabase() -> Client:
    return supabase
