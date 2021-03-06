import pkg_resources
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request

import logging
from six import iteritems, text_type
from django.conf import settings as DJANGO_SETTINGS
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String, Dict, Float, Boolean, List, DateTime, JSONField
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from lms.djangoapps.commerce.utils import EcommerceService
from xblockutils.resources import ResourceLoader
from django.template import Context, Template
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.urls import reverse


log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)
# Make '_' a no-op so we can scrape strings


def _(text): return text


def reify(meth):
    """
    Decorator which caches value so it is only computed once.
    Keyword arguments:
    inst
    """
    def getter(inst):
        """
        Set value to meth name in dict and returns value.
        """
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


class PaymentLinkXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name="Display Name",
        help="Display name for this module",
        default="Enlace de Pago",
        scope=Scope.settings,
    )
    has_author_view = True
    has_score = False
    editable_fields = ('display_name')

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @reify
    def block_course_id(self):
        """
        Return the course_id of the block.
        """
        return six.text_type(self.course_id)

    @reify
    def block_id(self):
        """
        Return the usage_id of the block.
        """
        return six.text_type(self.scope_ids.usage_id)

    def is_course_staff(self):
        # pylint: disable=no-member
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def show_staff_grading_interface(self):
        """
        Return if current user is staff and not in studio.
        """
        in_studio_preview = self.scope_ids.user_id is None
        return self.is_course_staff() and not in_studio_preview

    def author_view(self, context=None):
        context = self.get_context_author()
        template = self.render_template(
            'static/html/author_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/payment_link.css"))
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        fragment = Fragment()
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
        }
        fragment.content = self.render_template(
            'static/html/studio_view.html', context)
        fragment.add_css(self.resource_string("static/css/payment_link.css"))
        fragment.add_javascript(self.resource_string(
            "static/js/src/payment_link_studio.js"))
        fragment.initialize_js('PaymentLinkXBlock')
        return fragment

    def student_view(self, context=None):
        context = self.get_context_student()
        template = self.render_template(
            'static/html/payment_link.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/payment_link.css"))
        frag.add_javascript(self.resource_string(
            "static/js/src/payment_link.js"))
        frag.initialize_js('PaymentLinkXBlock')
        return frag

    def get_context_student(self):
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'is_enabled': False,
            'is_enrolled': True,
            'is_staff': False,
            'is_expired': self.is_course_expired()
        }
        from common.djangoapps.course_modes.models import CourseMode
        from common.djangoapps.student.models import CourseEnrollment
        from django.contrib.auth.models import User
        
        if self.show_staff_grading_interface():
            context['is_staff'] = True
        else:
            try:
                user = User.objects.get(id=self.scope_ids.user_id)
                enrollment = CourseEnrollment.get_enrollment(user, self.course_id)
            except Exception as e:
                log.error('PaymentLink - Error, Not Exists User or Enrollment, user: {}, course: {}, exception: {}'.format(self.scope_ids.user_id, self.course_id, str(e)))
                context.update({'is_enrolled': False})

        modes = CourseMode.modes_for_course_dict(self.course_id)
        if 'verified' in modes:
            ecommerce_service = EcommerceService()
            context.update({
                'is_enabled': True,
                'ecommerce_payment_page': ecommerce_service.payment_page_url(),
                'verified_sku': modes['verified'].sku
            })
        else:
            log.error('PaymentLink - Error, Course: {}  dont have verified_sku, user: {}'.format(self.course_id, self.scope_ids.user_id))
        return context

    def get_context_author(self):
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'is_enabled': False,
            'is_expired': self.is_course_expired()
        }
        from common.djangoapps.course_modes.models import CourseMode

        modes = CourseMode.modes_for_course_dict(self.course_id)
        if 'verified' in modes:
            ecommerce_service = EcommerceService()
            context.update({
                'is_enabled': True,
                'ecommerce_payment_page': ecommerce_service.payment_page_url(),
                'verified_sku': modes['verified'].sku
            })
        else:
            log.error('PaymentLink - Error, Course: {} dont have verified_sku'.format(self.course_id))
        return context

    def is_course_expired(self):
        """
            Verify if course is expired
        """
        from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
        now = timezone.now()
        course = CourseOverview.objects.get(id=self.course_id)
        if course.end_date is not None:
            return course.end_date < now
        return False

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        self.display_name = data.get('display_name')
        return {'result': 'success'}

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("PaymentLinkXBlock",
             """<payment_link/>
             """),
            ("Multiple PaymentLinkXBlock",
             """<vertical_demo>
                <payment_link/>
                <payment_link/>
                <payment_link/>
                </vertical_demo>
             """),
        ]