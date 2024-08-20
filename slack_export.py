import json
import argparse
import os
import io
import shutil
import copy
import sys
from datetime import datetime
from pick import pick
from time import sleep
from urllib.parse import urlparse
import requests


#################### Patched - Slacker ######################
# Purpose of the patch is to allow for a cookie header to be set
# so that xoxc (slack client) tokens can be used.

# Copyright 2015 Oktay Sancak
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import requests

import time

###### Slacker Utils ######
def get_api_url(method):
    """
    Returns API URL for the given method.

    :param method: Method name
    :type method: str

    :returns: API URL for the given method
    :rtype: str
    """
    return 'https://slack.com/api/{}'.format(method)


def get_item_id_by_name(list_dict, key_name):
    for d in list_dict:
        if d['name'] == key_name:
            return d['id']

###########################


__version__ = '0.14.0'

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 0
# seconds to wait after a 429 error if Slack's API doesn't provide one
DEFAULT_WAIT = 20

__all__ = ['Error', 'Response', 'BaseAPI', 'API', 'Auth', 'Users', 'Groups',
           'Channels', 'Chat', 'IM', 'IncomingWebhook', 'Search', 'Files',
           'Stars', 'Emoji', 'Presence', 'RTM', 'Team', 'Reactions', 'Pins',
           'UserGroups', 'UserGroupsUsers', 'MPIM', 'OAuth', 'DND', 'Bots',
           'FilesComments', 'Reminders', 'TeamProfile', 'UsersProfile',
           'IDPGroups', 'Apps', 'AppsPermissions', 'Slacker', 'Dialog',
           'Conversations', 'Migration']


class Error(Exception):
    pass


class Response(object):
    def __init__(self, body):
        self.raw = body
        self.body = json.loads(body)
        self.successful = self.body['ok']
        self.error = self.body.get('error')

    def __str__(self):
        return json.dumps(self.body)


# Patched
# Pass the headers along to the requests call
class BaseAPI(object):
    def __init__(self, token=None, headers=None, timeout=DEFAULT_TIMEOUT, proxies=None,
                 session=None, rate_limit_retries=DEFAULT_RETRIES):
        self.headers = headers
        self.token = token
        self.timeout = timeout
        self.proxies = proxies
        self.session = session
        self.rate_limit_retries = rate_limit_retries

    def _request(self, request_method, method, **kwargs):
        if self.token:
            kwargs.setdefault('params', {})['token'] = self.token
            kwargs['headers'] = self.headers
        url = get_api_url(method)

        # while we have rate limit retries left, fetch the resource and back
        # off as Slack's HTTP response suggests
        for retry_num in range(self.rate_limit_retries):
            response = request_method(
                url, timeout=self.timeout, proxies=self.proxies, **kwargs
            )

            if response.status_code == requests.codes.ok:
                break

            # handle HTTP 429 as documented at
            # https://api.slack.com/docs/rate-limits
            if response.status_code == requests.codes.too_many:
                sleep(1 + int(
                    response.headers.get('retry-after', DEFAULT_WAIT)
                ))
                continue

            response.raise_for_status()
        else:
            # with no retries left, make one final attempt to fetch the
            # resource, but do not handle too_many status differently
            response = request_method(
                url, timeout=self.timeout, proxies=self.proxies, **kwargs
            )
            response.raise_for_status()

        response = Response(response.text)
        if not response.successful:
            raise Error(response.error)

        return response

    def _session_get(self, url, params=None, **kwargs):
        kwargs.setdefault('allow_redirects', True)
        return self.session.request(
            method='get', url=url, params=params, **kwargs
        )

    def _session_post(self, url, data=None, **kwargs):
        return self.session.request(
            method='post', url=url, data=data, **kwargs
        )

    def get(self, api, **kwargs):
        return self._request(
            self._session_get if self.session else requests.get,
            api, **kwargs
        )

    def post(self, api, **kwargs):
        return self._request(
            self._session_post if self.session else requests.post,
            api, **kwargs
        )


class API(BaseAPI):
    def test(self, error=None, **kwargs):
        if error:
            kwargs['error'] = error

        return self.get('api.test', params=kwargs)


class Auth(BaseAPI):
    def test(self):
        return self.get('auth.test')

    def revoke(self, test=True):
        return self.post('auth.revoke', data={'test': int(test)})


class Conversations(BaseAPI):
    def archive(self, channel):
        return self.post('conversations.archive', data={'channel': channel})

    def close(self, channel):
        return self.post('conversations.close', data={'channel': channel})

    def create(self, name, user_ids=None, is_private=None):
        if isinstance(user_ids, (list, tuple)):
            user_ids = ','.join(user_ids)

        return self.post(
            'conversations.create',
            data={'name': name, 'user_ids': user_ids, 'is_private': is_private}
        )

    def history(self, channel, cursor=None, inclusive=None, latest=None,
                oldest=None, limit=None):
        return self.get(
            'conversations.history',
            params={
                'channel': channel,
                'cursor': cursor,
                'inclusive': inclusive,
                'latest': latest,
                'oldest': oldest,
                'limit': limit
            }
        )

    def info(self, channel, include_locale=None, include_num_members=None):
        return self.get(
            'conversations.info',
            params={
                'channel': channel,
                'include_locale': include_locale,
                'include_num_members': include_num_members
            }
        )

    def invite(self, channel, users):
        if isinstance(users, (list, tuple)):
            users = ','.join(users)

        return self.post(
            'conversations.invite',
            data={'channel': channel, 'users': users}
        )

    def join(self, channel):
        return self.post('conversations.join', data={'channel': channel})

    def kick(self, channel, user):
        return self.post(
            'conversations.kick',
            data={'channel': channel, 'user': user}
        )

    def leave(self, channel):
        return self.post('conversations.leave', data={'channel': channel})

    def list(self, cursor=None, exclude_archived=None, types=None, limit=None):
        if isinstance(types, (list, tuple)):
            types = ','.join(types)

        return self.get(
            'conversations.list',
            params={
                'cursor': cursor,
                'exclude_archived': exclude_archived,
                'types': types,
                'limit': limit
            }
        )

    def members(self, channel, cursor=None, limit=None):
        return self.get(
            'conversations.members',
            params={'channel': channel, 'cursor': cursor, 'limit': limit}
        )

    def open(self, channel=None, users=None, return_im=None):
        if isinstance(users, (list, tuple)):
            users = ','.join(users)

        return self.post(
            'conversations.open',
            data={'channel': channel, 'users': users, 'return_im': return_im}
        )

    def rename(self, channel, name):
        return self.post(
            'conversations.rename',
            data={'channel': channel, 'name': name}
        )

    def replies(self, channel, ts, cursor=None, inclusive=None, latest=None,
                oldest=None, limit=None):
        return self.get(
            'conversations.replies',
            params={
                'channel': channel,
                'ts': ts,
                'cursor': cursor,
                'inclusive': inclusive,
                'latest': latest,
                'oldest': oldest,
                'limit': limit
            }
        )

    def set_purpose(self, channel, purpose):
        return self.post(
            'conversations.setPurpose',
            data={'channel': channel, 'purpose': purpose}
        )

    def set_topic(self, channel, topic):
        return self.post(
            'conversations.setTopic',
            data={'channel': channel, 'topic': topic}
        )

    def unarchive(self, channel):
        return self.post('conversations.unarchive', data={'channel': channel})


