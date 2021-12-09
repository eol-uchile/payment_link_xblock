#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import patch, Mock, MagicMock
from collections import namedtuple
from django.urls import reverse
from django.test import TestCase, Client
from django.test import Client
from django.conf import settings
from django.contrib.auth.models import User
from common.djangoapps.util.testing import UrlResetMixin
from urllib.parse import parse_qs
from opaque_keys.edx.locator import CourseLocator
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from common.djangoapps.course_modes.models import CourseMode
from xblock.field_data import DictFieldData
import json
import urllib.parse
from .payment_link import PaymentLinkXBlock
# Create your tests here.

class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None

class TestPaymentLinkXBlock(UrlResetMixin, ModuleStoreTestCase):

    def make_an_xblock(cls, **kw):
        """
        Helper method that creates a PaymentLinkXBlock
        """

        course = cls.course
        runtime = Mock(
            course_id=course.id,
            user_is_staff=False,
            service=Mock(
                return_value=Mock(_catalog={}),
            ),
        )
        scope_ids = Mock()
        field_data = DictFieldData(kw)
        xblock = PaymentLinkXBlock(runtime, field_data, scope_ids)
        xblock.xmodule_runtime = runtime
        xblock.location = course.location
        xblock.course_id = course.id
        xblock.category = 'payment_link'
        return xblock

    def setUp(self):
        super(TestPaymentLinkXBlock, self).setUp()
        self.course = CourseFactory.create(org='foo', course='baz', run='bar')
        self.xblock = self.make_an_xblock()
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client = Client()
            user = UserFactory(
                username='testuser101',
                password='12345',
                email='student@edx.org',
                is_staff=True)
            self.client.login(username='testuser101', password='12345')
            CourseEnrollmentFactory(
                user=user, course_id=self.course.id)
            # user student
            self.student_client = Client()
            self.student = UserFactory(
                username='student',
                password='12345',
                email='student2@edx.org')
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            self.assertTrue(
                self.student_client.login(
                    username='student',
                    password='12345'))
    
    def test_validate_field_data(self):
        """
            Verify if default xblock is created correctly
        """
        self.assertEqual(self.xblock.display_name, 'Enlace de Pago')

    def test_edit_block_studio(self):
        """
            Verify submit studio edits is working
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')

    def test_context_author(self):
        """
            Test context author view
        """
        CourseMode.objects.get_or_create(
            course_id=self.course.id,
            mode_display_name='verified',
            mode_slug='verified',
            min_price=1,
            sku='ASD'
        )
        response = self.xblock.get_context_author()
        self.assertEqual(response['is_enabled'], True)
        self.assertEqual(response['ecommerce_payment_page'], '/basket/add/')
        self.assertEqual(response['verified_sku'], 'ASD')
    
    def test_context_author_not_course_mode(self):
        """
            Test context author view, when course mode is not configurated
        """
        response = self.xblock.get_context_author()
        self.assertEqual(response['is_enabled'], False)

    def test_context_student(self):
        """
            Test context student view
        """
        CourseMode.objects.get_or_create(
            course_id=self.course.id,
            mode_display_name='verified',
            mode_slug='verified',
            min_price=1,
            sku='ASD'
        )
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context_student()
        self.assertEqual(response['is_enabled'], True)
        self.assertEqual(response['is_enrolled'], True)
        self.assertEqual(response['ecommerce_payment_page'], '/basket/add/')
        self.assertEqual(response['verified_sku'], 'ASD')
    
    def test_context_student_not_course_mode(self):
         """
            Test context student view, when course mode is not configurated
        """
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context_student()
        self.assertEqual(response['is_enrolled'], True)
        self.assertEqual(response['is_enabled'], False)

    def test_context_student_not_enrolled(self):
         """
            Test context student view, when user is None
        """
        self.xblock.scope_ids.user_id = None
        response = self.xblock.get_context_student()
        self.assertEqual(response['is_enrolled'], False)