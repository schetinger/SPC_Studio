"""
Tests for deployment infrastructure: settings split, production config.
Uses TDD vertical slices — one behavior at a time.
"""
import os
import importlib
from django.test import TestCase


class SettingsDevelopmentTest(TestCase):
    """Ciclo 1 — Settings de desenvolvimento carregam SQLite e InMemoryChannelLayer."""

    def test_development_usa_sqlite(self):
        from cep.settings import development
        self.assertIn('sqlite3', development.DATABASES['default']['ENGINE'])

    def test_development_usa_in_memory_channel_layer(self):
        from cep.settings import development
        self.assertEqual(
            development.CHANNEL_LAYERS['default']['BACKEND'],
            'channels.layers.InMemoryChannelLayer',
        )

    def test_development_debug_true(self):
        from cep.settings import development
        self.assertTrue(development.DEBUG)


class SettingsProductionTest(TestCase):
    """Ciclo 2 — Settings de produção resolvem DATABASE_URL e REDIS_URL de env vars."""

    def test_production_debug_false(self):
        os.environ['SECRET_KEY'] = 'test-secret-key-for-ci'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        os.environ['REDIS_URL'] = 'redis://default:token@host:6379'
        try:
            from cep.settings import production
            importlib.reload(production)
            self.assertFalse(production.DEBUG)
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['DATABASE_URL']
            del os.environ['REDIS_URL']

    def test_production_usa_postgresql(self):
        os.environ['SECRET_KEY'] = 'test-secret-key-for-ci'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        os.environ['REDIS_URL'] = 'redis://default:token@host:6379'
        try:
            from cep.settings import production
            importlib.reload(production)
            self.assertIn('postgresql', production.DATABASES['default']['ENGINE'])
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['DATABASE_URL']
            del os.environ['REDIS_URL']

    def test_production_converte_redis_para_rediss(self):
        """Upstash fornece redis://, mas channels_redis precisa de rediss:// (TLS)."""
        os.environ['SECRET_KEY'] = 'test-secret-key-for-ci'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        os.environ['REDIS_URL'] = 'redis://default:token@host:6379'
        try:
            from cep.settings import production
            importlib.reload(production)
            redis_host = production.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
            self.assertTrue(
                redis_host.startswith('rediss://'),
                f"Esperava rediss:// mas obteve: {redis_host}"
            )
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['DATABASE_URL']
            del os.environ['REDIS_URL']

    def test_production_whitenoise_no_middleware(self):
        os.environ['SECRET_KEY'] = 'test-secret-key-for-ci'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        os.environ['REDIS_URL'] = 'redis://default:token@host:6379'
        try:
            from cep.settings import production
            importlib.reload(production)
            self.assertIn(
                'whitenoise.middleware.WhiteNoiseMiddleware',
                production.MIDDLEWARE,
            )
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['DATABASE_URL']
            del os.environ['REDIS_URL']

    def test_production_onrender_em_allowed_hosts(self):
        os.environ['SECRET_KEY'] = 'test-secret-key-for-ci'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        os.environ['REDIS_URL'] = 'redis://default:token@host:6379'
        try:
            from cep.settings import production
            importlib.reload(production)
            self.assertIn('.onrender.com', production.ALLOWED_HOSTS)
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['DATABASE_URL']
            del os.environ['REDIS_URL']