class Dialog(BaseAPI):
    def open(self, dialog, trigger_id):
        return self.post('dialog.open',
                         data={
                             'dialog': json.dumps(dialog),
                             'trigger_id': trigger_id,
                         })


class UsersProfile(BaseAPI):
    def get(self, user=None, include_labels=False):
        return super(UsersProfile, self).get(
            'users.profile.get',
            params={'user': user, 'include_labels': int(include_labels)}
        )

    def set(self, user=None, profile=None, name=None, value=None):
        return self.post('users.profile.set',
                         data={
                             'user': user,
                             'profile': profile,
                             'name': name,
                             'value': value
                         })


class UsersAdmin(BaseAPI):
    def invite(self, email, channels=None, first_name=None,
               last_name=None, resend=True):
        return self.post('users.admin.invite',
                         params={
                             'email': email,
                             'channels': channels,
                             'first_name': first_name,
                             'last_name': last_name,
                             'resend': resend
                         })


class Users(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(Users, self).__init__(*args, **kwargs)
        self._profile = UsersProfile(*args, **kwargs)
        self._admin = UsersAdmin(*args, **kwargs)

    @property
    def profile(self):
        return self._profile

    @property
    def admin(self):
        return self._admin

    def info(self, user, include_locale=False):
        return self.get('users.info',
                        params={'user': user, 'include_locale': include_locale})

    def list(self, presence=False, limit=None):
        return self.get('users.list', params={'presence': int(presence), 'limit': limit})

    def identity(self):
        return self.get('users.identity')

    def set_active(self):
        return self.post('users.setActive')

    def get_presence(self, user):
        return self.get('users.getPresence', params={'user': user})

    def set_presence(self, presence):
        return self.post('users.setPresence', data={'presence': presence})

    def get_user_id(self, user_name):
        members = self.list().body['members']
        return get_item_id_by_name(members, user_name)


class Groups(BaseAPI):
    def create(self, name):
        return self.post('groups.create', data={'name': name})

    def create_child(self, channel):
        return self.post('groups.createChild', data={'channel': channel})

    def info(self, channel):
        return self.get('groups.info', params={'channel': channel})

    def list(self, exclude_archived=None):
        return self.get('groups.list',
                        params={'exclude_archived': exclude_archived})

    def history(self, channel, latest=None, oldest=None, count=None,
                inclusive=None):
        return self.get('groups.history',
                        params={
                            'channel': channel,
                            'latest': latest,
                            'oldest': oldest,
                            'count': count,
                            'inclusive': inclusive
                        })

    def invite(self, channel, user):
        return self.post('groups.invite',
                         data={'channel': channel, 'user': user})

    def kick(self, channel, user):
        return self.post('groups.kick',
                         data={'channel': channel, 'user': user})

    def leave(self, channel):
        return self.post('groups.leave', data={'channel': channel})

    def mark(self, channel, ts):
        return self.post('groups.mark', data={'channel': channel, 'ts': ts})

    def rename(self, channel, name):
        return self.post('groups.rename',
                         data={'channel': channel, 'name': name})

    def replies(self, channel, thread_ts):
        return self.get('groups.replies',
                        params={'channel': channel, 'thread_ts': thread_ts})

    def archive(self, channel):
        return self.post('groups.archive', data={'channel': channel})

    def unarchive(self, channel):
        return self.post('groups.unarchive', data={'channel': channel})

    def open(self, channel):
        return self.post('groups.open', data={'channel': channel})

    def close(self, channel):
        return self.post('groups.close', data={'channel': channel})

    def set_purpose(self, channel, purpose):
        return self.post('groups.setPurpose',
                         data={'channel': channel, 'purpose': purpose})

    def set_topic(self, channel, topic):
        return self.post('groups.setTopic',
                         data={'channel': channel, 'topic': topic})


class Channels(BaseAPI):
    def create(self, name):
        return self.post('channels.create', data={'name': name})

    def info(self, channel):
        return self.get('channels.info', params={'channel': channel})

    def list(self, exclude_archived=None, exclude_members=None):
        return self.get('channels.list',
                        params={'exclude_archived': exclude_archived,
                                'exclude_members': exclude_members})

    def history(self, channel, latest=None, oldest=None, count=None,
                inclusive=False, unreads=False):
        return self.get('channels.history',
                        params={
                            'channel': channel,
                            'latest': latest,
                            'oldest': oldest,
                            'count': count,
                            'inclusive': int(inclusive),
                            'unreads': int(unreads)
                        })

    def mark(self, channel, ts):
        return self.post('channels.mark',
                         data={'channel': channel, 'ts': ts})

    def join(self, name):
        return self.post('channels.join', data={'name': name})

    def leave(self, channel):
        return self.post('channels.leave', data={'channel': channel})

    def invite(self, channel, user):
        return self.post('channels.invite',
                         data={'channel': channel, 'user': user})

    def kick(self, channel, user):
        return self.post('channels.kick',
                         data={'channel': channel, 'user': user})

    def rename(self, channel, name):
        return self.post('channels.rename',
                         data={'channel': channel, 'name': name})

    def replies(self, channel, thread_ts):
        return self.get('channels.replies',
                        params={'channel': channel, 'thread_ts': thread_ts})

    def archive(self, channel):
        return self.post('channels.archive', data={'channel': channel})

    def unarchive(self, channel):
        return self.post('channels.unarchive', data={'channel': channel})

    def set_purpose(self, channel, purpose):
        return self.post('channels.setPurpose',
                         data={'channel': channel, 'purpose': purpose})

    def set_topic(self, channel, topic):
        return self.post('channels.setTopic',
                         data={'channel': channel, 'topic': topic})

    def get_channel_id(self, channel_name):
        channels = self.list().body['channels']
        return get_item_id_by_name(channels, channel_name)


class Chat(BaseAPI):
    def post_message(self, channel, text=None, username=None, as_user=None,
                     parse=None, link_names=None, attachments=None,
                     unfurl_links=None, unfurl_media=None, icon_url=None,
                     icon_emoji=None, thread_ts=None, reply_broadcast=None,
                     blocks=None, mrkdwn=True):

        # Ensure attachments are json encoded
        if attachments:
            if isinstance(attachments, list):
                attachments = json.dumps(attachments)

        return self.post('chat.postMessage',
                         data={
                             'channel': channel,
                             'text': text,
                             'username': username,
                             'as_user': as_user,
                             'parse': parse,
                             'link_names': link_names,
                             'attachments': attachments,
                             'unfurl_links': unfurl_links,
                             'unfurl_media': unfurl_media,
                             'icon_url': icon_url,
                             'icon_emoji': icon_emoji,
                             'thread_ts': thread_ts,
                             'reply_broadcast': reply_broadcast,
                             'blocks': blocks,
                             'mrkdwn': mrkdwn,
                         })

    def me_message(self, channel, text):
        return self.post('chat.meMessage',
                         data={'channel': channel, 'text': text})

    def command(self, channel, command, text):
        return self.post('chat.command',
                         data={
                             'channel': channel,
                             'command': command,
                             'text': text
                         })

    def update(self, channel, ts, text, attachments=None, parse=None,
               link_names=False, as_user=None, blocks=None):
        # Ensure attachments are json encoded
        if attachments is not None and isinstance(attachments, list):
            attachments = json.dumps(attachments)
        return self.post('chat.update',
                         data={
                             'channel': channel,
                             'ts': ts,
                             'text': text,
                             'attachments': attachments,
                             'parse': parse,
                             'link_names': int(link_names),
                             'as_user': as_user,
                             'blocks': blocks
                         })

    def delete(self, channel, ts, as_user=False):
        return self.post('chat.delete',
                         data={
                             'channel': channel,
                             'ts': ts,
                             'as_user': as_user
                         })

    def post_ephemeral(self, channel, text, user, as_user=None,
                       attachments=None, link_names=None, parse=None,
                       blocks=None):
        # Ensure attachments are json encoded
        if attachments is not None and isinstance(attachments, list):
            attachments = json.dumps(attachments)
        return self.post('chat.postEphemeral',
                         data={
                             'channel': channel,
                             'text': text,
                             'user': user,
                             'as_user': as_user,
                             'attachments': attachments,
                             'link_names': link_names,
                             'parse': parse,
                             'blocks': blocks
                         })

    def unfurl(self, channel, ts, unfurls, user_auth_message=None,
               user_auth_required=False, user_auth_url=None):
        return self.post('chat.unfurl',
                         data={
                             'channel': channel,
                             'ts': ts,
                             'unfurls': unfurls,
                             'user_auth_message': user_auth_message,
                             'user_auth_required': user_auth_required,
                             'user_auth_url': user_auth_url,
                         })

    def get_permalink(self, channel, message_ts):
        return self.get('chat.getPermalink',
                        params={
                            'channel': channel,
                            'message_ts': message_ts
                        })


class IM(BaseAPI):
    def list(self):
        return self.get('im.list')

    def history(self, channel, latest=None, oldest=None, count=None,
                inclusive=None, unreads=False):
        return self.get('im.history',
                        params={
                            'channel': channel,
                            'latest': latest,
                            'oldest': oldest,
                            'count': count,
                            'inclusive': inclusive,
                            'unreads': int(unreads)
                        })

    def replies(self, channel, thread_ts):
        return self.get('im.replies',
                        params={'channel': channel, 'thread_ts': thread_ts})

    def mark(self, channel, ts):
        return self.post('im.mark', data={'channel': channel, 'ts': ts})

    def open(self, user):
        return self.post('im.open', data={'user': user})

    def close(self, channel):
        return self.post('im.close', data={'channel': channel})


class MPIM(BaseAPI):
    def open(self, users):
        if isinstance(users, (tuple, list)):
            users = ','.join(users)

        return self.post('mpim.open', data={'users': users})

    def close(self, channel):
        return self.post('mpim.close', data={'channel': channel})

    def mark(self, channel, ts):
        return self.post('mpim.mark', data={'channel': channel, 'ts': ts})

    def list(self):
        return self.get('mpim.list')

    def history(self, channel, latest=None, oldest=None, inclusive=False,
                count=None, unreads=False):
        return self.get('mpim.history',
                        params={
                            'channel': channel,
                            'latest': latest,
                            'oldest': oldest,
                            'inclusive': int(inclusive),
                            'count': count,
                            'unreads': int(unreads)
                        })

    def replies(self, channel, thread_ts):
        return self.get('mpim.replies',
                        params={'channel': channel, 'thread_ts': thread_ts})


class Search(BaseAPI):
    def all(self, query, sort=None, sort_dir=None, highlight=None, count=None,
            page=None):
        return self.get('search.all',
                        params={
                            'query': query,
                            'sort': sort,
                            'sort_dir': sort_dir,
                            'highlight': highlight,
                            'count': count,
                            'page': page
                        })

    def files(self, query, sort=None, sort_dir=None, highlight=None,
              count=None, page=None):
        return self.get('search.files',
                        params={
                            'query': query,
                            'sort': sort,
                            'sort_dir': sort_dir,
                            'highlight': highlight,
                            'count': count,
                            'page': page
                        })

    def messages(self, query, sort=None, sort_dir=None, highlight=None,
                 count=None, page=None):
        return self.get('search.messages',
                        params={
                            'query': query,
                            'sort': sort,
                            'sort_dir': sort_dir,
                            'highlight': highlight,
                            'count': count,
                            'page': page
                        })


class FilesComments(BaseAPI):
    def add(self, file_, comment):
        return self.post('files.comments.add',
                         data={'file': file_, 'comment': comment})

    def delete(self, file_, id_):
        return self.post('files.comments.delete',
                         data={'file': file_, 'id': id_})

    def edit(self, file_, id_, comment):
        return self.post('files.comments.edit',
                         data={'file': file_, 'id': id_, 'comment': comment})


class Files(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(Files, self).__init__(*args, **kwargs)
        self._comments = FilesComments(*args, **kwargs)

    @property
    def comments(self):
        return self._comments

    def list(self, user=None, ts_from=None, ts_to=None, types=None,
             count=None, page=None, channel=None):
        return self.get('files.list',
                        params={
                            'user': user,
                            'ts_from': ts_from,
                            'ts_to': ts_to,
                            'types': types,
                            'count': count,
                            'page': page,
                            'channel': channel
                        })

    def info(self, file_, count=None, page=None):
        return self.get('files.info',
                        params={'file': file_, 'count': count, 'page': page})

    def upload(self, file_=None, content=None, filetype=None, filename=None,
               title=None, initial_comment=None, channels=None, thread_ts=None):
        if isinstance(channels, (tuple, list)):
            channels = ','.join(channels)

        data = {
            'content': content,
            'filetype': filetype,
            'filename': filename,
            'title': title,
            'initial_comment': initial_comment,
            'channels': channels,
            'thread_ts': thread_ts
        }

        if file_:
            if isinstance(file_, str):
                with open(file_, 'rb') as f:
                    return self.post(
                        'files.upload', data=data, files={'file': f}
                    )

            return self.post(
                'files.upload', data=data, files={'file': file_}
            )

        return self.post('files.upload', data=data)

    def delete(self, file_):
        return self.post('files.delete', data={'file': file_})

    def revoke_public_url(self, file_):
        return self.post('files.revokePublicURL', data={'file': file_})

    def shared_public_url(self, file_):
        return self.post('files.sharedPublicURL', data={'file': file_})


class Stars(BaseAPI):
    def add(self, file_=None, file_comment=None, channel=None, timestamp=None):
        assert file_ or file_comment or channel

        return self.post('stars.add',
                         data={
                             'file': file_,
                             'file_comment': file_comment,
                             'channel': channel,
                             'timestamp': timestamp
                         })

    def list(self, user=None, count=None, page=None):
        return self.get('stars.list',
                        params={'user': user, 'count': count, 'page': page})

    def remove(self, file_=None, file_comment=None, channel=None,
               timestamp=None):
        assert file_ or file_comment or channel

        return self.post('stars.remove',
                         data={
                             'file': file_,
                             'file_comment': file_comment,
                             'channel': channel,
                             'timestamp': timestamp
                         })


class Emoji(BaseAPI):
    def list(self):
        return self.get('emoji.list')


class Presence(BaseAPI):
    AWAY = 'away'
    ACTIVE = 'active'
    TYPES = (AWAY, ACTIVE)

    def set(self, presence):
        assert presence in Presence.TYPES, 'Invalid presence type'
        return self.post('presence.set', data={'presence': presence})


class RTM(BaseAPI):
    def start(self, simple_latest=False, no_unreads=False, mpim_aware=False):
        return self.get('rtm.start',
                        params={
                            'simple_latest': int(simple_latest),
                            'no_unreads': int(no_unreads),
                            'mpim_aware': int(mpim_aware),
                        })

    def connect(self):
        return self.get('rtm.connect')


class TeamProfile(BaseAPI):
    def get(self, visibility=None):
        return super(TeamProfile, self).get(
            'team.profile.get',
            params={'visibility': visibility}
        )


class Team(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(Team, self).__init__(*args, **kwargs)
        self._profile = TeamProfile(*args, **kwargs)

    @property
    def profile(self):
        return self._profile

    def info(self):
        return self.get('team.info')

    def access_logs(self, count=None, page=None, before=None):
        return self.get('team.accessLogs',
                        params={
                            'count': count,
                            'page': page,
                            'before': before
                        })

    def integration_logs(self, service_id=None, app_id=None, user=None,
                         change_type=None, count=None, page=None):
        return self.get('team.integrationLogs',
                        params={
                            'service_id': service_id,
                            'app_id': app_id,
                            'user': user,
                            'change_type': change_type,
                            'count': count,
                            'page': page,
                        })

    def billable_info(self, user=None):
        return self.get('team.billableInfo', params={'user': user})


class Reactions(BaseAPI):
    def add(self, name, file_=None, file_comment=None, channel=None,
            timestamp=None):
        # One of file, file_comment, or the combination of channel and timestamp
        # must be specified
        assert (file_ or file_comment) or (channel and timestamp)

        return self.post('reactions.add',
                         data={
                             'name': name,
                             'file': file_,
                             'file_comment': file_comment,
                             'channel': channel,
                             'timestamp': timestamp,
                         })

    def get(self, file_=None, file_comment=None, channel=None, timestamp=None,
            full=None):
        return super(Reactions, self).get('reactions.get',
                                          params={
                                              'file': file_,
                                              'file_comment': file_comment,
                                              'channel': channel,
                                              'timestamp': timestamp,
                                              'full': full,
                                          })

    def list(self, user=None, full=None, count=None, page=None):
        return super(Reactions, self).get('reactions.list',
                                          params={
                                              'user': user,
                                              'full': full,
                                              'count': count,
                                              'page': page,
                                          })

    def remove(self, name, file_=None, file_comment=None, channel=None,
               timestamp=None):
        # One of file, file_comment, or the combination of channel and timestamp
        # must be specified
        assert (file_ or file_comment) or (channel and timestamp)

        return self.post('reactions.remove',
                         data={
                             'name': name,
                             'file': file_,
                             'file_comment': file_comment,
                             'channel': channel,
                             'timestamp': timestamp,
                         })


class Pins(BaseAPI):
    def add(self, channel, file_=None, file_comment=None, timestamp=None):
        # One of file, file_comment, or timestamp must also be specified
        assert file_ or file_comment or timestamp

        return self.post('pins.add',
                         data={
                             'channel': channel,
                             'file': file_,
                             'file_comment': file_comment,
                             'timestamp': timestamp,
                         })

    def remove(self, channel, file_=None, file_comment=None, timestamp=None):
        # One of file, file_comment, or timestamp must also be specified
        assert file_ or file_comment or timestamp

        return self.post('pins.remove',
                         data={
                             'channel': channel,
                             'file': file_,
                             'file_comment': file_comment,
                             'timestamp': timestamp,
                         })

    def list(self, channel):
        return self.get('pins.list', params={'channel': channel})


class UserGroupsUsers(BaseAPI):
    def list(self, usergroup, include_disabled=None):
        if isinstance(include_disabled, bool):
            include_disabled = int(include_disabled)

        return self.get('usergroups.users.list', params={
            'usergroup': usergroup,
            'include_disabled': include_disabled,
        })

    def update(self, usergroup, users, include_count=None):
        if isinstance(users, (tuple, list)):
            users = ','.join(users)

        if isinstance(include_count, bool):
            include_count = int(include_count)

        return self.post('usergroups.users.update', data={
            'usergroup': usergroup,
            'users': users,
            'include_count': include_count,
        })


class UserGroups(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(UserGroups, self).__init__(*args, **kwargs)
        self._users = UserGroupsUsers(*args, **kwargs)

    @property
    def users(self):
        return self._users

    def list(self, include_disabled=None, include_count=None,
             include_users=None):
        if isinstance(include_disabled, bool):
            include_disabled = int(include_disabled)

        if isinstance(include_count, bool):
            include_count = int(include_count)

        if isinstance(include_users, bool):
            include_users = int(include_users)

        return self.get('usergroups.list', params={
            'include_disabled': include_disabled,
            'include_count': include_count,
            'include_users': include_users,
        })

    def create(self, name, handle=None, description=None, channels=None,
               include_count=None):
        if isinstance(channels, (tuple, list)):
            channels = ','.join(channels)

        if isinstance(include_count, bool):
            include_count = int(include_count)

        return self.post('usergroups.create', data={
            'name': name,
            'handle': handle,
            'description': description,
            'channels': channels,
            'include_count': include_count,
        })

    def update(self, usergroup, name=None, handle=None, description=None,
               channels=None, include_count=None):
        if isinstance(channels, (tuple, list)):
            channels = ','.join(channels)

        if isinstance(include_count, bool):
            include_count = int(include_count)

        return self.post('usergroups.update', data={
            'usergroup': usergroup,
            'name': name,
            'handle': handle,
            'description': description,
            'channels': channels,
            'include_count': include_count,
        })

    def disable(self, usergroup, include_count=None):
        if isinstance(include_count, bool):
            include_count = int(include_count)

        return self.post('usergroups.disable', data={
            'usergroup': usergroup,
            'include_count': include_count,
        })

    def enable(self, usergroup, include_count=None):
        if isinstance(include_count, bool):
            include_count = int(include_count)

        return self.post('usergroups.enable', data={
            'usergroup': usergroup,
            'include_count': include_count,
        })


class DND(BaseAPI):
    def team_info(self, users=None):
        if isinstance(users, (tuple, list)):
            users = ','.join(users)

        return self.get('dnd.teamInfo', params={'users': users})

    def set_snooze(self, num_minutes):
        return self.post('dnd.setSnooze', data={'num_minutes': num_minutes})

    def info(self, user=None):
        return self.get('dnd.info', params={'user': user})

    def end_dnd(self):
        return self.post('dnd.endDnd')

    def end_snooze(self):
        return self.post('dnd.endSnooze')


class Migration(BaseAPI):
    def exchange(self, users, to_old=False):
        if isinstance(users, (list, tuple)):
            users = ','.join(users)

        return self.get(
            'migration.exchange', params={'users': users, 'to_old': to_old}
        )


class Reminders(BaseAPI):
    def add(self, text, time, user=None):
        return self.post('reminders.add', data={
            'text': text,
            'time': time,
            'user': user,
        })

    def complete(self, reminder):
        return self.post('reminders.complete', data={'reminder': reminder})

    def delete(self, reminder):
        return self.post('reminders.delete', data={'reminder': reminder})

    def info(self, reminder):
        return self.get('reminders.info', params={'reminder': reminder})

    def list(self):
        return self.get('reminders.list')


class Bots(BaseAPI):
    def info(self, bot=None):
        return self.get('bots.info', params={'bot': bot})


class IDPGroups(BaseAPI):
    def list(self, include_users=False):
        return self.get('idpgroups.list',
                        params={'include_users': int(include_users)})


class OAuth(BaseAPI):
    def access(self, client_id, client_secret, code, redirect_uri=None):
        return self.post('oauth.access',
                         data={
                             'client_id': client_id,
                             'client_secret': client_secret,
                             'code': code,
                             'redirect_uri': redirect_uri
                         })

    def token(self, client_id, client_secret, code, redirect_uri=None,
              single_channel=None):
        return self.post('oauth.token',
                         data={
                             'client_id': client_id,
                             'client_secret': client_secret,
                             'code': code,
                             'redirect_uri': redirect_uri,
                             'single_channel': single_channel,
                         })


class AppsPermissions(BaseAPI):
    def info(self):
        return self.get('apps.permissions.info')

    def request(self, scopes, trigger_id):
        return self.post('apps.permissions.request',
                         data={
                             scopes: ','.join(scopes),
                             trigger_id: trigger_id,
                         })


class Apps(BaseAPI):
    def __init__(self, *args, **kwargs):
        super(Apps, self).__init__(*args, **kwargs)
        self._permissions = AppsPermissions(*args, **kwargs)

    @property
    def permissions(self):
        return self._permissions

    def uninstall(self, client_id, client_secret):
        return self.get(
            'apps.uninstall',
            params={'client_id': client_id, 'client_secret': client_secret}
        )


class IncomingWebhook(object):
    def __init__(self, url=None, timeout=DEFAULT_TIMEOUT, proxies=None):
        self.url = url
        self.timeout = timeout
        self.proxies = proxies

    def post(self, data):
        """
        Posts message with payload formatted in accordance with
        this documentation https://api.slack.com/incoming-webhooks
        """
        if not self.url:
            raise Error('URL for incoming webhook is undefined')

        return requests.post(self.url, data=json.dumps(data),
                             timeout=self.timeout, proxies=self.proxies)

# Patched
class Slacker(object):
    oauth = OAuth(timeout=DEFAULT_TIMEOUT)

    def __init__(self, token, headers=None, incoming_webhook_url=None,
                 timeout=DEFAULT_TIMEOUT, http_proxy=None, https_proxy=None,
                 session=None, rate_limit_retries=DEFAULT_RETRIES):

        proxies = self.__create_proxies(http_proxy, https_proxy)
        api_args = {
            'headers': headers,
            'token': token,
            'timeout': timeout,
            'proxies': proxies,
            'session': session,
            'rate_limit_retries': rate_limit_retries,
        }
        self.im = IM(**api_args)
        self.api = API(**api_args)
        self.dnd = DND(**api_args)
        self.rtm = RTM(**api_args)
        self.apps = Apps(**api_args)
        self.auth = Auth(**api_args)
        self.bots = Bots(**api_args)
        self.chat = Chat(**api_args)
        self.dialog = Dialog(**api_args)
        self.team = Team(**api_args)
        self.pins = Pins(**api_args)
        self.mpim = MPIM(**api_args)
        self.users = Users(**api_args)
        self.files = Files(**api_args)
        self.stars = Stars(**api_args)
        self.emoji = Emoji(**api_args)
        self.search = Search(**api_args)
        self.groups = Groups(**api_args)
        self.channels = Channels(**api_args)
        self.presence = Presence(**api_args)
        self.reminders = Reminders(**api_args)
        self.migration = Migration(**api_args)
        self.reactions = Reactions(**api_args)
        self.idpgroups = IDPGroups(**api_args)
        self.usergroups = UserGroups(**api_args)
        self.conversations = Conversations(**api_args)
        self.incomingwebhook = IncomingWebhook(url=incoming_webhook_url,
                                               timeout=timeout, proxies=proxies)

    def __create_proxies(self, http_proxy=None, https_proxy=None):
        proxies = dict()
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        return proxies

##################################################################

# Obtains all replies for a given channel id + a starting timestamp
# Duplicates the logic in getHistory
def getReplies(channelId, timestamp, pageSize=1000):
    conversationObject = slack.conversations
    messages = []
    lastTimestamp = None
    lastTimestampFromPreviousIteration = lastTimestamp

    while True:
        try:
            response = conversationObject.replies(
                channel=channelId,
                ts=timestamp,
                latest=lastTimestamp,
                oldest=0,
                limit=pageSize,
            ).body
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retryInSeconds = int(e.response.headers["Retry-After"])
                print("Rate limit hit. Retrying in {0} second{1}.".format(retryInSeconds, "s" if retryInSeconds > 1 else ""))
                sleep(retryInSeconds + 1)

                response = conversationObject.replies(
                    channel=channelId,
                    ts=timestamp,
                    latest=lastTimestamp,
                    oldest=0,
                    limit=pageSize,
                ).body

        messages.extend(response["messages"])

        if response["has_more"] == True:
            sys.stdout.write(".")
            sys.stdout.flush()
            sleep(1.3)  # Respect the Slack API rate limit
                
            lastTimestamp = messages[-1]['ts']  # -1 means last element in a list
            minTimestamp = None
                
            if lastTimestamp == lastTimestampFromPreviousIteration:
                # Then we might be in an infinite loop,
                # because lastTimestamp is supposed to be decreasing.
                # Try harder: maybe we want messages[-2]['ts']?
                    
                minTimestamp = float(lastTimestamp)
                for m in messages:
                    if minTimestamp > float(m['ts']):
                        minTimestamp = float(m['ts'])
                
                if minTimestamp == lastTimestamp:
                    print("warning: lastTimestamp is not changing.  infinite loop?")
                lastTimestamp = minTimestamp
                    
            lastTimestampFromPreviousIteration = lastTimestamp

        else:
            break

    if lastTimestamp != None:
        print("")

    messages.sort(key=lambda message: message["ts"])

    # Obtaining replies also gives us the first message in the the thread
    # (which we don't want) -- after sorting, our first message with the be the
    # first in the list of all messages, so we remove the head of the list
    assert messages[0]["ts"] == timestamp, "unexpected start of thread"
    messages = messages[1:]

    return messages



# fetches the complete message history for a channel/group/im
#
# pageableObject could be:
# slack.channel
# slack.groups
# slack.im
#
# channelId is the id of the channel/group/im you want to download history for.

def getHistory(pageableObject, channelId, pageSize = 1000):
    messages = []
    lastTimestamp = None
    lastTimestampFromPreviousIteration = lastTimestamp

    while(True):
        try:
             if isinstance(pageableObject, Conversations):
                response = pageableObject.history(
                    channel=channelId,
                    latest=lastTimestamp,
                    oldest=0,
                    limit=pageSize
                ).body
             else:
                response = pageableObject.history(
                    channel = channelId,
                    latest    = lastTimestamp,
                    oldest    = 0,
                    count     = pageSize
                ).body
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retryInSeconds = int(e.response.headers['Retry-After'])
                print("Rate limit hit. Retrying in {0} second{1}.".format(retryInSeconds, "s" if retryInSeconds > 1 else ""))
                sleep(retryInSeconds + 1)
                if isinstance(pageableObject, Conversations):
                    response = pageableObject.history(
                        channel=channelId,
                        latest=lastTimestamp,
                        oldest=0,
                        limit=pageSize
                    ).body
                else:
                    response = pageableObject.history(
                        channel=channelId,
                        latest=lastTimestamp,
                        oldest=0,
                        count=pageSize
                    ).body

        messages.extend(response['messages'])

        # Grab all replies
        for message in response["messages"]:
            if "thread_ts" in message:
                sleep(0.5) #INSERT LIMIT 
                messages.extend(getReplies(channelId, message["thread_ts"], pageSize))

        if (response['has_more'] == True):
            sys.stdout.write("*")
            sys.stdout.flush()
            sleep(1.3) # Respect the Slack API rate limit
                
            lastTimestamp = messages[-1]['ts'] # -1 means last element in a list
            minTimestamp = None
                
            if lastTimestamp == lastTimestampFromPreviousIteration:
                # Then we might be in an infinite loop,
                # because lastTimestamp is supposed to be decreasing.
                # Try harder: maybe we want messages[-2]['ts']?
                    
                minTimestamp = float(lastTimestamp)
                for m in messages:
                    if minTimestamp > float(m['ts']):
                        minTimestamp = float(m['ts'])
                
                if minTimestamp == lastTimestamp:
                    print("warning: lastTimestamp is not changing.  infinite loop?")
                lastTimestamp = minTimestamp
                    
            lastTimestampFromPreviousIteration = lastTimestamp

        else:
            break

    if lastTimestamp != None:
        print("")

    messages.sort(key = lambda message: message['ts'])

    return messages


def mkdir(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)


# create datetime object from slack timestamp ('ts') string
def parseTimeStamp( timeStamp ):
    if '.' in timeStamp:
        t_list = timeStamp.split('.')
        if len( t_list ) != 2:
            raise ValueError( 'Invalid time stamp' )
        else:
            return datetime.utcfromtimestamp( float(t_list[0]) )


# move channel files from old directory to one with new channel name
def channelRename( oldRoomName, newRoomName ):
    # check if any files need to be moved
    if not os.path.isdir( oldRoomName ):
        return
    mkdir( newRoomName )
    for fileName in os.listdir( oldRoomName ):
        shutil.move( os.path.join( oldRoomName, fileName ), newRoomName )
    os.rmdir( oldRoomName )


def writeMessageFile( fileName, messages ):
    directory = os.path.dirname(fileName)

    # if there's no data to write to the file, return
    if not messages:
        return

    if not os.path.isdir( directory ):
        mkdir( directory )

    with open(fileName, 'w') as outFile:
        json.dump( messages, outFile, indent=4)


# parse messages by date
def parseMessages( roomDir, messages, roomType ):
    nameChangeFlag = roomType + "_name"

    currentFileDate = ''
    currentMessages = []
    for message in messages:
        #first store the date of the next message
        ts = parseTimeStamp( message['ts'] )
        fileDate = '{:%Y-%m-%d}'.format(ts)

        #if it's on a different day, write out the previous day's messages
        if fileDate != currentFileDate:
            outFileName = '{room}/{file}.json'.format( room = roomDir, file = currentFileDate )
            writeMessageFile( outFileName, currentMessages )
            currentFileDate = fileDate
            currentMessages = []

        # check if current message is a name change
        # dms won't have name change events
        if roomType != "im" and ( 'subtype' in message ) and message['subtype'] == nameChangeFlag:
            roomDir = message['name']
            oldRoomPath = message['old_name']
            newRoomPath = roomDir
            channelRename( oldRoomPath, newRoomPath )

        currentMessages.append( message )
    outFileName = '{room}/{file}.json'.format( room = roomDir, file = currentFileDate )
    writeMessageFile( outFileName, currentMessages )

def filterConversationsByName(channelsOrGroups, channelOrGroupNames):
    return [conversation for conversation in channelsOrGroups if conversation['name'] in channelOrGroupNames]

def promptForPublicChannels(channels):
    channelNames = [channel['name'] for channel in channels]
    selectedChannels = pick(channelNames, 'Select the Public Channels you want to export:', multi_select=True)
    return [channels[index] for channelName, index in selectedChannels]

# fetch and write history for all public channels
def fetchPublicChannels(channels):
    print("Fetching", len(channels), "public channels")
    if dryRun:
        print("Public Channels selected for export:")
        for channel in channels:
            print(channel['name'])
        print()
        return

    for channel in channels:
        channelDir = channel['name']
        print("Fetching history for Public Channel: {0}".format(channelDir))
        try:
            mkdir( channelDir )
        except NotADirectoryError:
            # Failed creating directory, probably because the name is not a valid
            # Windows directory name (like "com4"). Adding a prefix to try to work-around
            # that.
            channelDir = ("c-" + channel['name'])
            mkdir( channelDir )
        messages = getHistory(slack.conversations, channel['id'])
        parseMessages( channelDir, messages, 'channel')

# write channels.json file
def dumpChannelFile():
    print("Making channels file")

    private = []
    mpim = []

    for group in groups:
        if group['is_mpim']:
            mpim.append(group)
            continue
        private.append(group)

    # slack viewer wants DMs to have a members list, not sure why but doing as they expect
    for dm in dms:
        dm['members'] = [dm['user'], tokenOwnerId]

    #We will be overwriting this file on each run.
    with open('channels.json', 'w') as outFile:
        json.dump( channels , outFile, indent=4)
    with open('groups.json', 'w') as outFile:
        json.dump( private , outFile, indent=4)
    with open('mpims.json', 'w') as outFile:
        json.dump( mpim , outFile, indent=4)
    with open('dms.json', 'w') as outFile:
        json.dump( dms , outFile, indent=4)

def filterDirectMessagesByUserNameOrId(dms, userNamesOrIds):
    userIds = [userIdsByName.get(userNameOrId, userNameOrId) for userNameOrId in userNamesOrIds]
    return [dm for dm in dms if dm['user'] in userIds]

def promptForDirectMessages(dms):
    dmNames = [userNamesById.get(dm['user'], dm['user'] + " (name unknown)") for dm in dms]
    selectedDms = pick(dmNames, 'Select the 1:1 DMs you want to export:', multi_select=True)
    return [dms[index] for dmName, index in selectedDms]

def fetchConversations(threads):
    print("Fetching", len(threads), " specified threads")
    for convID in threads:
        print("Fetching specified conversation with ID {0}".format(convID))
        if not dryRun:
            channelID, convTS = convID.split("/")[-2:]
            if convTS.startswith("p"):
                convTS = convTS[1:11] + "." + convTS[11:]
            outDir = "threads/{0}".format(convTS)
            mkdir(outDir)

            response = slack.conversations.history(
                    channel = channelID,
                    latest  = convTS,
                    oldest  = 0,
                    limit   = 1
                ).body
            messages = list(response["messages"])
            messages.extend(getReplies(channelID, convTS, 1000))
            print("Fetched {0} replies for conversation from channel: {0} with TS {1}".format(len(messages), channelID, convTS))
            parseMessages( outDir, messages, "channel" )
            sleep(1.3)  # Respect the Slack API rate limit

# fetch and write history for all direct message conversations
# also known as IMs in the slack API.
def fetchDirectMessages(dms):
    print("Fetching", len(dms), "1:1 DMs")
    if dryRun:
        print("1:1 DMs selected for export:")
        for dm in dms:
            print(userNamesById.get(dm['user'], dm['user'] + " (name unknown)"))
        print()
        return

    for dm in dms:
        name = userNamesById.get(dm['user'], dm['user'] + " (name unknown)")
        print("Fetching 1:1 DMs with {0}".format(name))
        dmId = dm['id']
        mkdir(dmId)
        messages = getHistory(slack.conversations, dm['id'])
        parseMessages( dmId, messages, "im" )

def promptForGroups(groups):
    groupNames = [group['name'] for group in groups]
    selectedGroups = pick(groupNames, 'Select the Private Channels and Group DMs you want to export:', multi_select=True)
    return [groups[index] for groupName, index in selectedGroups]

# fetch and write history for specific private channel
# also known as groups in the slack API.
def fetchGroups(groups):
    print("Fetching", len(groups), "Private Channels and Group DMs")
    if dryRun:
        print("Private Channels and Group DMs selected for export:")
        for group in groups:
            print(group['name'])
        print()
        return

    for group in groups:
        groupDir = group['name']
        mkdir(groupDir)
        messages = []
        print("Fetching history for Private Channel / Group DM: {0}".format(group['name']))
        messages = getHistory(slack.conversations, group['id'])
        parseMessages( groupDir, messages, 'group' )

# fetch all users for the channel and return a map userId -> userName
def getUserMap():
    global userNamesById, userIdsByName
    for user in users:
        userNamesById[user['id']] = user['name']
        userIdsByName[user['name']] = user['id']

# stores json of user info
def dumpUserFile():
    #write to user file, any existing file needs to be overwritten.
    with open( "users.json", 'w') as userFile:
        json.dump( users, userFile, indent=4 )

# get basic info about the slack channel to ensure the authentication token works
def doTestAuth():
    testAuth = slack.auth.test().body
    teamName = testAuth['team']
    currentUser = testAuth['user']
    print("Successfully authenticated for team {0} and user {1} ".format(teamName, currentUser))
    return testAuth

# Since Slacker does not Cache.. populate some reused lists
# TODO: 
#   1. Only populate data for lists that will be used in export.
#   2. Allow adjustable limits (greater or less than 1000).
#      Fork by veqryn appears to do this for users:
#        - users = slack.users.list().body['members']
#        - print(u"Found {0} Users".format(len(users)))
#        -  
#        + users_list = slack.users.list(limit=500)
#        + users = users_list.body['members']
#        + while len(users_list.body['members']) >= 500:
#        +     users_list = slack.users.list(limit=500, cursor=users_list.body['response_metadata']['next_cursor'])
#        +     users.extend(users_list.body['members'])
#        +     sleep(1)  # crude rate limit
#        +        
#        + print("Found {0} Users".format(len(users)))
#   
def bootstrapKeyValues():
    global users, channels, groups, dms
     
    users = slack.users.list(limit=10).body['members']
    print("Found {0} Users".format(len(users)))
    sleep(3.05)

    channels = slack.conversations.list(limit = 1000, types=('public_channel')).body['channels']
    print("Found {0} Public Channels".format(len(channels)))
    # think mayne need to retrieve channel memberships for the slack-export-viewer to work
    for n in range(len(channels)):
        channels[n]["members"] = slack.conversations.members(limit=1000, channel=channels[n]['id']).body['members']
        print("Retrieved members of {0}".format(channels[n]['name']))
    sleep(3.05)

    groups = slack.conversations.list(limit = 1000, types=('private_channel', 'mpim')).body['channels']
    print("Found {0} Private Channels or Group DMs".format(len(groups)))
    # need to retrieve channel memberships for the slack-export-viewer to work
    for n in range(len(groups)):
        groups[n]["members"] = slack.conversations.members(limit=1000, channel=groups[n]['id']).body['members']
        print("Retrieved members of {0}".format(groups[n]['name']))
    sleep(3.05)

    dms = slack.conversations.list(limit = 1000, types=('im')).body['channels']
    print("Found {0} 1:1 DM conversations\n".format(len(dms)))
    sleep(3.05)

    getUserMap()

# Returns the conversations to download based on the command-line arguments
def selectConversations(allConversations, commandLineArg, filter, prompt):
    global args
    if args.excludeArchived:
        allConversations = [ conv for conv in allConversations if not conv["is_archived"] ]
    if isinstance(commandLineArg, list) and len(commandLineArg) > 0:
        return filter(allConversations, commandLineArg)
    elif commandLineArg != None or not anyConversationsSpecified():
        if args.prompt:
            return prompt(allConversations)
        else:
            return allConversations
    else:
        return []

# Returns true if any conversations were specified on the command line
def anyConversationsSpecified():
    global args
    return args.publicChannels != None or args.groups != None or args.directMessages != None

# This method is used in order to create a empty Channel if you do not export public channels
# otherwise, the viewer will error and not show the root screen. Rather than forking the editor, I work with it.
def dumpDummyChannel():
    channelName = channels[0]['name']
    mkdir( channelName )
    fileDate = '{:%Y-%m-%d}'.format(datetime.today())
    outFileName = '{room}/{file}.json'.format( room = channelName, file = fileDate )
    writeMessageFile(outFileName, [])

def downloadFiles(token, cookie_header=None):
    """
    Iterate through all json files, downloads files stored on files.slack.com and replaces the link with a local one

    Args:
        jsonDirectory: folder where the json files are in, will be searched recursively
    """
    print("Starting to download files")
    for root, subdirs, files in os.walk("."):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            filePath = os.path.join(root, filename)
            data = []
            with open(filePath) as inFile:
                data = json.load(inFile)
                for msg in data:
                    for slackFile in msg.get("files", []):
                        # Skip deleted files
                        if slackFile.get("mode") == "tombstone":
                            continue

                        for key, value in slackFile.items():
                            # Find all entries referring to files on files.slack.com
                            if not isinstance(value, str) or not value.startswith("https://files.slack.com/"):
                                continue

                            url = urlparse(value)

                            localFile = os.path.join("../files.slack.com", url.path[1:])  # Need to discard first "/" in URL, because:
                                # "If a component is an absolute path, all previous components are thrown away and joining continues
                                # from the absolute path component."
                            print("Downloading %s, saving to %s" % (url.geturl(), localFile))

                            # Create folder structure
                            os.makedirs(os.path.dirname(localFile), exist_ok=True)

                            # Replace URL in data - suitable for use with slack-export-viewer if files.slack.com is linked
                            slackFile[key] = "/static/files.slack.com%s" % url.path

                            # Check if file already downloaded, with a non-zero size
                            # (can't check for same size because thumbnails don't have a size)
                            if os.path.exists(localFile) and (os.path.getsize(localFile) > 0):
                                print("Skipping already downloaded file: %s" % localFile)
                                continue

                            # Download files
                            headers = {"Authorization": f"Bearer {token}",
                            **cookie_header}
                            r = requests.get(url.geturl(), headers=headers)
                            try: 
                                open(localFile, 'wb').write(r.content)
                            except FileNotFoundError: 
                                print("File writing error-still all broken")
                                continue
                            

            # Save updated data to json file
            with open(filePath, "w") as outFile:
                json.dump(data, outFile, indent=4, sort_keys=True)

            print("Replaced all files in %s" % filePath)

def finalize():
    os.chdir('..')
    if zipName:
        shutil.make_archive(zipName, 'zip', outputDirectory, None)
        shutil.rmtree(outputDirectory)
    exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export Slack history')

    parser.add_argument('--token', required=True, help="Slack API token")
    parser.add_argument('--cookie', help="a set of cookies for the xoxc api token")
    parser.add_argument('--zip', help="Name of a zip file to output as")

    parser.add_argument(
        '--dryRun',
        action='store_true',
        default=False,
        help="List the conversations that will be exported (don't fetch/write history)")

    parser.add_argument(
        '--publicChannels',
        nargs='*',
        default=None,
        metavar='CHANNEL_NAME',
        help="Export the given Public Channels")

    parser.add_argument(
        '--groups',
        nargs='*',
        default=None,
        metavar='GROUP_NAME',
        help="Export the given Private Channels / Group DMs")

    parser.add_argument(
        '--directMessages',
        nargs='*',
        default=None,
        metavar='USER_NAME',
        help="Export 1:1 DMs with the given users")

    parser.add_argument(
        '--prompt',
        action='store_true',
        default=False,
        help="Prompt you to select the conversations to export")

    parser.add_argument(
        '--downloadSlackFiles',
        action='store_true',
        default=False,
        help="Downloads files from files.slack.com for local access, stored in 'files.slack.com' folder. "
            "Link this folder inside slack-export-viewer/slackviewer/static/ to have it work seamless with slack-export-viewer")

    parser.add_argument(
        '--excludeArchived',
        action='store_true',
        default=False,
        help="Do not export channels that have been archived")

    parser.add_argument(
        '--excludeNonMember',
        action='store_true',
        default=False,
        help="Only export public channels if the user is a member of the channel")

    parser.add_argument(
        '--skipBootstrap',
        action='store_true',
        default=False,
        help="Skip the bootstrap process to load users and channels")

    parser.add_argument(
        '--threads',
        nargs='*',
        default=None,
        metavar='threads',
        help="Export the specific threads only given in the form of channelID/threadTS or full thread URLs")

    args = parser.parse_args()

    users = []
    channels = []
    groups = []
    dms = []
    userNamesById = {}
    userIdsByName = {}

    cookie_header = {'cookie': args.cookie}
    slack = Slacker(headers=cookie_header, token=args.token)
    testAuth = doTestAuth()
    tokenOwnerId = testAuth['user_id']

    if not args.skipBootstrap:
        bootstrapKeyValues()

    dryRun = args.dryRun
    zipName = args.zip

    outputDirectory = "{0}-slack_export".format(datetime.today().strftime("%Y%m%d-%H%M%S"))
    mkdir(outputDirectory)
    os.chdir(outputDirectory)

    if not dryRun:
        dumpUserFile()
        dumpChannelFile()

    selectedChannels = selectConversations(
        channels,
        args.publicChannels,
        filterConversationsByName,
        promptForPublicChannels)
    if args.excludeNonMember:
        selectedChannels  = [ channel for channel in selectedChannels if channel["is_member"] ]

    selectedGroups = selectConversations(
        groups,
        args.groups,
        filterConversationsByName,
        promptForGroups)

    selectedDms = selectConversations(
        dms,
        args.directMessages,
        filterDirectMessagesByUserNameOrId,
        promptForDirectMessages)

    if len(selectedChannels) > 0:
        fetchPublicChannels(selectedChannels)

    if len(selectedGroups) > 0:
        if len(selectedChannels) == 0:
            dumpDummyChannel()
        fetchGroups(selectedGroups)

    if len(selectedDms) > 0:
        fetchDirectMessages(selectedDms)

    if len(args.threads) > 0:
        fetchConversations(args.threads)

    if args.downloadSlackFiles:
        downloadFiles(token=args.token, cookie_header=cookie_header)

    finalize()
