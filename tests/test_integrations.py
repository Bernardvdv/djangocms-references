from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from cms.api import add_plugin, create_page, create_title
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_preview_url

from djangocms_alias.models import Alias as AliasModel, AliasContent, Category
from djangocms_alias.utils import is_versioning_enabled
from djangocms_versioning.constants import PUBLISHED, UNPUBLISHED

from djangocms_references.test_utils.factories import (
    PageVersionFactory,
    PollContentFactory,
)
from djangocms_references.test_utils.nested_references_app.models import (
    DeeplyNestedPoll,
    NestedPoll,
)


class AliasReferencesIntegrationTestCase(CMSTestCase):
    def test_aliases_references_integration(self):
        """
        When opening the references for a given alias, the objects which reference it should be listed
        """
        user = self.get_superuser()
        category = Category.objects.create(name="References Integration Alias Category")
        alias = AliasModel.objects.create(
            category=category,
            position=0,
        )
        AliasContent.objects.create(
            alias=alias,
            name="Alias Content",
            language="en",
        )
        kwargs = {}
        if is_versioning_enabled():
            kwargs = {"created_by": user}
        page = create_page(
            title="References Integration Page",
            template="page.html",
            language="en",
            menu_title="",
            in_navigation=True,
            **kwargs
        )
        if is_versioning_enabled():
            page_content = create_title("en", "Draft Page", page, created_by=user)
        else:
            page_content = page.pagecontent_set.last()
        placeholder = page_content.get_placeholders().get(
            slot="content"
        )
        alias_plugin = add_plugin(
            placeholder,
            "Alias",
            language="en",
            template="default",
            alias=alias,
        )
        alias_content_type = ContentType.objects.get(app_label="djangocms_alias", model="alias")

        references_endpoint = reverse(
            "djangocms_references:references-index",
            kwargs={"content_type_id": alias_content_type.id, "object_id": alias.id}
        )
        with self.login_user_context(user):
            response = self.client.get(references_endpoint)

        self.assertContains(response, alias.name)
        self.assertContains(response, alias_plugin.plugin_type.lower())
        self.assertContains(response, "pagecontent")
        self.assertContains(response, get_object_preview_url(page_content))
        self.assertContains(response, page_content.versions.first().state)


class NestedAppIntegrationTestCase(CMSTestCase):
    def test_nested_app_references(self):
        """
        A nested relationship should still be able to provide any references to an object.
        We ensure that the nested relationship can traverse through and find the reference
        and its attached page.
        """
        poll_content = PollContentFactory()
        poll = poll_content.poll
        nested_poll = NestedPoll.objects.create(poll=poll)
        deeply_nested_poll = DeeplyNestedPoll.objects.create(nested_poll=nested_poll)

        user = self.get_superuser()
        kwargs = {}
        if is_versioning_enabled():
            kwargs = {"created_by": user}
        page = create_page(
            title="References Nested Integration Test",
            template="page.html",
            language="en",
            menu_title="",
            in_navigation=True,
            **kwargs
        )
        if is_versioning_enabled():
            page_content = create_title("en", "Draft Page", page, created_by=user)
        else:
            page_content = page.pagecontent_set.last()
        placeholder = page_content.get_placeholders().get(
            slot="content"
        )
        add_plugin(
            placeholder,
            "DeeplyNestedPollPlugin",
            language="en",
            deeply_nested_poll=deeply_nested_poll,
        )

        poll_content_type = ContentType.objects.get(app_label="polls", model="poll")
        references_endpoint = reverse(
            "djangocms_references:references-index",
            kwargs={"content_type_id": poll_content_type.id, "object_id": poll.id}
        )

        with self.login_user_context(user):
            response = self.client.get(references_endpoint)

        self.assertContains(response, poll_content)
        self.assertContains(response, "pagecontent")
        self.assertContains(response, get_object_preview_url(page_content))
        self.assertContains(response, page_content.versions.first().state)


class VersioningIntegrationTestCase(CMSTestCase):
    def test_unpublish_versioned_item(self):
        """
        When unpublishing a versioned item, the state should be changed to unpublish
        """
        user = self.get_superuser()
        version = PageVersionFactory(
            content__title="test", content__language="en", state=PUBLISHED
        )

        # Changing version state to unpublished
        version.unpublish(user)

        # Version state should be unpublished
        self.assertEqual(version.state, UNPUBLISHED)
