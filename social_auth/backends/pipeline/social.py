from django.db import models
from django.db.utils import IntegrityError

from social_auth.utils import setting
from social_auth.backends.pipeline import warn_setting


# If UserSocialAuth class is overridden, it *must* provide the following fields
# and methods work with django-social-auth:
#
#   user = ForeignKey(User)
#   provider = CharField()
#   uid = CharField()
#   extra_data = JSONField()
#   def expiration_delta()
#       ...

from apps.accounts.models import UserSocialAuth


def social_auth_user(backend, uid, user=None, *args, **kwargs):
    """Return UserSocialAuth account for backend/uid pair or None if it
    doesn't exists.

    Raise ValueError if UserSocialAuth entry belongs to another user.
    """
    try:
        social_user = UserSocialAuth.objects.get(provider=backend.name,
                                                 uid=uid)
    except UserSocialAuth.DoesNotExist:
        social_user = None

    if social_user:
        if user and social_user.user != user:
            raise ValueError('Account already in use.', social_user)
        elif not user:
            user = social_user.user
    return {'social_user': social_user, 'user': user}


def associate_user(backend, user, uid, social_user=None, *args, **kwargs):
    """Associate user social account with user instance."""
    if social_user:
        return None

    try:
        social = UserSocialAuth.objects.create(user=user, uid=str(uid),
                                               provider=backend.name)
    except IntegrityError:
        # Protect for possible race condition, those bastard with FTL
        # clicking capabilities, check issue #131:
        #   https://github.com/omab/django-social-auth/issues/131
        return social_auth_user(backend, uid, user, social_user=social_user,
                                *args, **kwargs)
    except Exception as e:
        raise e
    else:
        return {'social_user': social, 'user': social.user}


def load_extra_data(backend, details, response, social_user, uid, user,
                    *args, **kwargs):
    """Load extra data from provider and store it on current UserSocialAuth
    extra_data field.
    """
    warn_setting('SOCIAL_AUTH_EXTRA_DATA', 'load_extra_data')

    if setting('SOCIAL_AUTH_EXTRA_DATA', True):
        extra_data = backend.extra_data(user, uid, response, details)
        if extra_data and social_user.extra_data != extra_data:
            social_user.extra_data = extra_data
            social_user.save()
