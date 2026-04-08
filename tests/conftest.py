import os
import pytest

# Garante que env vars de teste não quebram imports
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("UAZAPI_URL", "https://test.uazapi.com")
os.environ.setdefault("UAZAPI_TOKEN", "test-token")
os.environ.setdefault("UAZAPI_INSTANCE", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_xxx")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("SUCCESS_URL", "https://test.com/obrigado")
os.environ.setdefault("CANCEL_URL", "https://test.com/")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "eyJ.test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("BASE_URL", "https://test.com")
