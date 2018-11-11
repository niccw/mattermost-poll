# -*- coding: utf-8 -*-
import os.path
import json

import requests
from flask import url_for

import settings
import app


def format_help(command):
    """Returns a help string describing the poll slash command."""
    help_file = os.path.join(os.path.dirname(__file__), 'help.md')
    with open(help_file) as f:
        return f.read().format(command=command)
    return "Help file not found."""


def format_poll(poll):
    """Returns the JSON representation of the given poll.
    """
    if poll.is_finished():
        return _format_finished_poll(poll)
    return _format_running_poll(poll)


def _format_running_poll(poll):
    fields = [{
        'short': False,
        'value': "*Number of voters: {}*".format(poll.num_voters()),
        'title': ""
    }]
    if poll.public:
        fields += [{
            'short': False,
            'value': ":warning: *This poll is public. When it closes the"
                     " participants and their answers will be visible.*",
            'title': ""
        }]
    if poll.max_votes > 1:
        fields += [{
            'short': False,
            'value': "*You have {} votes*".format(poll.max_votes),
            'title': ""
        }]

    return {
        'response_type': 'in_channel',
        'attachments': [{
            'text': poll.message,
            'actions': format_actions(poll),
            'fields': fields
        }]
    }


def _format_finished_poll(poll):
    votes = [(vote, vote_id) for vote_id, vote in
             enumerate(poll.vote_options)]

    if poll.bars:
        # bars should be displayed from long to short
        votes.sort(key=lambda v: poll.count_votes(v[1]), reverse=True)

    return {
        'response_type': 'in_channel',
        'attachments': [{
            'text': poll.message,
            'fields': [{
                'short': False,
                'value': "*Number of voters: {}*".format(poll.num_voters()),
                'title': ""
            }] + [{
                'short': not poll.bars,
                'title': vote,
                'value': _format_vote_end_text(poll, vote_id)
            } for vote, vote_id in votes]
        }]
    }


def _format_vote_end_text(poll, vote_id):
    vote_count = poll.count_votes(vote_id)
    total_votes = poll.num_votes()
    if total_votes != 0:
        rel_vote_count = 100*vote_count/total_votes
    else:
        rel_vote_count = 0.0

    text = ''

    if poll.bars:
        png_path = url_for('send_img', filename="bar.png", _external=True)
        bar_min_width = 2  # even 0% should show a tiny bar
        bar_width = 450*rel_vote_count/100 + bar_min_width
        text += '![Bar]({} ={}x25) '.format(png_path, bar_width)

    plural = 's' if vote_count != 1 else ''
    text += '{} Vote{} ({:.1f}%)'.format(vote_count, plural, rel_vote_count)

    if poll.public:
        voters = resolve_usernames(poll.voters(vote_id))

        if len(voters):
            text += '\n' + ', '.join(voters)

    return text


def resolve_usernames(user_ids):
    """Resolve the list of user ids to list of user names."""
    if len(user_ids) == 0:
        return []

    try:
        header = {'Authorization': 'Bearer ' + settings.MATTERMOST_PA_TOKEN}
        url = settings.MATTERMOST_URL + '/api/v4/users/ids'

        r = requests.post(url, headers=header, json=user_ids)
        if r.ok:
            return [user["username"] for user in json.loads(r.text)]
    except Exception as e:
        app.app.logger.error('Username query failed: %s', str(e))

    return ['<Failed to resolve usernames>']


def format_actions(poll):
    """Returns the JSON data of all available actions of the given poll.
    Additional to the options of the poll, a 'End Poll' action
    is appended.
    The returned list looks similar to this:
    ```
    [{
        "name": "<First Option> (0)",
        "integration": {
            "context": {
                "poll_id": "<unique_id>",
                "vote": 0
            },
            "url": "http://<hostname:port>/vote"
        }
    },
    ... additional entries for all poll options ...
    {
        "name": "End Poll",
        "integration": {
            "url": "http://<hostname:port>/end",
            "context": {
                "poll_id": "<unique_id>"
            }
        }
    }]
    ```
    """
    options = poll.vote_options
    name = "{name}"
    if not poll.secret:
        # display current number of votes
        name += " ({votes})"
    actions = [{
        'name': name.format(name=vote, votes=poll.count_votes(vote_id)),
        'integration': {
            'url': url_for('vote', _external=True),
            'context': {
                'vote': vote_id,
                'poll_id': poll.id
            }
        }
    } for vote_id, vote in enumerate(options)]
    # add action to end the poll
    actions.append({
        'name': "End Poll",
        'integration': {
            'url': url_for('end_poll', _external=True),
            'context': {
                'poll_id': poll.id
            }
        }
    })
    return actions


def format_user_vote(poll, user_id):
    """Returns the vote of the given user as a string.
       Example: 'Pizza ✓, Burger ✗, Extra Cheese ✓'"""
    string = ''
    for vote_id, vote in enumerate(poll.vote_options):
        string += vote
        if vote_id in poll.votes(user_id):
            string += ' ✓'
        else:
            string += ' ✗'
        string += ', '
    return string[:-2]  # remove trailing ,