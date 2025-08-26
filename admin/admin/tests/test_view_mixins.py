from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.views import View
from told_common.view_mixins import (
    CatchErrorsMixin,
    GetFormView,
    PreventDoubleSubmitMixin,
)


class DummyForm:
    def __init__(self, valid=True):
        self._valid = valid

    def is_valid(self):
        return self._valid


class GetFormViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = GetFormView()

    def test_get_calls_form_valid_when_form_is_valid(self):
        request = self.factory.get("/dummy-url")
        form = DummyForm(valid=True)
        self.view.request = request
        self.view.get_form = MagicMock(return_value=form)
        self.view.form_valid = MagicMock(return_value=HttpResponse("valid"))

        response = self.view.get(request)

        self.view.get_form.assert_called_once()
        self.view.form_valid.assert_called_once_with(form)
        self.assertEqual(response.content, b"valid")

    def test_get_calls_form_invalid_when_form_is_invalid(self):
        request = self.factory.get("/dummy-url")
        form = DummyForm(valid=False)
        self.view.request = request
        self.view.get_form = MagicMock(return_value=form)
        self.view.form_invalid = MagicMock(return_value=HttpResponse("invalid"))

        response = self.view.get(request)

        self.view.get_form.assert_called_once()
        self.view.form_invalid.assert_called_once_with(form)
        self.assertEqual(response.content, b"invalid")


# Minimal base view that implements post()
class BasePostView(View):
    def post(self, request, *args, **kwargs):
        return HttpResponse("Processed")


class DummyFormView(PreventDoubleSubmitMixin, BasePostView):
    def get_success_url(self):
        return "/success/"


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class PreventDoubleSubmitMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def test_first_submission_processed(self):
        request = self.factory.post("/dummy/", {"field": "value"})
        request.session = {"user": {"id": 123}}
        view = DummyFormView.as_view()

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Processed")

    def test_duplicate_submission_redirected(self):
        request = self.factory.post("/dummy/", {"field": "value"})
        request.session = {"user": {"id": 123}}
        view = DummyFormView.as_view()

        # First submission
        response1 = view(request)
        self.assertEqual(response1.status_code, 200)

        # Second submission (same data) should redirect
        response2 = view(request)
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(response2["Location"], "/success/")


class CatchErrorsMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # Proper dummy view with View as base
        class DummyView(CatchErrorsMixin, View):
            def get(self, request, *args, **kwargs):
                return super().get(request, *args, **kwargs)

        self.view = DummyView.as_view()

    @patch("told_common.view_mixins.render")
    @patch("told_common.view_mixins.log")
    def test_provoke_error_get(self, mock_log, mock_render):
        request = self.factory.get("/test/?provoke_error=1")
        mock_render.return_value = HttpResponse("Rendered error page", status=500)

        self.view(request)

        # The mixin should catch the exception and call render
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertIn("Oh how you provoke me!", kwargs["context"]["message"])
        self.assertEqual(kwargs["status"], 500)

        # log.error should be called
        mock_log.error.assert_called_once()
