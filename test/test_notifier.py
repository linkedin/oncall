# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from ujson import dumps as json_dumps

WEEK = 60 * 60 * 24 * 7


def test_send_notification(mocker):

    def check_message(msg):
        assert msg['user'] == 'username'
        assert msg['mode'] == 'email'
        assert msg['subject'] == 'bar'
        assert msg['body'] == 'foo'

    from oncall.bin.notifier import send_queue, format_and_send_message
    mocker.patch('oncall.bin.notifier.send_message').side_effect = check_message
    mock_mark_sent = mocker.patch('oncall.bin.notifier.mark_message_as_sent')

    while send_queue.qsize() > 0:
        send_queue.get()
    send_time = 1476910800  # 14:00:00 on Oct 16, 2016
    send_queue.put({'user': 'username', 'mode': 'email', 'context': json_dumps({'foo': 'bar', 'baz': 'foo'}),
                    'send_time': send_time, 'subject': '%(foo)s', 'body': '%(baz)s'})
    format_and_send_message()
    assert send_queue.qsize() == 0
    mock_mark_sent.assert_called_once()
