from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from misago.categories.models import Category

from ..models import Post, Thread, ThreadParticipant
from ..participants import (
    has_participants,
    make_participants_aware,
    remove_participant,
    set_owner,
    set_users_unread_private_threads_sync,
)


class ParticipantsTests(TestCase):
    def setUp(self):
        datetime = timezone.now()

        self.category = Category.objects.all_categories()[:1][0]
        self.thread = Thread(
            category=self.category,
            started_on=datetime,
            starter_name='Tester',
            starter_slug='tester',
            last_post_on=datetime,
            last_poster_name='Tester',
            last_poster_slug='tester'
        )

        self.thread.set_title("Test thread")
        self.thread.save()

        post = Post.objects.create(
            category=self.category,
            thread=self.thread,
            poster_name='Tester',
            poster_ip='127.0.0.1',
            original="Hello! I am test message!",
            parsed="<p>Hello! I am test message!</p>",
            checksum="nope",
            posted_on=datetime,
            updated_on=datetime
        )

        self.thread.first_post = post
        self.thread.last_post = post
        self.thread.save()

    def test_has_participants(self):
        """has_participants returns true if thread has participants"""
        User = get_user_model()
        users = [
            User.objects.create_user("Bob", "bob@boberson.com", "Pass.123"),
            User.objects.create_user("Bob2", "bob2@boberson.com", "Pass.123"),
        ]

        self.assertFalse(has_participants(self.thread))

        ThreadParticipant.objects.add_participants(self.thread, users)
        self.assertTrue(has_participants(self.thread))

        self.thread.threadparticipant_set.all().delete()
        self.assertFalse(has_participants(self.thread))

    def test_make_participants_aware(self):
        """
        make_participants_aware sets participants_list and participant
        annotations on thread model
        """
        User = get_user_model()
        user = User.objects.create_user("Bob", "bob@boberson.com", "Pass.123")
        other_user = User.objects.create_user("Bob2", "bob2@boberson.com", "Pass.123")

        self.assertFalse(hasattr(self.thread, 'participants_list'))
        self.assertFalse(hasattr(self.thread, 'participant'))

        make_participants_aware(user, self.thread)

        self.assertTrue(hasattr(self.thread, 'participants_list'))
        self.assertTrue(hasattr(self.thread, 'participant'))

        self.assertEqual(self.thread.participants_list, [])
        self.assertIsNone(self.thread.participant)

        ThreadParticipant.objects.set_owner(self.thread, user)
        ThreadParticipant.objects.add_participants(self.thread, [other_user])

        make_participants_aware(user, self.thread)

        self.assertEqual(self.thread.participant.user, user)
        for participant in self.thread.participants_list:
            if participant.user == user:
                break
        else:
            self.fail("thread.participants_list didn't contain user")

    def test_remove_participant(self):
        """remove_participant removes user from thread"""
        User = get_user_model()
        user = User.objects.create_user("Bob", "bob@boberson.com", "Pass.123")

        set_owner(self.thread, user)
        remove_participant(self.thread, user)

        self.assertEqual(self.thread.participants.count(), 0)
        with self.assertRaises(ThreadParticipant.DoesNotExist):
            self.thread.threadparticipant_set.get(user=user)

    def test_set_owner(self):
        """set_owner sets user as thread owner"""
        User = get_user_model()
        user = User.objects.create_user("Bob", "bob@boberson.com", "Pass.123")

        set_owner(self.thread, user)

        owner = self.thread.threadparticipant_set.get(is_owner=True)
        self.assertEqual(user, owner.user)

    def test_set_users_unread_private_threads_sync(self):
        """
        set_users_unread_private_threads_sync sets sync_unread_private_threads
        flag on user model to true
        """
        User = get_user_model()
        users = [
            User.objects.create_user("Bob1", "bob1@boberson.com", "Pass.123"),
            User.objects.create_user("Bob2", "bob2@boberson.com", "Pass.123"),
        ]

        set_users_unread_private_threads_sync(users)
        for user in users:
            User.objects.get(pk=user.pk, sync_unread_private_threads=True)
