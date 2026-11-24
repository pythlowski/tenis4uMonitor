import logging
from datetime import time

import pytest
from pydantic import ValidationError

from models.court_type import CourtType
from tests.conftest import BASE_TOML, PREFIX

GLOBAL = {f"{PREFIX}DISCORD__GLOBAL_WEBHOOK_URL": "https://discord.test/global"}
TWO_FACILITIES = """
[discord]
mode = "{mode}"

[[facilities]]
key = "tenis4u_104"
name = "Hala XYZ"
provider = "tenis4u"
facility_id = 104
court_type = "badminton"

[[facilities]]
key = "blonia_badminton"
name = "Blonia"
provider = "tenis4u"
facility_id = "958662f0-0bd2-4fdc-8bef-bb2d69761adb"
court_type = "padel"
"""


def facility_env(key: str) -> str:
    return f"{PREFIX}DISCORD__FACILITY__{key.upper()}_WEBHOOK_URL"


class TestDefaults:
    def test_global_filters_and_default_weekdays_include_saturday(self, make_settings):
        settings = make_settings()
        assert settings.begin_time == time(16, 30)
        assert settings.end_time == time(22, 30)
        assert settings.min_duration_minutes == 60
        assert settings.days_ahead == 7
        assert "Saturday" in settings.weekdays and len(settings.weekdays) == 7
        assert settings.filters.weekdays == tuple(settings.weekdays)

    def test_global_filters_from_toml(self, make_settings):
        toml = 'begin_time = "17:00"\nend_time = "21:00"\nmin_duration_minutes = 90\nweekdays = ["Monday"]\n' + BASE_TOML
        settings = make_settings(toml)
        assert (settings.begin_time, settings.end_time) == (time(17), time(21))
        assert settings.filters.min_duration_minutes == 90
        assert settings.weekdays == ["Monday"]


class TestFacilities:
    def test_parses_facility_list_and_coerces_int_id(self, make_settings):
        settings = make_settings(TWO_FACILITIES.format(mode="global"))
        first, second = settings.facilities
        assert first.facility_id == "104"
        assert first.court_type is CourtType.BADMINTON
        assert second.facility_id == "958662f0-0bd2-4fdc-8bef-bb2d69761adb"
        assert first.booking_url is None

    @pytest.mark.parametrize("key", ["Tenis4u", "tenis-4u", "tenis4u__104", "_x", "x_", ""])
    def test_invalid_key(self, make_settings, key):
        with pytest.raises(ValidationError, match="key"):
            make_settings(BASE_TOML.replace('"tenis4u_104"', f'"{key}"'))

    def test_duplicate_keys(self, make_settings):
        toml = TWO_FACILITIES.format(mode="global").replace("blonia_badminton", "tenis4u_104")
        with pytest.raises(ValidationError, match="duplicate facility keys"):
            make_settings(toml)

    def test_unknown_provider(self, make_settings):
        with pytest.raises(ValidationError, match="unknown provider"):
            make_settings(BASE_TOML.replace('provider = "tenis4u"', 'provider = "nope"'))

    def test_unknown_court_type(self, make_settings):
        with pytest.raises(ValidationError):
            make_settings(BASE_TOML.replace('"badminton"', '"squash"'))

    def test_at_least_one_facility(self, make_settings):
        with pytest.raises(ValidationError):
            make_settings('[discord]\nmode = "global"\n')


class TestFilterValidation:
    def test_bad_weekday(self, make_settings):
        with pytest.raises(ValidationError):
            make_settings('weekdays = ["Funday"]\n' + BASE_TOML)

    def test_begin_must_be_before_end(self, make_settings):
        with pytest.raises(ValidationError, match="begin_time"):
            make_settings('begin_time = "22:00"\nend_time = "22:00"\n' + BASE_TOML)

    @pytest.mark.parametrize("days", [0, 15])
    def test_days_ahead_bounds(self, make_settings, days):
        with pytest.raises(ValidationError):
            make_settings(f"days_ahead = {days}\n" + BASE_TOML)


class TestDiscordWebhooks:
    def test_facility_webhook_env_var_resolves(self, make_settings):
        env = {facility_env("tenis4u_104"): "https://discord.test/104"}
        settings = make_settings(BASE_TOML.replace('"global"', '"per_facility"'), env=env)
        webhook = settings.discord.facility_webhook("tenis4u_104")
        assert webhook is not None and webhook.get_secret_value() == "https://discord.test/104"

    def test_global_webhook_env_var_resolves(self, make_settings):
        settings = make_settings(env=GLOBAL)
        assert settings.discord.global_webhook_url.get_secret_value() == "https://discord.test/global"

    @pytest.mark.parametrize("mode", ["global", "both"])
    def test_missing_global_webhook(self, make_settings, mode):
        env = {facility_env("tenis4u_104"): "x", facility_env("blonia_badminton"): "y"}
        with pytest.raises(ValidationError, match="GLOBAL_WEBHOOK_URL"):
            make_settings(TWO_FACILITIES.format(mode=mode), env=env)

    @pytest.mark.parametrize("mode", ["per_facility", "both"])
    def test_missing_facility_webhook(self, make_settings, mode):
        env = {**GLOBAL, facility_env("tenis4u_104"): "x"}
        with pytest.raises(ValidationError, match="BLONIA_BADMINTON_WEBHOOK_URL"):
            make_settings(TWO_FACILITIES.format(mode=mode), env=env)

    def test_both_mode_with_all_webhooks(self, make_settings):
        env = {**GLOBAL, facility_env("tenis4u_104"): "x", facility_env("blonia_badminton"): "y"}
        settings = make_settings(TWO_FACILITIES.format(mode="both"), env=env)
        assert settings.discord.sends_global and settings.discord.sends_per_facility

    def test_empty_global_webhook_counts_as_missing(self, make_settings):
        with pytest.raises(ValidationError, match="GLOBAL_WEBHOOK_URL"):
            make_settings(env={f"{PREFIX}DISCORD__GLOBAL_WEBHOOK_URL": ""})

    def test_extra_facility_webhook_logs_warning(self, make_settings, caplog):
        env = {**GLOBAL, facility_env("typo_key"): "x"}
        with caplog.at_level(logging.WARNING, logger="SETTINGS"):
            make_settings(env=env)
        assert "typo_key_webhook_url" in caplog.text
